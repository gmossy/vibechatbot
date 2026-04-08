import os
from typing import Optional
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from PIL import Image
import pytesseract

class RAGService:
    def __init__(self, persist_dir: str = "./data/faiss_index"):
        self.persist_dir = persist_dir
        # Using a fast, standard local embedding model
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store: Optional[FAISS] = None
        
        # Load existing index if present
        if os.path.exists(self.persist_dir) and os.path.exists(os.path.join(self.persist_dir, "index.faiss")):
            try:
                self.vector_store = FAISS.load_local(
                    folder_path=self.persist_dir, 
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True # Required for local loading from disk natively in python
                )
            except Exception as e:
                print(f"FAISS index could not be loaded: {e}")

    def ingest_file(self, file_path: str, filename: str):
        # Determine loader by extension
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
            documents = loader.load()
        elif ext in [".doc", ".docx"]:
            loader = Docx2txtLoader(file_path)
            documents = loader.load()
        elif ext in [".c", ".py", ".cpp", ".txt", ".md"]:
            loader = TextLoader(file_path, autodetect_encoding=True)
            documents = loader.load()
        elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
            # Native Tesseract OCR for uploading images into the vector memory
            extracted_text = pytesseract.image_to_string(Image.open(file_path))
            doc = Document(
                page_content=extracted_text,
                metadata={"source": filename}
            )
            documents = [doc]
        else:
            raise ValueError(f"Unsupported file type for ingestion: {ext}")

        # Chunk documents algorithmically
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)

        if not chunks:
            return 0

        # Add to FAISS Vector Store
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        else:
            self.vector_store.add_documents(chunks)
        
        # Persist automatically to disk
        os.makedirs(self.persist_dir, exist_ok=True)
        self.vector_store.save_local(self.persist_dir)

        return len(chunks)

    def retrieve_context(self, query: str, k: int = 4) -> str:
        if self.vector_store is None:
            return ""
        
        # Similarity search
        docs = self.vector_store.similarity_search(query, k=k)
        if not docs:
            return ""

        context_parts = []
        for doc in docs:
            source = doc.metadata.get("source", "Unknown File")
            # Extract just filename for cleanliness
            basename = os.path.basename(source)
            context_parts.append(f"--- Document Content from {basename} ---\n{doc.page_content}")
            
        return "\n\n".join(context_parts)

# Expose a singleton instance globally for the API layers
rag_service = RAGService()
