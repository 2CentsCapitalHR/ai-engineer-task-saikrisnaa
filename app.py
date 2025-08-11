import streamlit as st
import tempfile
import os
from pathlib import Path
import json
from typing import List, Dict

from core.rag import RAGSystem
from core.classify import DocumentClassifier
from core.checklist import ChecklistValidator
from core.redflags import RedFlagDetector
from core.docx_utils import DocxProcessor
from core.report import ReportGenerator
from core.llm import LLMInterface

# Configure Streamlit
st.set_page_config(
    page_title="ADGM Corporate Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def initialize_system():
    """Initialize all system components"""
    try:
        rag = RAGSystem()
        rag.initialize_vectorstore()
        
        llm = LLMInterface()
        classifier = DocumentClassifier(rag, llm)
        validator = ChecklistValidator(rag)
        detector = RedFlagDetector(rag, llm)
        processor = DocxProcessor()
        reporter = ReportGenerator()
        
        return {
            'rag': rag,
            'classifier': classifier,
            'validator': validator,
            'detector': detector,
            'processor': processor,
            'reporter': reporter,
            'llm': llm
        }
    except Exception as e:
        st.error(f"Failed to initialize system: {str(e)}")
        st.stop()

def main():
    st.title("⚖️ ADGM Corporate Agent")
    st.markdown("**AI-Powered Document Intelligence for ADGM Compliance**")
    
    # Initialize system
    with st.spinner("Initializing ADGM Corporate Agent..."):
        components = initialize_system()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        st.info("Upload .docx documents for ADGM compliance review")
        
        max_files = st.number_input("Max files", min_value=1, max_value=50, value=20)
        confidence_threshold = st.slider("Classification confidence threshold", 0.0, 1.0, 0.5)
    
    # File upload
    uploaded_files = st.file_uploader(
        "Upload ADGM Documents (.docx)",
        type=["docx"],
        accept_multiple_files=True,
        help="Upload Articles of Association, Memorandum, Resolutions, UBO Declarations, etc."
    )
    
    if uploaded_files:
        st.success(f"Uploaded {len(uploaded_files)} files")
        
        # Display file list
        with st.expander("Uploaded Files"):
            for file in uploaded_files:
                st.write(f"📄 {file.name} ({file.size:,} bytes)")
    
    # Process documents
    if st.button("🔍 Run ADGM Compliance Review", disabled=not uploaded_files):
        process_documents(uploaded_files, components, confidence_threshold)

def process_documents(uploaded_files: List, components: Dict, confidence_threshold: float):
    """Process uploaded documents through the ADGM compliance pipeline"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Save uploaded files
        file_paths = []
        for file in uploaded_files:
            file_path = tmpdir_path / file.name
            with open(file_path, "wb") as f:
                f.write(file.read())
            file_paths.append(file_path)
        
        # Process each document
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_docs = []
        
        for i, file_path in enumerate(file_paths):
            status_text.text(f"Processing: {file_path.name}")
            
            # Parse document
            try:
                text, metadata = components['processor'].extract_text(file_path)
                
                # Classify document
                classification = components['classifier'].classify(
                    filename=file_path.name,
                    text=text,
                    metadata=metadata
                )
                
                processed_docs.append({
                    'path': file_path,
                    'name': file_path.name,
                    'text': text,
                    'metadata': metadata,
                    'classification': classification
                })
                
            except Exception as e:
                st.error(f"Error processing {file_path.name}: {str(e)}")
                continue
            
            progress_bar.progress((i + 1) / len(file_paths))
        
        if not processed_docs:
            st.error("No documents could be processed successfully")
            return
        
        # Infer process and validate checklist
        status_text.text("Analyzing document set...")
        process_info = components['validator'].infer_process(processed_docs)
        checklist_result = components['validator'].validate_checklist(processed_docs, process_info)
        
        # Detect red flags
        status_text.text("Detecting compliance issues...")
        all_issues = []
        reviewed_paths = []
        
        for doc in processed_docs:
            issues = components['detector'].detect_issues(doc, process_info)
            all_issues.extend(issues)
            
            # Add comments to document
            if issues:
                reviewed_path = components['processor'].add_comments(doc['path'], issues)
                reviewed_paths.append({
                    'original': doc['name'],
                    'reviewed_path': reviewed_path
                })
            else:
                reviewed_paths.append({
                    'original': doc['name'],
                    'reviewed_path': doc['path']
                })
        
        # Generate report
        status_text.text("Generating report...")
        report = components['reporter'].generate_report(
            process_info=process_info,
            documents=processed_docs,
            checklist_result=checklist_result,
            issues=all_issues
        )
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Display results
        display_results(report, reviewed_paths, process_info)

def display_results(report: Dict, reviewed_paths: List[Dict], process_info: Dict):
    """Display analysis results"""
    
    st.header("📊 Analysis Results")
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Process Detected", process_info.get('process', 'Unknown'))
    
    with col2:
        st.metric("Documents Uploaded", report.get('documents_uploaded', 0))
    
    with col3:
        issues_count = len(report.get('issues_found', []))
        st.metric("Issues Found", issues_count)
    
    with col4:
        missing_count = len(report.get('missing_documents', []))
        st.metric("Missing Documents", missing_count)
    
    # Missing documents alert
    if report.get('missing_documents'):
        st.error("Missing Required Documents")
        for doc in report['missing_documents']:
            st.write(f"• {doc}")
    
    # Issues summary
    if report.get('issues_found'):
        st.subheader(" Compliance Issues")
        
        # Group by severity
        high_issues = [i for i in report['issues_found'] if i.get('severity') == 'High']
        medium_issues = [i for i in report['issues_found'] if i.get('severity') == 'Medium']
        low_issues = [i for i in report['issues_found'] if i.get('severity') == 'Low']
        
        if high_issues:
            st.error(f"High Priority Issues ({len(high_issues)})")
            for issue in high_issues:
                st.write(f"📄 **{issue.get('document')}**: {issue.get('issue')}")
        
        if medium_issues:
            st.warning(f"Medium Priority Issues ({len(medium_issues)})")
            for issue in medium_issues:
                st.write(f"📄 **{issue.get('document')}**: {issue.get('issue')}")
        
        if low_issues:
            st.info(f"Low Priority Issues ({len(low_issues)})")
            for issue in low_issues:
                st.write(f"📄 **{issue.get('document')}**: {issue.get('issue')}")
    else:
        st.success("No compliance issues detected!")
    
    # Download section
    st.subheader(" Download Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Reviewed Documents")
        for item in reviewed_paths:
            if item['reviewed_path'].exists():
                with open(item['reviewed_path'], 'rb') as f:
                    st.download_button(
                        label=f"📄 {item['original']}",
                        data=f.read(),
                        file_name=f"reviewed_{item['original']}",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
    
    with col2:
        st.subheader("Analysis Report")
        report_json = json.dumps(report, indent=2)
        st.download_button(
            label="Download JSON Report",
            data=report_json,
            file_name="adgm_compliance_report.json",
            mime="application/json"
        )
        
        # Display report preview
        with st.expander("View Report Details"):
            st.json(report)

if __name__ == "__main__":
    main()
