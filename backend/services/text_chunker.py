
import re


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[dict]:
    """
    Split extracted document text into overlapping chunks.

    Prefer paragraph, line, and sentence boundaries.
    Align overlapping chunks to word boundaries.

    Original medical text is preserved without rewriting.
    """

    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be positive"
        )

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    text = text.strip()

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):

        hard_end = min(
            start + chunk_size,
            len(text),
        )

        end = hard_end

        if hard_end < len(text):

            paragraph_boundary = text.rfind(
                "\n\n",
                start,
                hard_end,
            )

            line_boundary = text.rfind(
                "\n",
                start,
                hard_end,
            )

            sentence_matches = list(
                re.finditer(
                    r"[.!?](?:\s+|$)",
                    text[start:hard_end],
                )
            )

            sentence_boundary = (
                start + sentence_matches[-1].end()
                if sentence_matches
                else -1
            )

            word_boundary = text.rfind(
                " ",
                start,
                hard_end,
            )

            minimum_boundary = start + int(
                chunk_size * 0.5
            )

            candidates = [
                paragraph_boundary + 2
                if paragraph_boundary >= 0
                else -1,

                line_boundary + 1
                if line_boundary >= 0
                else -1,

                sentence_boundary,

                word_boundary
                if word_boundary >= 0
                else -1,
            ]

            valid_candidates = [
                boundary
                for boundary in candidates
                if boundary >= minimum_boundary
            ]

            if valid_candidates:
                end = max(valid_candidates)

        content = text[start:end].strip()

        if content:
            chunks.append({
                "chunk_index": chunk_index,
                "content": content,
            })

            chunk_index += 1

        if end >= len(text):
            break

        next_start = max(
            0,
            end - overlap,
        )

        # Align overlap to the beginning of a word.
        if (
            next_start > 0
            and next_start < len(text)
            and not text[next_start].isspace()
        ):
            while (
                next_start > 0
                and not text[next_start - 1].isspace()
            ):
                next_start -= 1

        # Skip whitespace at the beginning of the next chunk.
        while (
            next_start < len(text)
            and text[next_start].isspace()
        ):
            next_start += 1

        # Prevent an infinite loop.
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks
