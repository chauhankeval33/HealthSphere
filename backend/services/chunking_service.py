
import re


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MIN_CHUNK_SIZE = 50


def clean_extracted_text(text: str) -> str:
    """
    Clean extracted document text without removing
    important medical values, units, or symbols.
    """

    if not text or not text.strip():
        raise ValueError(
            "Document text cannot be empty"
        )

    # Normalize line endings.
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove null characters.
    text = text.replace("\x00", "")

    # Remove excessive spaces and tabs.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Limit excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """
    Split extracted document text into overlapping chunks.

    Each chunk contains:
    - chunk_index
    - content
    """

    if not text or not text.strip():
        raise ValueError(
            "Document text cannot be empty"
        )

    if chunk_size < MIN_CHUNK_SIZE:
        raise ValueError(
            f"Chunk size must be at least {MIN_CHUNK_SIZE}"
        )

    if chunk_overlap < 0:
        raise ValueError(
            "Chunk overlap cannot be negative"
        )

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap must be smaller than chunk size"
        )

    cleaned_text = clean_extracted_text(text)

    chunks = []

    start = 0
    chunk_index = 0
    text_length = len(cleaned_text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length,
        )

        # Prefer ending at a word boundary.
        if end < text_length:
            boundary = cleaned_text.rfind(
                " ",
                start,
                end,
            )

            if boundary > start:
                end = boundary

        content = cleaned_text[start:end].strip()

        if content:
            chunks.append({
                "chunk_index": chunk_index,
                "content": content,
            })

            chunk_index += 1

        if end >= text_length:
            break

        next_start = end - chunk_overlap

        # Avoid getting stuck in an infinite loop.
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks
