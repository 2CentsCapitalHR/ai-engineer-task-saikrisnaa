from typing import Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        pass
    
    def generate_report(self, 
                       process_info: Dict, 
                       documents: List[Dict], 
                       checklist_result: Dict, 
                       issues: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        
        # Count issues by severity
        issue_counts = {'High': 0, 'Medium': 0, 'Low': 0}
        for issue in issues:
            severity = issue.get('severity', 'Medium')
            issue_counts[severity] = issue_counts.get(severity, 0) + 1
        
        # Document summary
        doc_summary = []
        for doc in documents:
            classification = doc['classification']
            doc_summary.append({
                'filename': doc['name'],
                'detected_type': classification['type'],
                'confidence': round(classification['confidence'], 2),
                'classification_method': classification.get('method', 'unknown')
            })
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            process_info, checklist_result, issues
        )
        
        # Create comprehensive report
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'process_detected': process_info.get('process', 'Unknown'),
            'entity_type': process_info.get('entity_type'),
            'process_confidence': process_info.get('confidence', 0),
            
            # Document analysis
            'documents_uploaded': len(documents),
            'document_summary': doc_summary,
            
            # Checklist validation
            'checklist_status': checklist_result.get('status', 'unknown'),
            'required_documents': checklist_result.get('required_documents', []),
            'present_documents': checklist_result.get('present_documents', []),
            'missing_documents': checklist_result.get('missing_documents', []),
            'completeness_score': round(checklist_result.get('completeness_score', 0), 2),
            
            # Issues analysis
            'total_issues': len(issues),
            'issues_by_severity': issue_counts,
            'issues_found': self._format_issues(issues),
            
            # Recommendations
            'recommendations': recommendations,
            
            # Compliance score
            'overall_compliance_score': self._calculate_compliance_score(
                checklist_result, issue_counts
            )
        }
        
        return report
    
    def _format_issues(self, issues: List[Dict]) -> List[Dict]:
        """Format issues for report output"""
        formatted_issues = []
        
        for issue in issues:
            formatted_issue = {
                'document': issue.get('document', 'Unknown'),
                'section': issue.get('section_hint', 'General'),
                'issue': issue.get('issue', 'Unknown issue'),
                'severity': issue.get('severity', 'Medium'),
                'citations': issue.get('citations', []),
                'suggestion': issue.get('suggestion', '')
            }
            formatted_issues.append(formatted_issue)
        
        # Sort by severity (High first)
        severity_order = {'High': 0, 'Medium': 1, 'Low': 2}
        formatted_issues.sort(key=lambda x: severity_order.get(x['severity'], 1))
        
        return formatted_issues
    
    def _generate_recommendations(self, 
                                 process_info: Dict, 
                                 checklist_result: Dict, 
                                 issues: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Missing documents recommendations
        missing_docs = checklist_result.get('missing_documents', [])
        if missing_docs:
            recommendations.append(
                f"Complete document set by preparing: {', '.join(missing_docs)}"
            )
        
        # High severity issues
        high_issues = [i for i in issues if i.get('severity') == 'High']
        if high_issues:
            recommendations.append(
                f"Address {len(high_issues)} high-priority compliance issues before submission"
            )
        
        # Jurisdiction issues
        jurisdiction_issues = [i for i in issues if 'jurisdiction' in i.get('section_hint', '').lower()]
        if jurisdiction_issues:
            recommendations.append(
                "Review and update jurisdiction clauses to reference ADGM Courts exclusively"
            )
        
        # UBO issues
        ubo_issues = [i for i in issues if 'ubo' in i.get('issue', '').lower()]
        if ubo_issues:
            recommendations.append(
                "Complete UBO declaration with all required particulars per ADGM regulations"
            )
        
        # Process-specific recommendations
        process = process_info.get('process')
        if process == 'Company Incorporation':
            if checklist_result.get('completeness_score', 0) < 1.0:
                recommendations.append(
                    "Ensure all incorporation documents are prepared before ADGM submission"
                )
        
        # General recommendations
        if not recommendations:
            if issues:
                recommendations.append("Address identified issues to improve compliance")
            else:
                recommendations.append("Documents appear compliant - ready for submission")
        
        return recommendations
    
    def _calculate_compliance_score(self, checklist_result: Dict, issue_counts: Dict) -> float:
        """Calculate overall compliance score (0-100)"""
        
        # Base score from checklist completeness (60% weight)
        completeness_score = checklist_result.get('completeness_score', 0) * 60
        
        # Issue penalty (40% weight)
        total_issues = sum(issue_counts.values())
        if total_issues == 0:
            issue_score = 40
        else:
            # Weighted penalty by severity
            penalty = (
                issue_counts.get('High', 0) * 10 +
                issue_counts.get('Medium', 0) * 5 +
                issue_counts.get('Low', 0) * 2
            )
            issue_score = max(0, 40 - penalty)
        
        total_score = completeness_score + issue_score
        return round(min(100, max(0, total_score)), 1)
    
    def generate_summary_message(self, report: Dict) -> str:
        """Generate user-friendly summary message"""
        
        process = report.get('process_detected', 'Unknown')
        completeness = report.get('completeness_score', 0)
        total_issues = report.get('total_issues', 0)
        compliance_score = report.get('overall_compliance_score', 0)
        
        message = f" ADGM Compliance Analysis Complete\n\n"
        message += f"Process: {process}\n"
        message += f"Document completeness: {completeness:.0%}\n"
        message += f"Issues found: {total_issues}\n"
        message += f"Compliance score: {compliance_score}/100\n\n"
        
        if report.get('missing_documents'):
            message += " Missing required documents\n"
        
        if total_issues > 0:
            high_issues = report.get('issues_by_severity', {}).get('High', 0)
            if high_issues > 0:
                message += f" {high_issues} high-priority issues require attention\n"
        
        if compliance_score >= 80:
            message += " Good compliance level"
        elif compliance_score >= 60:
            message += " Moderate compliance - address issues before submission"
        else:
            message += " Low compliance - significant issues need resolution"
        
        return message
