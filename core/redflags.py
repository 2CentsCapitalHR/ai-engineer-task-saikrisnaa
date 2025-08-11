from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class RedFlagDetector:
    def __init__(self, rag_system, llm_interface):
        self.rag = rag_system
        self.llm = llm_interface
        
        # Initialize rule-based checks
        self.rules = [
            self._check_jurisdiction,
            self._check_registered_office,
            self._check_articles_sections,
            self._check_signatory_blocks,
            self._check_ubo_particulars,
            self._check_binding_language,
            self._check_adgm_references
        ]
    
    def detect_issues(self, document: Dict, process_info: Dict) -> List[Dict[str, Any]]:
        """Detect compliance issues in a document"""
        
        issues = []
        
        # Run rule-based checks
        for rule in self.rules:
            try:
                rule_issues = rule(document, process_info)
                if rule_issues:
                    issues.extend(rule_issues)
            except Exception as e:
                logger.error(f"Rule check failed: {e}")
        
        # Run LLM-assisted semantic checks for critical documents
        if self._is_critical_document(document):
            llm_issues = self._llm_semantic_check(document, process_info)
            issues.extend(llm_issues)
        
        return issues
    
    def _is_critical_document(self, document: Dict) -> bool:
        """Check if document needs detailed semantic analysis"""
        critical_types = {
            "Articles of Association",
            "Memorandum of Association", 
            "UBO Declaration",
            "Commercial Agreement"
        }
        return document['classification']['type'] in critical_types
    
    def _check_jurisdiction(self, document: Dict, process_info: Dict) -> List[Dict]:
        """Check jurisdiction and governing law clauses"""
        issues = []
        text = document.get('text', '').lower()
        doc_type = document['classification']['type']
        
        # Flag non-ADGM court references
        bad_courts = [
            'uae federal courts', 'dubai courts', 'abu dhabi courts',
            'federal courts of uae', 'courts of dubai'
        ]
        
        for court in bad_courts:
            if court in text:
                issues.append({
                    'document': doc_type,
                    'section_hint': 'Jurisdiction clause',
                    'issue': f'References {court} instead of ADGM Courts',
                    'severity': 'High',
                    'citations': ['ADGM Courts Framework'],
                    'suggestion': 'Update jurisdiction to reference ADGM Courts exclusively.',
                    'location': self._find_text_location(document.get('text', ''), court)
                })
        
        # Check for missing ADGM jurisdiction in key documents
        key_docs = {'Articles of Association', 'Memorandum of Association', 'Commercial Agreement'}
        if doc_type in key_docs:
            if not re.search(r'adgm\s+courts?|abu dhabi global market.*courts?', text):
                issues.append({
                    'document': doc_type,
                    'section_hint': 'Jurisdiction clause',
                    'issue': 'Missing explicit ADGM Courts jurisdiction reference',
                    'severity': 'High',
                    'citations': ['ADGM Courts Framework'],
                    'suggestion': 'Include clause specifying ADGM Courts jurisdiction.',
                    'location': None
                })
        
        return issues
    
    def _check_registered_office(self, document: Dict, process_info: Dict) -> List[Dict]:
        """Check registered office requirements"""
        issues = []
        text = document.get('text', '')
        doc_type = document['classification']['type']
        
        # For incorporation documents, ensure ADGM address is present
        if doc_type in {'Articles of Association', 'Incorporation Application'}:
            if not re.search(r'adgm|abu dhabi global market', text, re.IGNORECASE):
                issues.append({
                    'document': doc_type,
                    'section_hint': 'Registered office',
                    'issue': 'Registered office address must be within ADGM',
                    'severity': 'High',
                    'citations': ['ADGM Companies Regulations 2020, Section 6(4)(a)'],
                    'suggestion': 'Specify a registered office address within ADGM jurisdiction.',
                    'location': None
                })
        
        return issues
    
    def _check_articles_sections(self, document: Dict, process_info: Dict) -> List[Dict]:
        """Check Articles of Association for required sections"""
        if document['classification']['type'] != 'Articles of Association':
            return []
        
        issues = []
        text = document.get('text', '').lower()
        
        required_sections = {
            'objects': ['objects', 'purpose', 'business'],
            'share_capital': ['share capital', 'capital', 'shares'],
            'directors': ['directors', 'board'],
            'meetings': ['meetings', 'general meeting'],
            'transfers': ['transfer', 'transmission']
        }
        
        for section_name, keywords in required_sections.items():
            if not any(keyword in text for keyword in keywords):
                issues.append({
                    'document': 'Articles of Association',
                    'section_hint': f'{section_name.replace("_", " ").title()} provisions',
                    'issue': f'Missing or unclear {section_name.replace("_", " ")} provisions',
                    'severity': 'Medium',
                    'citations': ['ADGM Model Articles Requirements'],
                    'suggestion': f'Include clear provisions regarding {section_name.replace("_", " ")}.',
                    'location': None
                })
        
        return issues
    
    def _check_signatory_blocks(self, document: Dict, process_info: Dict) -> List[Dict]:
        """Check for proper signatory blocks"""
        issues = []
        text = document.get('text', '')
        doc_type = document['classification']['type']
        
        # Documents that require signatures
        signature_required = {
            'Articles of Association', 'Memorandum of Association',
            'Board Resolution', 'Shareholder Resolution',
            'Commercial Agreement', 'Employment Contract'
        }
        
        if doc_type in signature_required:
            has_signature_block = bool(re.search(
                r'signature|signed|witness|date.*sign|sign.*date', 
                text, re.IGNORECASE
            ))
            
            if not has_signature_block:
                issues.append({
                    'document': doc_type,
                    'section_hint': 'Execution block',
                    'issue': 'Missing signature block or execution provisions',
                    'severity': 'Medium',
                    'citations': ['ADGM Document Execution Requirements'],
                    'suggestion': 'Include proper signature blocks with name, title, and date.',
                    'location': None
                })
        
        return issues
    
    def _check_ubo_particulars(self, document: Dict, process_info: Dict) -> List[Dict]:
        """Check UBO declaration completeness"""
        if document['classification']['type'] != 'UBO Declaration':
            return []
        
        issues = []
        text = document.get('text', '').lower()
        
        required_fields = {
            'name': ['name', 'full name'],
            'birth': ['date of birth', 'birth', 'born'],
            'nationality': ['nationality', 'citizen'],
            'address': ['address', 'residential'],
            'passport': ['passport', 'identity', 'id number'],
            'ownership': ['ownership', 'beneficial', 'control', 'shares']
        }
        
        missing_fields = []
        for field, keywords in required_fields.items():
            if not any(keyword in text for keyword in keywords):
                missing_fields.append(field)
        
        if missing_fields:
            issues.append({
                'document': 'UBO Declaration',
                'section_hint': 'Required particulars',
                'issue': f'Missing required UBO particulars: {", ".join(missing_fields)}',
                'severity': 'High',
                'citations': ['ADGM Beneficial Ownership Regulations 2022'],
                'suggestion': 'Include all required UBO particulars as per ADGM regulations.',
                'location': None
            })
        
        return issues
    
    def _check_binding_language(self, document: Dict, process_info: Dict) -> List[Dict]:
        """Check for non-binding language where binding language expected"""
        issues = []
        text = document.get('text', '')
        doc_type = document['classification']['type']
        
        # Documents that should use binding language
        binding_docs = {
            'Articles of Association', 'Memorandum of Association',
            'Commercial Agreement', 'Employment Contract'
        }
        
        if doc_type in binding_docs:
            # Look for weak language patterns
            weak_patterns = [
                r'\bmay\s+(?:be|do|have)',
                r'\bshould\s+(?:be|do|have)',
                r'\bmight\s+(?:be|do|have)',
                r'\bcould\s+(?:be|do|have)'
            ]
            
            for pattern in weak_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    issues.append({
                        'document': doc_type,
                        'section_hint': 'Language clarity',
                        'issue': f'Potentially non-binding language: "{match.group()}"',
                        'severity': 'Low',
                        'citations': ['Legal Drafting Best Practices'],
                        'suggestion': 'Consider using "shall", "must", or "will" for binding obligations.',
                        'location': match.span()
                    })
        
        return issues
    
    def _check_adgm_references(self, document: Dict, process_info: Dict) -> List[Dict]:
        """Check for proper ADGM references"""
        issues = []
        text = document.get('text', '').lower()
        doc_type = document['classification']['type']
        
        # Key documents should reference ADGM
        key_docs = {
            'Articles of Association', 'Memorandum of Association',
            'Incorporation Application'
        }
        
        if doc_type in key_docs:
            if 'adgm' not in text and 'abu dhabi global market' not in text:
                issues.append({
                    'document': doc_type,
                    'section_hint': 'ADGM references',
                    'issue': 'Document does not clearly reference ADGM jurisdiction',
                    'severity': 'Medium',
                    'citations': ['ADGM Registration Requirements'],
                    'suggestion': 'Include clear references to ADGM as the governing jurisdiction.',
                    'location': None
                })
        
        return issues
    
    def _llm_semantic_check(self, document: Dict, process_info: Dict) -> List[Dict]:
        """LLM-assisted semantic compliance check"""
        try:
            # Get relevant regulatory context
            context_docs = self.rag.search(
                f"ADGM compliance requirements {document['classification']['type']}", 
                k=3
            )
            context = "\n".join([doc.page_content for doc in context_docs])
            
            prompt = f"""
            Analyze this ADGM {document['classification']['type']} for compliance issues:
            
            ADGM Regulatory Context:
            {context}
            
            Document Content:
            {document.get('text', '')[:3000]}
            
            Identify any compliance issues, missing clauses, or regulatory violations.
            Focus on ADGM-specific requirements.
            
            Respond in this format:
            ISSUE: [description]
            SEVERITY: [High/Medium/Low]
            SUGGESTION: [how to fix]
            ---
            """
            
            response = self.llm.query(prompt)
            return self._parse_llm_issues(response, document['classification']['type'])
            
        except Exception as e:
            logger.error(f"LLM semantic check failed: {e}")
            return []
    
    def _parse_llm_issues(self, response: str, doc_type: str) -> List[Dict]:
        """Parse LLM response into structured issues"""
        issues = []
        
        # Simple parsing - could be enhanced
        sections = response.split('---')
        for section in sections:
            if 'ISSUE:' in section:
                issue_match = re.search(r'ISSUE:\s*(.+)', section)
                severity_match = re.search(r'SEVERITY:\s*(\w+)', section)
                suggestion_match = re.search(r'SUGGESTION:\s*(.+)', section)
                
                if issue_match:
                    issues.append({
                        'document': doc_type,
                        'section_hint': 'LLM Analysis',
                        'issue': issue_match.group(1).strip(),
                        'severity': severity_match.group(1) if severity_match else 'Medium',
                        'citations': ['LLM Semantic Analysis'],
                        'suggestion': suggestion_match.group(1).strip() if suggestion_match else '',
                        'location': None
                    })
        
        return issues
    
    def _find_text_location(self, text: str, search_term: str) -> tuple:
        """Find location of text for commenting"""
        match = re.search(re.escape(search_term), text, re.IGNORECASE)
        return match.span() if match else None
