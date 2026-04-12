import mimetypes
import os
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.security import get_current_user

router = APIRouter()

_GENERATED_DIR = os.path.abspath(os.path.join(os.getcwd(), "generated_files"))


def _safe_join_generated(filename: str) -> str:
    candidate = os.path.abspath(os.path.join(_GENERATED_DIR, filename))
    if not candidate.startswith(_GENERATED_DIR + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return candidate


@router.get("/generated_files", summary="List generated files")
async def list_generated_files(_user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    if not os.path.isdir(_GENERATED_DIR):
        return {"files": []}

    files: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(_GENERATED_DIR)):
        if name.startswith("."):
            continue
        full_path = os.path.join(_GENERATED_DIR, name)
        if not os.path.isfile(full_path):
            continue

        st = os.stat(full_path)
        mime, _ = mimetypes.guess_type(full_path)
        url_base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
        url = f"{url_base}{settings.API_V1_STR}/generated_files/{name}" if url_base else ""
        files.append(
            {
                "name": name,
                "size_bytes": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                "mime_type": mime or "application/octet-stream",
                "download_url": url,
            }
        )

    return {"files": files}


@router.get("/generated_files/{filename}", summary="Download a generated file")
async def download_generated_file(filename: str, _user_id: str = Depends(get_current_user)):
    full_path = _safe_join_generated(filename)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    mime, _ = mimetypes.guess_type(full_path)
    return FileResponse(
        full_path,
        media_type=mime or "application/octet-stream",
        filename=os.path.basename(full_path),
    )
