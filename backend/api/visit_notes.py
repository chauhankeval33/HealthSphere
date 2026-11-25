
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_current_user
from backend.schemas.visit_notes import (
    VisitNoteCreate,
    VisitNoteUpdate,
)

router = APIRouter(
    prefix="/api/patients/{patient_id}/notes",
    tags=["Visit Notes"],
)


def verify_patient_ownership(client, patient_id, user_id):
    response = (
        client.table("healthsphere_patients")
        .select("id")
        .eq("id", str(patient_id))
        .eq("owner_id", str(user_id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )


@router.post("/")
def create_visit_note(
    patient_id: UUID,
    note: VisitNoteCreate,
    context=Depends(get_current_user),
):
    client = context["client"]
    user = context["user"]

    verify_patient_ownership(client, patient_id, user.id)

    note_data = note.model_dump()
    note_data["patient_id"] = str(patient_id)
    note_data["owner_id"] = str(user.id)

    response = (
        client.table("healthsphere_visit_notes")
        .insert(note_data)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Failed to create visit note",
        )

    return {
        "message": "Visit note created successfully",
        "note": response.data[0],
    }


@router.get("/")
def get_visit_notes(
    patient_id: UUID,
    context=Depends(get_current_user),
):
    client = context["client"]
    user = context["user"]

    verify_patient_ownership(client, patient_id, user.id)

    response = (
        client.table("healthsphere_visit_notes")
        .select("*")
        .eq("patient_id", str(patient_id))
        .eq("owner_id", str(user.id))
        .order("visit_date", desc=True)
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "count": len(response.data),
        "notes": response.data,
    }


@router.patch("/{note_id}")
def update_visit_note(
    patient_id: UUID,
    note_id: UUID,
    note: VisitNoteUpdate,
    context=Depends(get_current_user),
):
    client = context["client"]
    user = context["user"]

    verify_patient_ownership(client, patient_id, user.id)

    update_data = note.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    response = (
        client.table("healthsphere_visit_notes")
        .update(update_data)
        .eq("id", str(note_id))
        .eq("patient_id", str(patient_id))
        .eq("owner_id", str(user.id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Visit note not found",
        )

    return {
        "message": "Visit note updated successfully",
        "note": response.data[0],
    }


@router.delete("/{note_id}")
def delete_visit_note(
    patient_id: UUID,
    note_id: UUID,
    context=Depends(get_current_user),
):
    client = context["client"]
    user = context["user"]

    verify_patient_ownership(client, patient_id, user.id)

    response = (
        client.table("healthsphere_visit_notes")
        .delete()
        .eq("id", str(note_id))
        .eq("patient_id", str(patient_id))
        .eq("owner_id", str(user.id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Visit note not found",
        )

    return {
        "message": "Visit note deleted successfully",
    }
