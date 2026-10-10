"""Provider-agnostic AI service layer for Gemini and Groq.

This follows the app's existing pattern: the UI stores a single API key locally,
then the selected provider uses that same key. The rest of the app stays
provider-independent.
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TEMPORARY_ERROR_CODES = {429, 500, 502, 503, 504}


class AIServiceError(RuntimeError):
    """Raised when provider configuration or API access fails."""

    def __init__(self, message: str, *, temporary: bool = False, provider: str | None = None) -> None:
        super().__init__(message)
        self.temporary = temporary
        self.provider = provider


@dataclass
class AIRequest:
    """Common request object used by all AI providers."""

    questionnaire: str = ""
    data_dictionary: str = ""
    quota_requirements: str = ""
    validation_results: dict[str, Any] = field(default_factory=dict)
    suspicious_records: list[dict[str, Any]] = field(default_factory=list)
    interviewer_stats: dict[str, Any] = field(default_factory=dict)
    relevant_metadata: dict[str, Any] = field(default_factory=dict)
    prompt: str = ""
    dataset_summary: dict[str, Any] = field(default_factory=dict)
    max_records: int = 50

    @property
    def compact_summary(self) -> dict[str, Any]:
        return {
            "questionnaire": self.questionnaire[:12_000],
            "data_dictionary": self.data_dictionary[:8_000],
            "quota_requirements": self.quota_requirements[:4_000],
            "validation_results": self.validation_results,
            "suspicious_records": self.suspicious_records[: self.max_records],
            "interviewer_stats": self.interviewer_stats,
            "relevant_metadata": self.relevant_metadata,
            "dataset_summary": self.dataset_summary,
            "prompt": self.prompt[:4_000],
        }


class BaseAIProvider(ABC):
    """Abstract API client for a provider."""

    name: str = "base"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or ""
        self._model = model or ""

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def base_url(self) -> str:
        raise NotImplementedError

    def _request_json(self, payload: dict[str, Any]) -> Any:
        if not self.api_key:
            raise AIServiceError(f"{self.name.upper()} API key is missing. Add it in Settings and save it.")
        request = Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise AIServiceError(
                f"{self.name.upper()} request failed with HTTP {exc.code}: {self._error_body(exc)}",
                temporary=self._temporary_error(exc),
                provider=self.name,
            ) from exc
        except URLError as exc:
            raise AIServiceError(f"{self.name.upper()} network error: {exc.reason}", temporary=True, provider=self.name) from exc
        except TimeoutError as exc:
            raise AIServiceError(f"{self.name.upper()} request timed out.", temporary=True, provider=self.name) from exc

    @staticmethod
    def _temporary_error(exc: Exception) -> bool:
        status_code = getattr(exc, "code", None)
        if status_code in TEMPORARY_ERROR_CODES:
            return True
        text = str(exc).lower()
        return any(token in text for token in ("503", "timeout", "rate limit", "temporarily unavailable", "overloaded", "capacity"))

    @staticmethod
    def _error_body(error: HTTPError) -> str:
        try:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
                return json.dumps(parsed, ensure_ascii=False)[:2_000]
            except json.JSONDecodeError:
                return raw[:2_000]
        except Exception:
            return str(error.reason or error)

    def _system_prompt(self) -> str:
        return (
            "You are a professional survey and data-quality analyst. Use only the supplied evidence. "
            "Do not invent data. Distinguish genuine issues from unusual but possible responses. "
            "Return structured JSON with a 'findings' array and a 'summary' object."
        )

    def _user_prompt(self, request: AIRequest) -> str:
        return (
            f"{request.prompt or 'Review the data quality signals and provide structured findings.'}\n\n"
            + json.dumps(request.compact_summary, ensure_ascii=False, default=str)
        )

    @staticmethod
    def _normalise_result(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {"findings": [], "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}}

        findings = payload.get("findings") if isinstance(payload.get("findings"), list) else []
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        return {
            "findings": findings,
            "summary": {
                "critical": int(summary.get("critical", 0) or 0),
                "high": int(summary.get("high", 0) or 0),
                "medium": int(summary.get("medium", 0) or 0),
                "low": int(summary.get("low", 0) or 0),
            },
        }

    @abstractmethod
    def analyze(self, request: AIRequest) -> dict[str, Any]:
        raise NotImplementedError


class GeminiProvider(BaseAIProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(api_key, model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta/openai"

    def analyze(self, request: AIRequest) -> dict[str, Any]:
        body = self._request_json({
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._user_prompt(request)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        })
        content = body["choices"][0]["message"]["content"]
        return self._normalise_result(json.loads(content))


class GroqProvider(BaseAIProvider):
    name = "groq"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(api_key, model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return "https://api.groq.com/openai/v1"

    def analyze(self, request: AIRequest) -> dict[str, Any]:
        body = self._request_json({
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._user_prompt(request)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        })
        content = body["choices"][0]["message"]["content"]
        return self._normalise_result(json.loads(content))


class AIService:
    """Route the same user request through the selected provider."""

    def __init__(
        self,
        *,
        gemini_api_key: str | None = None,
        groq_api_key: str | None = None,
        preferred_provider: str = "auto",
        max_retries: int = 3,
        gemini_model: str | None = None,
        groq_model: str | None = None,
    ) -> None:
        self.gemini = GeminiProvider(gemini_api_key or os.getenv("GEMINI_API_KEY", ""), gemini_model)
        self.groq = GroqProvider(groq_api_key or os.getenv("GROQ_API_KEY", ""), groq_model)
        self.preferred_provider = preferred_provider.lower()
        self.max_retries = max_retries

    def _provider_sequence(self) -> list[BaseAIProvider]:
        if self.preferred_provider == "gemini":
            return [self.gemini]
        if self.preferred_provider == "groq":
            return [self.groq]
        return [self.gemini, self.groq]

    def analyze(self, request: AIRequest) -> dict[str, Any]:
        last_error: AIServiceError | None = None
        for provider in self._provider_sequence():
            for attempt in range(self.max_retries + 1):
                try:
                    result = provider.analyze(request)
                    result["provider"] = provider.name
                    result["model"] = provider.model
                    return result
                except AIServiceError as exc:
                    last_error = exc
                    if not exc.temporary or attempt >= self.max_retries:
                        break
                    time.sleep(2 ** attempt)
            if self.preferred_provider != "auto":
                break

        if last_error is not None:
            raise AIServiceError(
                f"AI request failed after retries: {last_error}",
                temporary=False,
                provider=getattr(last_error, "provider", None),
            ) from last_error
        raise AIServiceError("No AI provider is available.")


def analyzeWithAI(request: AIRequest, **kwargs: Any) -> dict[str, Any]:
    """Compatibility wrapper for the rest of the app."""
    return AIService(**kwargs).analyze(request)
