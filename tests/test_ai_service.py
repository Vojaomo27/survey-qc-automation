from __future__ import annotations

from core.ai_service import AIRequest, AIService, AIServiceError, BaseAIProvider


class FakeGeminiProvider(BaseAIProvider):
    name = "gemini"

    def __init__(self, *, fail_with: Exception | None = None):
        self.fail_with = fail_with
        self.calls = 0

    @property
    def api_key(self) -> str:
        return "gemini-key"

    @property
    def model(self) -> str:
        return "gemini-3.6-flash"

    @property
    def base_url(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta/openai"

    def analyze(self, request: AIRequest) -> dict:
        self.calls += 1
        if self.fail_with is not None:
            raise self.fail_with
        return {"findings": [], "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}}


class FakeGroqProvider(BaseAIProvider):
    name = "groq"

    def __init__(self):
        self.calls = 0

    @property
    def api_key(self) -> str:
        return "groq-key"

    @property
    def model(self) -> str:
        return "openai/gpt-oss-120b"

    @property
    def base_url(self) -> str:
        return "https://api.groq.com/openai/v1"

    def analyze(self, request: AIRequest) -> dict:
        self.calls += 1
        return {
            "findings": [{
                "record_id": "123",
                "issue_type": "logical_inconsistency",
                "severity": "high",
                "confidence": 0.94,
                "variables": ["Q12", "Q13"],
                "evidence": "Q12 and Q13 are inconsistent.",
                "explanation": "Respondent reported both values.",
                "recommendation": "manual_review",
            }],
            "summary": {"critical": 0, "high": 1, "medium": 0, "low": 0},
        }


def test_auto_provider_falls_back_to_groq_after_gemini_503():
    gemini = FakeGeminiProvider(fail_with=RuntimeError("503 temporary unavailable"))
    groq = FakeGroqProvider()
    service = AIService(primary=gemini, fallback=groq, preferred_provider="auto", max_retries=2)

    result = service.analyze(AIRequest(questionnaire="survey", prompt="check this data"))

    assert result["provider"] == "groq"
    assert gemini.calls == 2
    assert groq.calls == 1


def test_provider_schema_is_consistent():
    provider = FakeGroqProvider()
    result = provider.analyze(AIRequest(questionnaire="survey", prompt="check this data"))

    assert "findings" in result
    assert "summary" in result
    assert result["findings"][0]["issue_type"] == "logical_inconsistency"


def test_missing_api_key_raises_clear_configuration_error():
    provider = FakeGeminiProvider()
    provider.api_key = ""  # type: ignore[attr-defined]
    service = AIService(primary=provider, fallback=FakeGroqProvider(), preferred_provider="gemini", max_retries=1)

    try:
        service.analyze(AIRequest(questionnaire="survey", prompt="check this data"))
    except AIServiceError as exc:
        assert "API key" in str(exc)
    else:
        raise AssertionError("Expected AIServiceError for missing API key")
