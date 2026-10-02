import io
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10
MAX_CV_CHARS = 30_000
MIN_CV_CHARS = 50


class CvExtractionError(ValueError):
    pass


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def validate_cv_text(text: str) -> str:
    text = clean_text(text)
    if len(text) < MIN_CV_CHARS:
        raise CvExtractionError(
            "Couldn't find enough text in that CV. If it's a scanned PDF, paste the text instead."
        )
    if len(text) > MAX_CV_CHARS:
        raise CvExtractionError(f"CV is too long (max {MAX_CV_CHARS:,} characters).")
    return text


def extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise CvExtractionError("That PDF is password-protected.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise CvExtractionError(f"CV PDFs can have at most {MAX_PDF_PAGES} pages.")
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except PdfReadError as exc:
        raise CvExtractionError("That file isn't a readable PDF.") from exc
    return validate_cv_text(text)
