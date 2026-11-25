
import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from backend.dependencies import get_current_user

from backend.services.document_service import (
    upload_patient_document,
)

from backend.services.document_processor import (
    process_pdf,
    process_image,
)

from backend.services.gemini_service import (
    analyze_medical_document,
    analyze_medical_image,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/patients",
    tags=["Patient Documents"],
)


BUCKET_NAME = "healthsphere-reports"

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def mark_document_processing_status(
    client,
    document_id: str,
    owner_id: str,
    status: str,
):
    """
    Safely update document processing status.
    Logging prevents a secondary database failure
    from hiding the original processing error.
    """

    try:
        (
            client.table("healthsphere_documents")
            .update({
                "processing_status": status
            })
            .eq("id", document_id)
            .eq("owner_id", owner_id)
            .execute()
        )

    except Exception:
        logger.exception(
            "Unable to update document processing status | "
            "Document: %s | Status: %s",
            document_id,
            status,
        )


# STEP 22: Upload patient document
@router.post("/{patient_id}/documents")
async def upload_document(
    patient_id: UUID,
    file: UploadFile = File(...),
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        patient_response = (
            client.table("healthsphere_patients")
            .select("id")
            .eq("id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not patient_response.data:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient ownership verification failed | "
            "Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to verify patient ownership",
        )

    try:
        document = await upload_patient_document(
            client=client,
            user_id=str(user.id),
            patient_id=str(patient_id),
            file=file,
        )

        logger.info(
            "Patient document uploaded | "
            "Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        return {
            "message": "Document uploaded successfully",
            "document": document,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient document upload failed | "
            "Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to upload patient document",
        )


# STEP 23: List patient documents
@router.get("/{patient_id}/documents")
def list_patient_documents(
    patient_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        patient_response = (
            client.table("healthsphere_patients")
            .select("id")
            .eq("id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not patient_response.data:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        response = (
            client.table("healthsphere_documents")
            .select(
                "id, patient_id, file_name, mime_type, "
                "file_size, processing_status, created_at"
            )
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .order("created_at", desc=True)
            .execute()
        )

        documents = response.data or []

        return {
            "patient_id": str(patient_id),
            "total_documents": len(documents),
            "documents": documents,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient document listing failed | "
            "Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve patient documents",
        )


# STEP 24: Generate secure document download URL
@router.get(
    "/{patient_id}/documents/{document_id}/download"
)
def download_patient_document(
    patient_id: UUID,
    document_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        response = (
            client.table("healthsphere_documents")
            .select("id, storage_path, file_name")
            .eq("id", str(document_id))
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        document = response.data[0]

        signed_response = (
            client.storage
            .from_(BUCKET_NAME)
            .create_signed_url(
                document["storage_path"],
                60,
            )
        )

        signed_url = (
            signed_response.get("signedURL")
            or signed_response.get("signedUrl")
        )

        if not signed_url:
            raise RuntimeError(
                "Signed URL was not generated"
            )

        logger.info(
            "Document download link generated | "
            "Document: %s | Owner: %s",
            document_id,
            user.id,
        )

        return {
            "message": "Download link generated successfully",
            "file_name": document["file_name"],
            "download_url": signed_url,
            "expires_in_seconds": 60,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Document download link generation failed | "
            "Document: %s | Owner: %s",
            document_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to generate document download link",
        )


# STEP 25: Delete patient document
@router.delete(
    "/{patient_id}/documents/{document_id}"
)
def delete_patient_document(
    patient_id: UUID,
    document_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        response = (
            client.table("healthsphere_documents")
            .select("id, storage_path")
            .eq("id", str(document_id))
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        document = response.data[0]

        client.storage.from_(
            BUCKET_NAME
        ).remove([
            document["storage_path"]
        ])

        (
            client.table("healthsphere_documents")
            .delete()
            .eq("id", str(document_id))
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        logger.info(
            "Patient document deleted | "
            "Document: %s | Patient: %s | Owner: %s",
            document_id,
            patient_id,
            user.id,
        )

        return {
            "message": "Document deleted successfully",
            "document_id": str(document_id),
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient document deletion failed | "
            "Document: %s | Patient: %s | Owner: %s",
            document_id,
            patient_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to delete document",
        )


# STEP 27: Process stored patient document
@router.post(
    "/{patient_id}/documents/{document_id}/process"
)
def process_patient_document(
    patient_id: UUID,
    document_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        response = (
            client.table("healthsphere_documents")
            .select(
                "id, storage_path, file_name, mime_type"
            )
            .eq("id", str(document_id))
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        document = response.data[0]

        mark_document_processing_status(
            client,
            str(document_id),
            str(user.id),
            "processing",
        )

        file_content = client.storage.from_(
            BUCKET_NAME
        ).download(document["storage_path"])

        mime_type = document["mime_type"]

        if mime_type == "application/pdf":
            result = process_pdf(file_content)

        elif mime_type in IMAGE_MIME_TYPES:
            result = process_image(
                file_content,
                mime_type,
            )

        else:
            raise ValueError(
                "Unsupported document type"
            )

        mark_document_processing_status(
            client,
            str(document_id),
            str(user.id),
            "completed",
        )

        logger.info(
            "Patient document processed | "
            "Document: %s | Owner: %s",
            document_id,
            user.id,
        )

        return {
            "message": "Document processed successfully",
            "document_id": str(document_id),
            "file_name": document["file_name"],
            "processing_result": result,
        }

    except HTTPException:
        raise

    except ValueError:
        mark_document_processing_status(
            client,
            str(document_id),
            str(user.id),
            "failed",
        )

        logger.exception(
            "Document processing validation failed | "
            "Document: %s | Owner: %s",
            document_id,
            user.id,
        )

        raise HTTPException(
            status_code=400,
            detail="Unable to process document content",
        )

    except Exception:
        mark_document_processing_status(
            client,
            str(document_id),
            str(user.id),
            "failed",
        )

        logger.exception(
            "Patient document processing failed | "
            "Document: %s | Owner: %s",
            document_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process document",
        )


# STEP 34: Analyze PDF and image reports using Gemini
# Also save the generated analysis in Supabase.
@router.post(
    "/{patient_id}/documents/{document_id}/analyze"
)
def analyze_patient_document(
    patient_id: UUID,
    document_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        # 1. Verify document ownership.
        response = (
            client.table("healthsphere_documents")
            .select(
                "id, storage_path, file_name, mime_type"
            )
            .eq("id", str(document_id))
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        document = response.data[0]
        mime_type = document["mime_type"]

        # 2. Download the private document.
        file_content = client.storage.from_(
            BUCKET_NAME
        ).download(document["storage_path"])

        # 3. Process and analyze according to file type.
        if mime_type == "application/pdf":

            processing_result = process_pdf(
                file_content
            )

            if not processing_result["has_text"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "No readable text found in this PDF. "
                        "Scanned PDFs require OCR support."
                    ),
                )

            ai_result = analyze_medical_document(
                processing_result["extracted_text"]
            )

            document_type = "pdf"

        elif mime_type in IMAGE_MIME_TYPES:

            process_image(
                file_content,
                mime_type,
            )

            ai_result = analyze_medical_image(
                image_content=file_content,
                mime_type=mime_type,
            )

            document_type = "image"

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported document type",
            )

        # 4. Save analysis in Supabase.
        saved_analysis = (
            client.table("healthsphere_ai_analyses")
            .insert({
                "owner_id": str(user.id),
                "patient_id": str(patient_id),
                "document_id": str(document_id),
                "analysis_text": ai_result["analysis"],
                "model_name": ai_result["model"],
            })
            .execute()
        )

        if not saved_analysis.data:
            raise RuntimeError(
                "Unable to save AI analysis"
            )

        analysis_id = saved_analysis.data[0]["id"]

        logger.info(
            "Medical document analysis completed | "
            "Document: %s | Analysis: %s | Owner: %s",
            document_id,
            analysis_id,
            user.id,
        )

        # 5. Return analysis to frontend.
        return {
            "message": (
                "Document analyzed successfully and "
                "analysis saved"
            ),
            "analysis_id": analysis_id,
            "document_id": str(document_id),
            "patient_id": str(patient_id),
            "file_name": document["file_name"],
            "document_type": document_type,
            "document_summary": ai_result["analysis"],
            "ai_model": ai_result["model"],
            "disclaimer": ai_result["disclaimer"],
        }

    except HTTPException:
        raise

    except ValueError:
        logger.exception(
            "Medical document analysis validation failed | "
            "Document: %s | Owner: %s",
            document_id,
            user.id,
        )

        raise HTTPException(
            status_code=400,
            detail="Unable to analyze document content",
        )

    except RuntimeError:
        logger.exception(
            "AI analysis or persistence failed | "
            "Document: %s | Owner: %s",
            document_id,
            user.id,
        )

        raise HTTPException(
            status_code=502,
            detail="AI analysis or saving the analysis failed",
        )

    except Exception:
        logger.exception(
            "Medical document analysis failed | "
            "Document: %s | Owner: %s",
            document_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to analyze patient document",
        )


# STEP 32: Retrieve saved AI analyses
@router.get(
    "/{patient_id}/documents/{document_id}/analyses"
)
def get_document_analyses(
    patient_id: UUID,
    document_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        document_response = (
            client.table("healthsphere_documents")
            .select("id")
            .eq("id", str(document_id))
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not document_response.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        response = (
            client.table("healthsphere_ai_analyses")
            .select(
                "id, patient_id, document_id, "
                "analysis_text, model_name, created_at"
            )
            .eq("patient_id", str(patient_id))
            .eq("document_id", str(document_id))
            .eq("owner_id", str(user.id))
            .order("created_at", desc=True)
            .execute()
        )

        analyses = response.data or []

        return {
            "patient_id": str(patient_id),
            "document_id": str(document_id),
            "total_analyses": len(analyses),
            "analyses": analyses,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Saved AI analysis retrieval failed | "
            "Document: %s | Patient: %s | Owner: %s",
            document_id,
            patient_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve saved AI analyses",
        )
