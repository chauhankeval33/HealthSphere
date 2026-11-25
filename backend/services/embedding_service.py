
import logging
import math

from google import genai
from google.genai import types

from backend.config import GEMINI_API_KEY


logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"

EMBEDDING_DIMENSIONS = 768


def get_embedding(
    text: str,
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[float]:
    """
    Generate a normalized 768-dimensional Gemini embedding.
    """

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Gemini API key is not configured"
        )

    if not text or not text.strip():
        raise ValueError(
            "Text cannot be empty"
        )

    allowed_tasks = {
        "RETRIEVAL_DOCUMENT",
        "RETRIEVAL_QUERY",
    }

    if task_type not in allowed_tasks:
        raise ValueError(
            "Unsupported embedding task type"
        )

    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )

        if not response.embeddings:
            raise RuntimeError(
                "Gemini returned no embeddings"
            )

        vector = response.embeddings[0].values

        if not vector or len(vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                "Unexpected embedding dimensions"
            )

        # Normalize the vector.
        magnitude = math.sqrt(
            sum(value * value for value in vector)
        )

        if magnitude == 0:
            raise RuntimeError(
                "Gemini returned a zero embedding"
            )

        return [
            float(value / magnitude)
            for value in vector
        ]

    except Exception as exc:
        logger.exception(
            "Gemini embedding generation failed"
        )

        raise RuntimeError(
            "Unable to generate text embedding"
        ) from exc


def embed_document_chunks(
    chunks: list[dict],
) -> list[dict]:
    """
    Generate embeddings for all document chunks.
    """

    embedded_chunks = []

    for chunk in chunks:
        vector = get_embedding(
            text=chunk["content"],
            task_type="RETRIEVAL_DOCUMENT",
        )

        embedded_chunks.append({
            **chunk,
            "embedding": vector,
        })

    return embedded_chunks


def embed_search_query(
    question: str,
) -> list[float]:
    """
    Generate an embedding for a chatbot question.
    """

    return get_embedding(
        text=question,
        task_type="RETRIEVAL_QUERY",
    )
