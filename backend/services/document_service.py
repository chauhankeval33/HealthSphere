import logging

logger = logging.getLogger(__name__)
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

BUCKET_NAME = "healthsphere-reports"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


async def upload_patient_document(
    client,
    user_id: str,
    patient_id: str,
    file: UploadFile,
):
    # Validate file extension and MIME type.
    extension = Path(file.filename or "").suffix.lower()

    allowed_extensions = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    expected_mime = allowed_extensions.get(extension)

    if (
        expected_mime is None
        or file.content_type != expected_mime
        or file.content_type not in ALLOWED_MIME_TYPES
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPEG, PNG and WEBP files are allowed",
        )

    # Read at most 10 MB + 1 byte to detect oversized files.
    file_content = await file.read(MAX_FILE_SIZE + 1)

    if not file_content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size cannot exceed 10 MB",
        )

    # Basic file-signature validation.
    signatures = {
        "application/pdf": b"%PDF-",
        "image/jpeg": b"\xff\xd8\xff",
        "image/png": b"\x89PNG\r\n\x1a\n",
        "image/webp": b"RIFF",
    }

    if not file_content.startswith(signatures[file.content_type]):
        raise HTTPException(
            status_code=400,
            detail="File content does not match its declared type",
        )

    if file.content_type == "image/webp" and file_content[8:12] != b"WEBP":
        raise HTTPException(
            status_code=400,
            detail="Invalid WEBP file",
        )

    safe_extension = extension
    stored_name = f"{uuid.uuid4().hex}{safe_extension}"

    storage_path = f"{user_id}/{patient_id}/{stored_name}"

    upload_completed = False

    try:
        # Upload to private Supabase Storage.
        client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_content,
            file_options={
                "content-type": file.content_type,
                "upsert": "false",
            },
        )

        upload_completed = True

        # Save document metadata in PostgreSQL.
        document_data = {
            "owner_id": user_id,
            "patient_id": patient_id,
            "file_name": Path(file.filename).name,
            "storage_path": storage_path,
            "mime_type": file.content_type,
            "file_size": len(file_content),
            "processing_status": "pending",
        }

        response = (
            client.table("healthsphere_documents")
            .insert(document_data)
            .execute()
        )

        if not response.data:
            raise RuntimeError("Document metadata was not saved")

        return response.data[0]

    except Exception as exc:
        logger.exception("HealthSphere document upload failed")
        # Roll back Storage upload if database insertion fails.
        if upload_completed:
            try:
                client.storage.from_(BUCKET_NAME).remove(
                    [storage_path]
                )
            except Exception:
                pass

        if isinstance(exc, HTTPException):
            raise

        raise HTTPException(
            status_code=500,
            detail="Unable to upload document",
        )
