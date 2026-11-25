
from io import BytesIO

import pytesseract
import pypdfium2 as pdfium

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader


MAX_FILE_SIZE = 10 * 1024 * 1024
PDF_RENDER_SCALE = 2.0

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def _ocr_image(image):
    """Extract text from a PIL image using Tesseract."""

    image = image.convert("RGB")

    return pytesseract.image_to_string(
        image,
        lang="eng",
        config="--psm 3",
    ).strip()


def _ocr_pdf_page(pdf_document, page_index):
    """Render one PDF page and extract its text using OCR."""

    page = None
    bitmap = None
    image = None

    try:
        page = pdf_document[page_index]

        bitmap = page.render(
            scale=PDF_RENDER_SCALE
        )

        image = bitmap.to_pil()

        return _ocr_image(image)

    finally:
        if image is not None:
            image.close()

        if bitmap is not None:
            bitmap.close()

        if page is not None:
            page.close()


def process_pdf(file_content: bytes) -> dict:
    """
    Extract text from native and scanned PDF pages.

    Native PDF text extraction is attempted first.
    Tesseract OCR is used for pages without extractable text.
    """

    if not file_content:
        raise ValueError("PDF file is empty")

    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError("PDF exceeds the 10 MB limit")

    pdf_document = None

    try:
        reader = PdfReader(BytesIO(file_content))

        if reader.is_encrypted:
            raise ValueError(
                "Encrypted PDFs are not supported"
            )

        total_pages = len(reader.pages)

        if total_pages == 0:
            raise ValueError(
                "PDF contains no pages"
            )

        pdf_document = pdfium.PdfDocument(
            file_content
        )

        extracted_pages = []
        ocr_pages = 0

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):
            page_text = (
                page.extract_text() or ""
            ).strip()

            extraction_method = "native_text"

            # OCR pages without extractable native text.
            if not page_text:

                page_text = _ocr_pdf_page(
                    pdf_document,
                    page_number - 1,
                )

                extraction_method = "tesseract_ocr"
                ocr_pages += 1

            extracted_pages.append({
                "page": page_number,
                "text": page_text,
                "extraction_method": extraction_method,
            })

        full_text = "\n\n".join(
            page["text"]
            for page in extracted_pages
            if page["text"]
        )

        if ocr_pages == 0:
            ocr_status = "not_required"
        elif full_text.strip():
            ocr_status = "completed"
        else:
            ocr_status = "no_text_found"

        return {
            "document_type": "pdf",
            "total_pages": total_pages,
            "extracted_text": full_text,
            "pages": extracted_pages,
            "has_text": bool(full_text.strip()),
            "ocr_status": ocr_status,
            "ocr_pages": ocr_pages,
        }

    except ValueError:
        raise

    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError(
            "Tesseract OCR is not installed or its "
            "executable is not available in PATH"
        ) from exc

    except pytesseract.TesseractError as exc:
        raise ValueError(
            "PDF page OCR processing failed"
        ) from exc

    except Exception as exc:
        raise ValueError(
            "Unable to read or process PDF document"
        ) from exc

    finally:
        if pdf_document is not None:
            pdf_document.close()


def process_image(
    file_content: bytes,
    mime_type: str,
) -> dict:
    """
    Validate an image and extract text using Tesseract OCR.
    """

    if not file_content:
        raise ValueError("Image file is empty")

    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError(
            "Image exceeds the 10 MB limit"
        )

    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(
            "Unsupported image format"
        )

    try:
        image = Image.open(
            BytesIO(file_content)
        )

        image.verify()

        image = Image.open(
            BytesIO(file_content)
        )

        image_format = image.format
        width, height = image.size

        extracted_text = _ocr_image(image)

        image.close()

        return {
            "document_type": "image",
            "format": image_format,
            "width": width,
            "height": height,
            "extracted_text": extracted_text,
            "has_text": bool(extracted_text),
            "ocr_status": (
                "completed"
                if extracted_text
                else "no_text_found"
            ),
        }

    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(
            "Unable to read image document"
        ) from exc

    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError(
            "Tesseract OCR is not installed or its "
            "executable is not available in PATH"
        ) from exc

    except pytesseract.TesseractError as exc:
        raise ValueError(
            "Image OCR processing failed"
        ) from exc
