import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.embeddings import OpenAIEmbeddings
import chromadb

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self, persist_dir: str = "./data/vector_store"):
        self.persist_dir = persist_dir
        self.vectorstore = None
        self.embeddings = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize embeddings with fallback"""
        try:
            if os.getenv("OPENAI_API_KEY"):
                self.embeddings = OpenAIEmbeddings()
                logger.info("Using OpenAI embeddings")
            else:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                logger.info("Using HuggingFace embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            # Fallback to HuggingFace
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
    
    def initialize_vectorstore(self):
        """Initialize or load existing vectorstore with ADGM knowledge"""
        os.makedirs(self.persist_dir, exist_ok=True)
        
        try:
            # Try to load existing vectorstore
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
            
            # Check if vectorstore has data
            if self.vectorstore._collection.count() == 0:
                logger.info("Empty vectorstore detected, seeding with ADGM knowledge")
                self._seed_knowledge_base()
            else:
                logger.info(f"Loaded existing vectorstore with {self.vectorstore._collection.count()} documents")
                
        except Exception as e:
            logger.error(f"Error loading vectorstore: {e}")
            self._seed_knowledge_base()
    
    def _seed_knowledge_base(self):
        """Seed vectorstore with ADGM regulatory knowledge"""
        knowledge_items = self._get_adgm_knowledge()
        
        # Create documents
        documents = []
        for item in knowledge_items:
            doc = Document(
                page_content=item["content"],
                metadata=item["metadata"]
            )
            documents.append(doc)
        
        # Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        split_docs = text_splitter.split_documents(documents)
        
        # Create vectorstore
        self.vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            persist_directory=self.persist_dir
        )
        
        logger.info(f"Seeded vectorstore with {len(split_docs)} document chunks")
    
    def _get_adgm_knowledge(self) -> List[Dict[str, Any]]:
        """Get ADGM regulatory knowledge base"""
        return [
            {
                "content": """ADGM Registration & Incorporation Requirements:
                Companies incorporating in ADGM must submit specific documentation including:
                - Articles of Association (AoA) compliant with ADGM template
                - Memorandum of Association stating company purpose and structure
                - Incorporation Application Form with all required particulars
                - Ultimate Beneficial Owner (UBO) Declaration with complete ownership details
                - Register of Members showing initial shareholding
                - Register of Directors with director particulars and appointments
                - Evidence of director appointments through Board or Shareholder Resolutions
                - Registered office address within ADGM jurisdiction
                - Statement of capital or guarantee as applicable
                
                All documents must reference ADGM jurisdiction and comply with Companies Regulations 2020.""",
                "metadata": {
                    "source": "ADGM Companies Regulations 2020",
                    "category": "incorporation",
                    "citation_id": "ADGM-REG-2020-S6",
                    "url": "https://www.adgm.com/registration-authority/registration-and-incorporation"
                }
            },
            {
                "content": """ADGM Jurisdiction Requirements:
                All corporate documents must specify ADGM Courts jurisdiction for dispute resolution.
                References to UAE Federal Courts, Dubai Courts, or other non-ADGM jurisdictions are non-compliant.
                Governing law clauses should reference ADGM laws where applicable.
                
                Correct jurisdiction clause example: "This agreement shall be governed by ADGM laws and 
                any disputes shall be subject to the exclusive jurisdiction of ADGM Courts."
                
                Registered office must be within ADGM boundaries - addresses outside ADGM are invalid.""",
                "metadata": {
                    "source": "ADGM Courts Framework",
                    "category": "jurisdiction",
                    "citation_id": "ADGM-COURTS-JURIS",
                    "url": "https://www.adgm.com/courts"
                }
            },
            {
                "content": """Beneficial Ownership & Control Regulations:
                UBO declarations must include complete particulars:
                - Full legal name and any known aliases
                - Date and place of birth
                - Nationality and passport/ID details
                - Residential address
                - Nature and extent of beneficial ownership or control
                - Date from which beneficial ownership/control commenced
                
                Companies must maintain current UBO records and notify ADGM of changes within prescribed timeframes.
                Failure to maintain accurate UBO records constitutes regulatory breach.""",
                "metadata": {
                    "source": "ADGM Beneficial Ownership Regulations 2022",
                    "category": "beneficial_ownership",
                    "citation_id": "ADGM-BOC-2022",
                    "url": "https://www.adgm.com/legal-framework/guidance-and-policy-statements"
                }
            },
            {
                "content": """Required Corporate Registers:
                ADGM companies must maintain the following registers:
                - Register of Members: Details of all shareholders, share holdings, transfer dates
                - Register of Directors: Full particulars of all directors, appointment dates, resignations
                
                Registers may be combined into single "Register of Members and Directors" document.
                All register entries must be dated and signed by authorized persons.
                Registers must be available for inspection and filed with annual returns.""",
                "metadata": {
                    "source": "ADGM Companies Regulations",
                    "category": "corporate_records",
                    "citation_id": "ADGM-REG-REGISTERS",
                    "url": "https://www.adgm.com/registration-authority/registration-and-incorporation"
                }
            },
            {
                "content": """Articles of Association Requirements:
                AoA must contain mandatory provisions covering:
                - Company name and registered office in ADGM
                - Objects and purposes of the company
                - Share capital structure or guarantee provisions
                - Director appointment procedures and powers
                - Shareholder rights and meeting procedures
                - Share transfer restrictions and procedures
                - Winding up provisions
                
                Articles must be signed by all subscribers and witnessed.
                Non-standard provisions require ADGM Registration Authority approval.""",
                "metadata": {
                    "source": "ADGM Model Articles",
                    "category": "articles",
                    "citation_id": "ADGM-MODEL-ARTICLES",
                    "url": "https://en.adgm.thomsonreuters.com/rulebook/7-company-incorporation-package"
                }
            },
            {
                "content": """Document Formatting and Execution Requirements:
                All corporate documents must:
                - Include proper signatory blocks with name, title, and date
                - Be executed by authorized persons with proper capacity
                - Include witness signatures where required by law
                - Use binding language ("shall", "must") rather than permissive ("may", "should")
                - Reference correct legal names of parties
                - Include proper document dating
                
                Improper execution may invalidate legal effect of documents.""",
                "metadata": {
                    "source": "ADGM Document Standards",
                    "category": "execution",
                    "citation_id": "ADGM-DOC-STANDARDS",
                    "url": "https://www.adgm.com/registration-authority"
                }
            }
        ]
    
    def search(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Document]:
        """Search the knowledge base"""
        if not self.vectorstore:
            logger.warning("Vectorstore not initialized")
            return []
        
        try:
            if filter_metadata:
                return self.vectorstore.similarity_search(query, k=k, filter=filter_metadata)
            else:
                return self.vectorstore.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def add_documents(self, documents: List[Document]):
        """Add new documents to the knowledge base"""
        if not self.vectorstore:
            logger.error("Vectorstore not initialized")
            return
        
        try:
            self.vectorstore.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to vectorstore")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
