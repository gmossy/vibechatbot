import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Dict, Any
from app.services.rag_service import RAGService
from app.core.security import get_current_user

router = APIRouter()

UPLOAD_DIR = "./temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", summary="Ingest Document into RAG", response_description="Ingestion Status Report")
async def upload_document(
    file: UploadFile = File(..., description="The document file (PDF, DOCX, XLSX, TXT, or Source Code)."),
    project_id: str = Form("default_project", description="Logical project grouping for document isolation."),
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    ### Overview
    Uploads a document to the **Docling-powered RAG Pipeline**.
    
    ### Process:
    1.  **Ingestion**: Detects format (Office, PDF, Code, XML, Image).
    2.  **Structuring**: Extracts layout and tables using Docling 2.x.
    3.  **Vectorization**: Embeds chunks using `all-MiniLM-L6-v2`.
    4.  **Indexing**: Adds to a FAISS vector store scoped by `user_id` and `project_id`.
    
    ### Responses:
    - **200 OK**: Success with the count of semantic chunks created.
    - **400 Bad Request**: Unsupported format or parsing error.
    - **500 Internal Server Error**: Infrastructure or ML model failure.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # Stream file to local disk buffer
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Push through the ML ingestion pipeline
        # Initialize logic boundaries natively
        rag_service = RAGService(user_id=user_id, project_id=project_id)
        chunks_created = rag_service.ingest_file(file_path, file.filename)
        
        # Once vectorized, original isn't needed by FAISS so we do pristine cleanup
        os.remove(file_path)
        
        return {
            "status": "success", 
            "filename": file.filename, 
            "chunks_processed": chunks_created,
            "message": "File successfully ingested and embedded into FAISS vector database."
        }
    except ValueError as ve:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))
