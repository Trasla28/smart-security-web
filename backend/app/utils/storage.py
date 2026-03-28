"""File storage utilities for ticket attachments."""
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB


async def save_file(
    file: UploadFile,
    tenant_id: uuid.UUID,
    ticket_id: uuid.UUID,
    storage_path: str,
) -> tuple[str, int, str]:
    """Persist an uploaded file to disk.

    Args:
        file: The FastAPI ``UploadFile`` instance.
        tenant_id: Owning tenant UUID (used to partition storage).
        ticket_id: Owning ticket UUID.
        storage_path: Root directory where files are stored.

    Returns:
        A 3-tuple of ``(file_path, file_size, mime_type)``.

    Raises:
        HTTPException 400: If the MIME type is not allowed or the file exceeds 10 MB.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipo de archivo no permitido. Solo PDF, Word, Excel, JPG, PNG, WEBP.",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Archivo demasiado grande. Máximo 10 MB.",
        )

    # Store in: {storage_path}/{tenant_id}/{ticket_id}/{uuid}_{filename}
    dir_path = Path(storage_path) / str(tenant_id) / str(ticket_id)
    dir_path.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = str(dir_path / safe_filename)

    with open(file_path, "wb") as fh:
        fh.write(content)

    return file_path, len(content), file.content_type


def delete_file(file_path: str) -> None:
    """Remove a file from disk, silently ignoring missing files."""
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass


def generate_signed_url(
    file_path: str,
    attachment_id: uuid.UUID,  # noqa: ARG001  kept for signature clarity
    expires_in: int = 3600,
) -> str:
    """Generate a signed download token for a stored file.

    Args:
        file_path: Absolute path of the file on disk.
        attachment_id: UUID of the attachment record (for future use).
        expires_in: Token validity in seconds (default 1 hour).

    Returns:
        An opaque HMAC-signed token string.
    """
    from app.utils.security import generate_signed_url_token

    return generate_signed_url_token(file_path, expires_in)
