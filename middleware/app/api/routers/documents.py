import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
from app.services.rag_service import rag_service

router = APIRouter()

UPLOAD_DIR = "./temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Receives File uploads (PDF, Word, Code) -> Saves -> Chunks -> Embeds in FAISS -> Cleans up
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # Stream file to local disk buffer
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Push through the ML ingestion pipeline
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
