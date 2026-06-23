"""
file_parser.py — Document text extraction

Extracts raw text from uploaded PDF, DOCX, or TXT files server-side.
"""

from io import BytesIO

import pdfplumber
from docx import Document


def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """Extract raw text content from an uploaded document file.

    Supports:
      - .pdf — pdfplumber for robust extraction including tables
      - .docx — python-docx for paragraph text
      - .txt (fallback) — UTF-8 decode
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    text = ""

    if ext == "pdf":
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n\n".join(pages)

    elif ext in ("docx", "doc"):
        doc = Document(BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)

    else:
        text = file_bytes.decode("utf-8", errors="replace")

    if not text.strip():
        raise ValueError(
            f"No text could be extracted from '{filename}'. "
            "The file may be empty, scanned (image-only), or unsupported."
        )
    return text.strip()
