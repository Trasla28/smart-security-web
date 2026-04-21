"""Signed file download endpoint."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.utils.security import verify_signed_url_token

router = APIRouter()


@router.get("/download")
async def download_file(
    path: str = Query(...),
    token: str = Query(...),
) -> FileResponse:
    """Serve a stored attachment file after validating its signed token."""
    if not verify_signed_url_token(path, token):
        raise HTTPException(status_code=403, detail="Token inválido o expirado")

    file = Path(path)
    if not file.exists() or not file.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(path=str(file), filename=file.name)
