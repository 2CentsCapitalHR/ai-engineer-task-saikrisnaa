from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ChecklistValidator:
    def __init__(self, rag_system):
        self.rag = rag_system
        
        # Define required documents for different processes
        self.process_requirements = {
            "Company Incorporation": {
                "Private Company Limited by Shares": [
                    "Articles of Association",
                    "Memorandum of Association", 
                    "Incorporation Application",
                    "UBO Declaration",
                    "Register of Members",
                    "Register of Directors",
                    "Board Resolution"
                ],
                "Private Company Limited by Guarantee": [
                    "Articles of Association",
                    "Memorandum of Association",
                    "Incorporation Application", 
                    "UBO Declaration",
                    "Register of Members",
                    "Register of Directors",
                    "Board Resolution"
                ]
            },
            "Licensing": [
                "Licensing Filing",
                "Business Plan"
            ],
            "Employment/HR": [
                "Employment Contract"
            ]
        }
    
    def infer_process(self, documents: List[Dict]) -> Dict[str, Any]:
        """Infer the legal process from uploaded document types"""
        
        doc_types = {doc['classification']['type'] for doc in documents}
        
        # Company incorporation indicators
        incorporation_docs = {
            "Articles of Association", "Memorandum of Association", 
            "Incorporation Application", "UBO Declaration",
            "Register of Members", "Register of Directors"
        }
        
        if len(doc_types & incorporation_docs) >= 3:
            # Determine entity type based on document content
            entity_type = self._infer_entity_type(documents)
            return {
                'process': 'Company Incorporation',
                'entity_type': entity_type,
                'confidence': 0.9
            }
        
        # Licensing indicators
        if "Licensing Filing" in doc_types:
            return {
                'process': 'Licensing',
                'entity_type': None,
                'confidence': 0.8
            }
        
        # Employment indicators  
        if "Employment Contract" in doc_types:
            return {
                'process': 'Employment/HR',
                'entity_type': None,
                'confidence': 0.8
            }
        
        return {
            'process': 'Unknown',
            'entity_type': None,
            'confidence': 0.3
        }
    
    def _infer_entity_type(self, documents: List[Dict]) -> str:
        """Infer entity type from document content"""
        
        # Look for clues in document text
        all_text = " ".join([doc.get('text', '') for doc in documents]).lower()
        
        if any(term in all_text for term in ["limited by guarantee", "guarantee"]):
            return "Private Company Limited by Guarantee"
        elif any(term in all_text for term in ["limited by shares", "share capital", "shares"]):
            return "Private Company Limited by Shares"
        else:
            # Default assumption
            return "Private Company Limited by Shares"
    
    def validate_checklist(self, documents: List[Dict], process_info: Dict) -> Dict[str, Any]:
        """Validate document set against required checklist"""
        
        process = process_info.get('process')
        entity_type = process_info.get('entity_type')
        
        if process not in self.process_requirements:
            return {
                'status': 'unknown_process',
                'missing_documents': [],
                'present_documents': [],
                'completeness_score': 0.0
            }
        
        # Get required documents for this process/entity type
        if isinstance(self.process_requirements[process], dict):
            required_docs = self.process_requirements[process].get(entity_type, [])
        else:
            required_docs = self.process_requirements[process]
        
        # Get present document types
        present_docs = [doc['classification']['type'] for doc in documents 
                       if doc['classification']['confidence'] >= 0.5]
        
        # Handle special cases for registers
        present_set = set(present_docs)
        required_set = set(required_docs)
        
        # If combined register is present, it satisfies both individual registers
        if "Register of Members and Directors" in present_set:
            if "Register of Members" in required_set:
                present_set.add("Register of Members")
            if "Register of Directors" in required_set:
                present_set.add("Register of Directors")
        
        # Handle resolution equivalencies
        if any(res in present_set for res in ["Board Resolution", "Shareholder Resolution"]):
            present_set.add("Board Resolution")  # Either type satisfies requirement
        
        # Calculate missing documents
        missing_docs = list(required_set - present_set)
        
        # Calculate completeness score
        completeness_score = (len(required_set) - len(missing_docs)) / len(required_set) if required_docs else 1.0
        
        return {
            'status': 'complete' if not missing_docs else 'incomplete',
            'required_documents': required_docs,
            'present_documents': list(present_set & required_set),
            'missing_documents': missing_docs,
            'completeness_score': completeness_score,
            'total_required': len(required_docs),
            'total_present': len(present_set & required_set)
        }
    
    def generate_checklist_message(self, process_info: Dict, checklist_result: Dict) -> str:
        """Generate user-friendly checklist message"""
        
        process = process_info.get('process', 'Unknown')
        entity_type = process_info.get('entity_type', '')
        
        if checklist_result['status'] == 'complete':
            return f"All required documents for {process} are present."
        
        missing = checklist_result['missing_documents']
        total_required = checklist_result['total_required']
        total_present = checklist_result['total_present']
        
        message = f" Document checklist for {process}"
        if entity_type:
            message += f" ({entity_type})"
        
        message += f": {total_present} of {total_required} required documents uploaded.\n\n"
        
        if missing:
            message += "Missing documents:\n"
            for doc in missing:
                message += f"• {doc}\n"
        
        return message
