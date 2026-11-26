
import logging
from backend.services.document_service import BUCKET_NAME
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import get_current_user
from backend.schemas.patient import PatientCreate, PatientUpdate


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/patients",
    tags=["Patients"],
)


@router.post("/")
def create_patient(
    data: PatientCreate,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    patient_data = data.model_dump(mode="json")
    patient_data["owner_id"] = user.id

    try:
        response = (
            client.table("healthsphere_patients")
            .insert(patient_data)
            .execute()
        )

        if not response.data:
            logger.error(
                "Patient creation returned no data | Owner: %s",
                user.id,
            )

            raise HTTPException(
                status_code=500,
                detail="Unable to create patient",
            )

        logger.info(
            "Patient created successfully | Owner: %s",
            user.id,
        )

        return {
            "message": "Patient created successfully",
            "patient": response.data[0],
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient creation failed | Owner: %s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to create patient",
        )


@router.get("/")
def get_patients(
    search: str = Query(default="", max_length=120),
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        query = (
            client.table("healthsphere_patients")
            .select("*")
            .eq("owner_id", user.id)
        )

        if search.strip():
            query = query.ilike(
                "full_name",
                f"%{search.strip()}%",
            )

        response = query.order(
            "created_at",
            desc=True,
        ).execute()

        return {
            "count": len(response.data),
            "patients": response.data,
        }

    except Exception:
        logger.exception(
            "Patient retrieval failed | Owner: %s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve patients",
        )


@router.get("/{patient_id}")
def get_patient(
    patient_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        response = (
            client.table("healthsphere_patients")
            .select("*")
            .eq("id", str(patient_id))
            .eq("owner_id", user.id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient retrieval failed | Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve patient",
        )


@router.patch("/{patient_id}")
def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    update_data = data.model_dump(
        mode="json",
        exclude_unset=True,
    )

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No update fields provided",
        )

    update_data["updated_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    try:
        response = (
            client.table("healthsphere_patients")
            .update(update_data)
            .eq("id", str(patient_id))
            .eq("owner_id", user.id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        logger.info(
            "Patient updated successfully | Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        return {
            "message": "Patient updated successfully",
            "patient": response.data[0],
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient update failed | Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to update patient",
        )


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        # 1. Verify that this patient belongs to the logged-in user.
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

        # 2. Retrieve only this patient's document Storage paths.
        documents_response = (
            client.table("healthsphere_documents")
            .select("storage_path")
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        storage_paths = [
            item["storage_path"]
            for item in (documents_response.data or [])
            if item.get("storage_path")
            and item["storage_path"].startswith(
                f"{user.id}/{patient_id}/"
            )
        ]

        # 3. Delete the patient.
        # Related database records are removed by ON DELETE CASCADE.
        delete_response = (
            client.table("healthsphere_patients")
            .delete()
            .eq("id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not delete_response.data:
            raise HTTPException(
                status_code=404,
                detail="Patient not found or already deleted",
            )

        # 4. Remove this patient's files from private Storage.
        storage_cleanup_warning = False

        if storage_paths:
            try:
                client.storage.from_(BUCKET_NAME).remove(
                    storage_paths
                )
            except Exception:
                storage_cleanup_warning = True
                logger.exception(
                    "Patient deleted, but Storage cleanup failed | "
                    "Patient: %s | Owner: %s",
                    patient_id,
                    user.id,
                )

        logger.info(
            "Patient deletion completed | Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        return {
            "message": "Patient deleted successfully",
            "storage_cleanup_warning": storage_cleanup_warning,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient deletion failed | Patient: %s | Owner: %s",
            patient_id,
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to delete patient",
        )