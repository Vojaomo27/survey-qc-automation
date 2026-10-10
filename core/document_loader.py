"""Load project questionnaires and quota documents for LLM context."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(path: str | Path, max_characters: int = 100_000) -> str:
    """Extract readable text from a PDF without sending it anywhere."""
    reader = PdfReader(str(path))
    pages: list[str] = []
    remaining = max_characters
    for page in reader.pages:
        if remaining <= 0:
            break
        text = page.extract_text() or ""
        pages.append(text[:remaining])
        remaining -= len(text)
    return "\n\n".join(pages).strip()