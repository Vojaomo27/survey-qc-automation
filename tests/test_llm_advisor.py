"""Tests for safe data-management advisor recommendations."""

from __future__ import annotations

import pandas as pd
from unittest.mock import patch
from urllib.error import HTTPError

from core.agent import QCAgent
from core.llm_advisor import DataManagementAdvisor
from core.llm_context import build_chat_evidence, build_study_context
from core.models import ColumnMapping


def test_local_advisor_recommends_actions_from_data_risks() -> None:
    """Local advice reflects missingness and outlier signals without an API."""
    dataframe = pd.DataFrame({"score": [10, 11, 12, 13, 14, 15, 1000], "blank": [None] * 7})
    analysis = QCAgent().analyze(dataframe, ColumnMapping())

    recommendations = DataManagementAdvisor().recommend(analysis, {"llm_provider": "none"})
    titles = {recommendation.title for recommendation in recommendations}

    assert "Review missingness before cleaning" in titles
    assert "Separate valid extremes from errors" in titles
    assert all(recommendation.source == "local" for recommendation in recommendations)


def test_llm_context_contains_question_profiles_and_row_sessions() -> None:
    """The LLM receives question structure and bounded instance narratives."""
    dataframe = pd.DataFrame({"instance_id": ["a", "b"], "age": [20, 30], "consent": ["yes", "no"]})
    analysis = QCAgent().analyze(dataframe, ColumnMapping())
    context = build_study_context(dataframe, analysis, "Household survey")

    assert context["questionnaire_text"] == "Household survey"
    assert len(context["questions"]) == 3
    assert context["row_sessions"][0]["instance_id"] == "a"
    assert context["row_sessions"][0]["responses"]["age"] == 20


def test_llm_review_surfaces_connection_failure() -> None:
    """A failed API call is visible to the user rather than hidden."""
    dataframe = pd.DataFrame({"instance_id": ["a"]})
    analysis = QCAgent().analyze(dataframe, ColumnMapping())
    settings = {
        "llm_provider": "google_ai_studio",
        "llm_endpoint": "https://example.invalid/v1",
        "llm_model": "gemini-2.5-flash",
    }
    with patch.object(DataManagementAdvisor, "_api_key", return_value="test-key"):
        with patch("core.llm_advisor.urlopen", side_effect=OSError("network unavailable")):
            review = DataManagementAdvisor().review(analysis, settings)

    assert not review.connected
    assert not review.succeeded
    assert "network unavailable" in review.status


def test_google_provider_uses_google_defaults() -> None:
    """Google selection does not silently route requests to a stale provider."""
    advisor = DataManagementAdvisor()
    endpoint, model = advisor._provider_defaults({"llm_provider": "google_ai_studio"})

    assert endpoint == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert model == "gemini-2.5-flash"


def test_http_error_body_is_preserved() -> None:
    """Provider error details remain visible for diagnosis."""
    error = HTTPError("https://example.test", 400, "bad request", {}, None)
    error.read = lambda: b'{"error":{"message":"invalid model"}}'  # type: ignore[method-assign]

    assert "invalid model" in DataManagementAdvisor._error_body(error)


def test_chat_requires_configured_llm() -> None:
    """Chat reports missing provider configuration without making a request."""
    dataframe = pd.DataFrame({"instance_id": ["a"], "age": [20]})
    analysis = QCAgent().analyze(dataframe, ColumnMapping())

    review = DataManagementAdvisor().chat(analysis, {"llm_provider": "none"}, "Explain age")

    assert not review.succeeded
    assert "disabled" in review.status


def test_chat_evidence_retrieves_full_data_signals() -> None:
    """Chat evidence searches loaded rows beyond the initial LLM sample."""
    dataframe = pd.DataFrame({
        "instance_id": ["a", "b", "b"],
        "age": [20, None, 200],
    })

    evidence = build_chat_evidence(dataframe, "show missing values and duplicate instance b")

    assert "missingness" in evidence
    assert "duplicate_rows" in evidence
    assert evidence["matched_by"] == "instance_id"