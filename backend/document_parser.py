from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_BYTES = 10 * 1024 * 1024


def validate_filename(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, DOCX, and TXT files are supported")
    return extension


def extract_text(data: bytes, filename: str) -> str:
    extension = validate_filename(filename)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("CV exceeds the 10 MB limit")
    if extension == ".txt":
        text = data.decode("utf-8", errors="replace")
    elif extension == ".pdf":
        reader = PdfReader(BytesIO(data))
        text = "\n\n".join(
            f"[Page {index}]\n{page.extract_text() or ''}"
            for index, page in enumerate(reader.pages, start=1)
        )
    else:
        document = Document(BytesIO(data))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(normalized) < 30:
        raise ValueError("Could not extract enough text from this CV")
    return normalized

