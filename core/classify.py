from typing import Dict, Any, Optional
from rapidfuzz import fuzz
import re
import logging

logger = logging.getLogger(__name__)

class DocumentClassifier:
    def __init__(self, rag_system, llm_interface):
        self.rag = rag_system
        self.llm = llm_interface
        self.doc_types = [
            "Articles of Association",
            "Memorandum of Association", 
            "Board Resolution",
            "Shareholder Resolution",
            "Incorporation Application",
            "UBO Declaration",
            "Register of Members",
            "Register of Directors",
            "Register of Members and Directors",
            "Change of Registered Address Notice",
            "Employment Contract",
            "Compliance Policy",
            "Commercial Agreement",
            "Licensing Filing"
        ]
        
        self.keywords = {
            "Articles of Association": [
                "articles of association", "aoa", "articles", "company constitution"
            ],
            "Memorandum of Association": [
                "memorandum of association", "moa", "memorandum", "company memorandum"
            ],
            "Board Resolution": [
                "board resolution", "directors resolution", "board meeting", "director resolution"
            ],
            "Shareholder Resolution": [
                "shareholder resolution", "members resolution", "shareholders meeting"
            ],
            "Incorporation Application": [
                "incorporation application", "application for incorporation", 
                "company incorporation", "incorporation form"
            ],
            "UBO Declaration": [
                "ultimate beneficial owner", "beneficial ownership", "ubo declaration", 
                "beneficial owner", "ubo"
            ],
            "Register of Members": [
                "register of members", "members register", "share register", "shareholder register"
            ],
            "Register of Directors": [
                "register of directors", "directors register", "director register"
            ],
            "Register of Members and Directors": [
                "register of members and directors", "combined register", 
                "members and directors register"
            ],
            "Change of Registered Address Notice": [
                "change of registered address", "registered office change", "address change"
            ],
            "Employment Contract": [
                "employment contract", "employment agreement", "service agreement", 
                "employee contract"
            ],
            "Compliance Policy": [
                "compliance policy", "policy document", "procedure", "risk policy", 
                "governance policy"
            ],
            "Commercial Agreement": [
                "commercial agreement", "service agreement", "consultancy agreement", 
                "nda", "non-disclosure", "sha", "shareholder agreement"
            ],
            "Licensing Filing": [
                "licensing application", "license application", "regulatory filing", 
                "business plan", "licensing"
            ]
        }
    
    def classify(self, filename: str, text: str, metadata: Dict) -> Dict[str, Any]:
        """Classify document type with confidence score"""
        
        # Try rule-based classification first
        rule_result = self._classify_by_rules(filename, text, metadata)
        
        if rule_result['confidence'] >= 0.7:
            return rule_result
        
        # Fall back to LLM-assisted classification
        llm_result = self._classify_by_llm(filename, text)
        
        # Return the more confident result
        if llm_result['confidence'] > rule_result['confidence']:
            return llm_result
        else:
            return rule_result
    
    def _classify_by_rules(self, filename: str, text: str, metadata: Dict) -> Dict[str, Any]:
        """Rule-based classification using keywords and patterns"""
        
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        best_type = None
        best_score = 0
        
        # Check each document type
        for doc_type, keywords in self.keywords.items():
            score = 0
            
            # Check filename
            for keyword in keywords:
                filename_score = fuzz.partial_ratio(keyword, filename_lower)
                score = max(score, filename_score)
            
            # Check content
            for keyword in keywords:
                # Exact phrase matching gets higher score
                if keyword in text_lower:
                    score = max(score, 95)
                else:
                    content_score = fuzz.partial_ratio(keyword, text_lower[:2000])
                    score = max(score, content_score * 0.8)  # Slight penalty for fuzzy match
            
            # Check title/header patterns
            title_score = self._check_title_patterns(doc_type, text_lower[:500])
            score = max(score, title_score)
            
            if score > best_score:
                best_score = score
                best_type = doc_type
        
        confidence = min(1.0, best_score / 100.0)
        
        return {
            'type': best_type if confidence >= 0.4 else 'Unknown',
            'confidence': confidence,
            'method': 'rule_based'
        }
    
    def _check_title_patterns(self, doc_type: str, text_start: str) -> float:
        """Check for document-specific title patterns"""
        
        patterns = {
            "Articles of Association": [
                r"articles\s+of\s+association",
                r"company\s+constitution",
                r"constitutional\s+document"
            ],
            "Memorandum of Association": [
                r"memorandum\s+of\s+association",
                r"company\s+memorandum"
            ],
            "Board Resolution": [
                r"board\s+resolution",
                r"directors?\s+resolution",
                r"resolution\s+of\s+the\s+board"
            ],
            "UBO Declaration": [
                r"ultimate\s+beneficial\s+owner",
                r"beneficial\s+ownership\s+declaration",
                r"ubo\s+declaration"
            ],
            "Register of Members": [
                r"register\s+of\s+members",
                r"members?\s+register"
            ],
            "Register of Directors": [
                r"register\s+of\s+directors?",
                r"directors?\s+register"
            ]
        }
        
        if doc_type in patterns:
            for pattern in patterns[doc_type]:
                if re.search(pattern, text_start, re.IGNORECASE):
                    return 90
        
        return 0
    
    def _classify_by_llm(self, filename: str, text: str) -> Dict[str, Any]:
        """LLM-assisted classification with RAG context"""
        
        try:
            # Get relevant context from knowledge base
            context_docs = self.rag.search(
                f"ADGM document types classification {filename}", 
                k=3
            )
            
            context = "\n".join([doc.page_content for doc in context_docs])
            
            prompt = f"""
            Classify this ADGM corporate document into one of these types:
            {', '.join(self.doc_types)}
            
            Context from ADGM regulations:
            {context}
            
            Document filename: {filename}
            Document content (first 2000 chars):
            {text[:2000]}
            
            Respond with just the document type from the list above, or "Unknown" if unclear.
            """
            
            response = self.llm.query(prompt)
            
            # Extract document type from response
            predicted_type = self._extract_type_from_response(response)
            
            # Estimate confidence based on response clarity
            confidence = 0.6 if predicted_type != 'Unknown' else 0.3
            
            return {
                'type': predicted_type,
                'confidence': confidence,
                'method': 'llm_assisted'
            }
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {
                'type': 'Unknown',
                'confidence': 0.2,
                'method': 'llm_failed'
            }
    
    def _extract_type_from_response(self, response: str) -> str:
        """Extract document type from LLM response"""
        
        response_lower = response.lower()
        
        # Look for exact matches first
        for doc_type in self.doc_types:
            if doc_type.lower() in response_lower:
                return doc_type
        
        # Look for partial matches
        for doc_type in self.doc_types:
            key_words = doc_type.lower().split()
            if all(word in response_lower for word in key_words):
                return doc_type
        
        return 'Unknown'
