"""Tests for local questionnaire document extraction."""

from __future__ import annotations

from core import document_loader


class _Page:
    def __init__(self, text: str) -> None:
        self.text = text

    def extract_text(self) -> str:
        return self.text


class _Reader:
    pages = [_Page("Study purpose and quota"), _Page("Question: age")]


def test_extract_pdf_text_combines_pages(monkeypatch, tmp_path) -> None:
    """Questionnaire text is combined locally in page order."""
    monkeypatch.setattr(document_loader, "PdfReader", lambda _path: _Reader())

    text = document_loader.extract_pdf_text(tmp_path / "questionnaire.pdf")

    assert "Study purpose and quota" in text
    assert "Question: age" in text