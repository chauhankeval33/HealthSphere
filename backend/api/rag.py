
import logging
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user

from backend.services.rag_service import (
    index_patient_document,
)

from backend.services.embedding_service import (
    embed_search_query,
)

from backend.services.chat_service import (
    answer_patient_question,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/patients",
    tags=["RAG - Document Search"],
)

MAX_HISTORY_MESSAGES = 10


# ============================================================
# GEMINI ERROR HANDLING
# ============================================================

def _get_gemini_http_error(exc: Exception):
    """
    Convert temporary Gemini API errors into meaningful
    HTTP responses.

    Uses the status_code exposed by google.genai API errors.
    """

    status_code = getattr(
        exc,
        "status_code",
        None,
    )

    if status_code == 429:
        return HTTPException(
            status_code=429,
            detail=(
                "The AI service is receiving too many requests. "
                "Please wait briefly and try again."
            ),
        )

    if status_code in (500, 503, 504):
        return HTTPException(
            status_code=503,
            detail=(
                "The AI service is temporarily unavailable. "
                "Your documents are still indexed. "
                "Please try again shortly."
            ),
        )

    return None


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class DocumentSearchRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=1000,
    )

    match_count: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    conversation_id: UUID = Field(
        default_factory=uuid4,
    )


class ChatHistoryRequest(BaseModel):
    conversation_id: UUID

    role: Literal["user", "assistant"]

    content: str = Field(
        min_length=1,
        max_length=10000,
    )

    sources: list[dict] = Field(
        default_factory=list,
    )


# ============================================================
# STEP 38A: INDEX PATIENT DOCUMENT
# ============================================================

@router.post(
    "/{patient_id}/documents/{document_id}/index"
)
def index_document(
    patient_id: UUID,
    document_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        return index_patient_document(
            client=client,
            user_id=str(user.id),
            patient_id=str(patient_id),
            document_id=str(document_id),
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError:
        logger.exception("Document indexing failed.")

        raise HTTPException(
            status_code=502,
            detail="Unable to index document.",
        )


# ============================================================
# STEP 38B: CHECK DOCUMENT INDEXING STATUS
# ============================================================

@router.get(
    "/{patient_id}/documents/{document_id}/index-status"
)
def get_index_status(
    patient_id: UUID,
    document_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    try:
        document_response = (
            client.table("healthsphere_documents")
            .select("id, file_name")
            .eq("id", str(document_id))
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        if not document_response.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        response = (
            client.table("healthsphere_document_chunks")
            .select("id", count="exact")
            .eq("document_id", str(document_id))
            .eq("patient_id", str(patient_id))
            .eq("owner_id", str(user.id))
            .execute()
        )

        total_chunks = response.count or 0

        return {
            "document_id": str(document_id),
            "file_name": document_response.data[0]["file_name"],
            "indexed": total_chunks > 0,
            "total_chunks": total_chunks,
            "status": (
                "indexed"
                if total_chunks > 0
                else "not_indexed"
            ),
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unable to retrieve indexing status."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve indexing status.",
        )


# ============================================================
# STEP 38C: SEARCH PATIENT DOCUMENT CHUNKS
# ============================================================

@router.post(
    "/{patient_id}/documents/search"
)
def search_patient_documents(
    patient_id: UUID,
    data: DocumentSearchRequest,
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
                detail="Patient not found.",
            )

        query_embedding = embed_search_query(
            data.question
        )

        response = client.rpc(
            "match_healthsphere_chunks",
            {
                "query_embedding": query_embedding,
                "match_patient_id": str(patient_id),
                "match_count": data.match_count,
            },
        ).execute()

        results = response.data or []

        return {
            "patient_id": str(patient_id),
            "question": data.question,
            "total_results": len(results),
            "results": results,
        }

    except HTTPException:
        raise

    except RuntimeError:
        logger.exception("Search embedding failed.")

        raise HTTPException(
            status_code=502,
            detail="Unable to generate search embedding.",
        )

    except Exception:
        logger.exception(
            "Patient document search failed."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to search patient documents.",
        )


# ============================================================
# STEP 39 + 42: CONVERSATION-AWARE RAG CHATBOT
# ============================================================

@router.post(
    "/{patient_id}/chat"
)
def chat_with_patient_documents(
    patient_id: UUID,
    data: DocumentSearchRequest,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    user_id = str(user.id)
    patient_id_str = str(patient_id)
    conversation_id = str(data.conversation_id)

    try:
        # 1. Verify patient ownership.
        patient_response = (
            client.table("healthsphere_patients")
            .select("id")
            .eq("id", patient_id_str)
            .eq("owner_id", user_id)
            .limit(1)
            .execute()
        )

        if not patient_response.data:
            raise HTTPException(
                status_code=404,
                detail="Patient not found.",
            )

        # 2. Retrieve conversation history.
        history_response = (
            client.table("healthsphere_chat_messages")
            .select("role, content")
            .eq("owner_id", user_id)
            .eq("patient_id", patient_id_str)
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(MAX_HISTORY_MESSAGES)
            .execute()
        )

        conversation_history = list(
            reversed(history_response.data or [])
        )

        # 3. Generate the RAG answer.
        try:
            result = answer_patient_question(
                client=client,
                user_id=user_id,
                patient_id=patient_id_str,
                question=data.question,
                match_count=data.match_count,
                conversation_history=conversation_history,
            )

        except Exception as exc:
            logger.exception(
                "Gemini or RAG answer generation failed."
            )

            gemini_http_error = _get_gemini_http_error(
                exc
            )

            if gemini_http_error is not None:
                raise gemini_http_error from exc

            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to generate the answer. "
                    "Please try again."
                ),
            ) from exc

        # 4. Validate generated response.
        if (
            not isinstance(result, dict)
            or not result.get("answer")
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "The AI service returned an empty answer. "
                    "Please try again."
                ),
            )

        # 5. Save conversation messages.
        try:
            saved_messages = (
                client.table("healthsphere_chat_messages")
                .insert([
                    {
                        "owner_id": user_id,
                        "patient_id": patient_id_str,
                        "conversation_id": conversation_id,
                        "role": "user",
                        "content": data.question,
                        "sources": [],
                    },
                    {
                        "owner_id": user_id,
                        "patient_id": patient_id_str,
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result.get("sources", []),
                    },
                ])
                .execute()
            )

        except Exception as exc:
            logger.exception(
                "Unable to save generated chatbot response."
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "The answer was generated, but saving "
                    "the conversation failed. Please try again."
                ),
            ) from exc

        # 6. Return response.
        return {
            "patient_id": patient_id_str,
            "conversation_id": conversation_id,
            "question": data.question,
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "history_messages_used": len(
                conversation_history
            ),
            "saved": bool(saved_messages.data),
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Patient document chatbot failed."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process the patient chatbot request.",
        )


# ============================================================
# STEP 41: SAVE INDIVIDUAL CHAT MESSAGE
# ============================================================

@router.post(
    "/{patient_id}/chat-history"
)
def save_chat_message(
    patient_id: UUID,
    data: ChatHistoryRequest,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    user_id = str(user.id)

    try:
        patient_response = (
            client.table("healthsphere_patients")
            .select("id")
            .eq("id", str(patient_id))
            .eq("owner_id", user_id)
            .limit(1)
            .execute()
        )

        if not patient_response.data:
            raise HTTPException(
                status_code=404,
                detail="Patient not found.",
            )

        response = (
            client.table("healthsphere_chat_messages")
            .insert({
                "owner_id": user_id,
                "patient_id": str(patient_id),
                "conversation_id": str(data.conversation_id),
                "role": data.role,
                "content": data.content,
                "sources": data.sources,
            })
            .execute()
        )

        return {
            "message": "Chat message saved successfully.",
            "data": response.data,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unable to save chat message."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to save chat message.",
        )


# ============================================================
# STEP 41: LOAD CHAT HISTORY
# ============================================================

@router.get(
    "/{patient_id}/chat-history"
)
def get_chat_history(
    patient_id: UUID,
    conversation_id: UUID,
    context=Depends(get_current_user),
):
    user = context["user"]
    client = context["client"]

    user_id = str(user.id)

    try:
        patient_response = (
            client.table("healthsphere_patients")
            .select("id")
            .eq("id", str(patient_id))
            .eq("owner_id", user_id)
            .limit(1)
            .execute()
        )

        if not patient_response.data:
            raise HTTPException(
                status_code=404,
                detail="Patient not found.",
            )

        response = (
            client.table("healthsphere_chat_messages")
            .select("*")
            .eq("owner_id", user_id)
            .eq("patient_id", str(patient_id))
            .eq("conversation_id", str(conversation_id))
            .order("created_at")
            .execute()
        )

        return {
            "patient_id": str(patient_id),
            "conversation_id": str(conversation_id),
            "messages": response.data or [],
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unable to load chat history."
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to load chat history.",
        )
