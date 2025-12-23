"""PDF text extraction using PyPDF2 (kept minimal)."""

from pathlib import Path

from PyPDF2 import PdfReader


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()

