
import logging

from fastapi import HTTPException

from backend.services.document_processor import (
    process_pdf,
    process_image,
)

from backend.services.text_chunker import chunk_text

from backend.services.embedding_service import (
    embed_document_chunks,
)


logger = logging.getLogger(__name__)

BUCKET_NAME = "healthsphere-reports"

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def index_patient_document(
    client,
    user_id: str,
    patient_id: str,
    document_id: str,
) -> dict:
    """
    Extract document content, generate chunks and embeddings,
    and store them in Supabase for RAG retrieval.

    PDFs use native extraction with OCR fallback.
    Images use Tesseract OCR.
    """

    try:
        # 1. Verify document ownership.
        response = (
            client.table("healthsphere_documents")
            .select(
                "id, patient_id, owner_id, storage_path, "
                "file_name, mime_type"
            )
            .eq("id", document_id)
            .eq("patient_id", patient_id)
            .eq("owner_id", user_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        document = response.data[0]
        mime_type = document["mime_type"]

        # 2. Download document from private Storage.
        file_content = client.storage.from_(
            BUCKET_NAME
        ).download(document["storage_path"])

        # 3. Extract searchable text.
        if mime_type == "application/pdf":

            result = process_pdf(file_content)

            if not result["has_text"]:
                raise ValueError(
                    "PDF contains no extractable text"
                )

            extracted_text = result["extracted_text"]

            metadata = {
                "file_name": document["file_name"],
                "document_type": "pdf",
                "total_pages": result["total_pages"],
                "ocr_status": result["ocr_status"],
                "ocr_pages": result["ocr_pages"],
            }

        elif mime_type in IMAGE_MIME_TYPES:

            image_result = process_image(
                file_content=file_content,
                mime_type=mime_type,
            )

            if not image_result["has_text"]:
                raise ValueError(
                    "Image contains no extractable text"
                )

            extracted_text = image_result[
                "extracted_text"
            ]

            metadata = {
                "file_name": document["file_name"],
                "document_type": "image",
                "image_format": image_result["format"],
                "ocr_source": "tesseract",
                "ocr_status": image_result["ocr_status"],
            }

        else:
            raise ValueError(
                "Unsupported document type"
            )

        # 4. Split extracted text into chunks.
        chunks = chunk_text(
            extracted_text,
            chunk_size=1200,
            overlap=200,
        )

        if not chunks:
            raise ValueError(
                "No searchable text chunks were generated"
            )

        # 5. Generate embeddings.
        embedded_chunks = embed_document_chunks(chunks)

        if not embedded_chunks:
            raise ValueError(
                "Unable to generate document embeddings"
            )

        # 6. Prepare database records.
        records = []

        for chunk in embedded_chunks:
            records.append({
                "owner_id": user_id,
                "patient_id": patient_id,
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": chunk["embedding"],
                "metadata": metadata,
            })

        # 7. Remove previous index only after new embeddings
        # have been generated successfully.
        (
            client.table("healthsphere_document_chunks")
            .delete()
            .eq("document_id", document_id)
            .eq("owner_id", user_id)
            .execute()
        )

        # 8. Save new chunks and embeddings.
        saved = (
            client.table("healthsphere_document_chunks")
            .insert(records)
            .execute()
        )

        if not saved.data:
            raise RuntimeError(
                "Unable to save document embeddings"
            )

        return {
            "message": "Document indexed successfully",
            "document_id": document_id,
            "patient_id": patient_id,
            "file_name": document["file_name"],
            "total_chunks": len(saved.data),
            "embedding_dimensions": 768,
            "status": "indexed",
            "extraction_method": (
                "native_text_with_ocr_fallback"
                if mime_type == "application/pdf"
                else "tesseract_ocr"
            ),
        }

    except HTTPException:
        raise

    except ValueError:
        raise

    except Exception as exc:
        logger.exception(
            "HealthSphere document indexing failed"
        )

        raise RuntimeError(
            "Unable to index patient document"
        ) from exc
