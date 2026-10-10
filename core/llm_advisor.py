"""Data-management experience advice with optional Gemini/Groq LLM support."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.agent import AgentAnalysis
from core.ai_service import AIRequest, AIService, AIServiceError, GeminiProvider, GroqProvider
from core.llm_context import build_chat_evidence, build_study_context
from utils.constants import LLM_API_KEY_FILE


@dataclass(frozen=True)
class UXRecommendation:
    """Actionable improvement for the data-management workflow."""

    title: str
    rationale: str
    action: str
    priority: str = "medium"
    source: str = "local"


@dataclass(frozen=True)
class LLMReview:
    """Transparent result of one LLM request."""

    connected: bool
    succeeded: bool
    status: str
    response_text: str = ""
    recommendations: tuple[UXRecommendation, ...] = ()


class DataManagementAdvisor:
    """Generate transparent workflow advice and optionally ask an LLM to refine it."""

    def local_recommendations(self, analysis: AgentAnalysis) -> list[UXRecommendation]:
        understanding = analysis.understanding
        recommendations: list[UXRecommendation] = []
        metrics = {metric.name: metric.value for metric in understanding.metrics}
        if metrics.get("Missing cells", "0%").rstrip("%").replace(".", "", 1).isdigit():
            missing = float(metrics["Missing cells"].rstrip("%"))
            if missing >= 10:
                recommendations.append(UXRecommendation(
                    "Review missingness before cleaning",
                    f"{metrics['Missing cells']} of cells are missing.",
                    "Show missingness by question and define whether blanks mean skip, refusal, or data loss.",
                    "high",
                ))
        if int(metrics.get("Duplicate records", "0").replace(",", "")) > 0:
            recommendations.append(UXRecommendation(
                "Require duplicate resolution",
                "Duplicate records can inflate counts and rates.",
                "Add a review step that selects the retained record and records the resolution reason.",
                "high",
            ))
        if int(metrics.get("Potential outlier values", "0").replace(",", "")) > 0:
            recommendations.append(UXRecommendation(
                "Separate valid extremes from errors",
                "Potential outliers may be real observations or entry mistakes.",
                "Present each outlier with its question, value, valid range, and an accept or investigate action.",
                "high",
            ))
        if understanding.links:
            recommendations.append(UXRecommendation(
                "Make linked entities explicit",
                f"{len(understanding.links)} possible links were detected.",
                "Show the key columns and overlap percentage before joining or comparing sheets.",
                "medium",
            ))
        recommendations.append(UXRecommendation(
            "Use an approval checkpoint",
            "Automatic mappings and interpretations can be wrong for project-specific questionnaires.",
            "Require a user to approve mappings, relationships, and proposed cleaning actions before changes are applied.",
            "high",
        ))
        return recommendations

    def llm_recommendations(
        self,
        analysis: AgentAnalysis,
        endpoint: str,
        model: str,
        api_key: str,
        questionnaire_text: str = "",
    ) -> LLMReview:
        """Ask an OpenAI-compatible endpoint and preserve the actual response."""
        summary = build_study_context(analysis.dataframe, analysis, questionnaire_text)
        prompt = (
            "You are a senior survey data-management UX advisor. Based only on this "
            "structured dataset summary, propose practical improvements to the app's "
            "workflow for understanding, cleaning, reviewing, and approving data. "
            "Return JSON: {\"recommendations\":[{\"title\":...,\"rationale\":...,"
            "\"action\":...,\"priority\":\"high|medium|low\"}]}.\n\n"
            + json.dumps(summary, default=list)
        )
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }).encode("utf-8")
        request = Request(
            endpoint.rstrip("/") + "/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:  # noqa: S310 - configured endpoint
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            response_text = str(content)
            parsed_text = response_text.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                parsed = json.loads(parsed_text)
            except json.JSONDecodeError:
                return LLMReview(
                    True,
                    True,
                    "Connected and received a plain-text response; no structured recommendations were extracted.",
                    response_text,
                )
            recommendations = tuple(
                UXRecommendation(
                    item["title"], item["rationale"], item["action"], item.get("priority", "medium"), "llm"
                )
                for item in parsed.get("recommendations", [])
                if all(key in item for key in ("title", "rationale", "action"))
            )
            return LLMReview(True, True, "Connected and received a response.", response_text, recommendations)
        except HTTPError as exc:
            detail = self._error_body(exc)
            return LLMReview(False, False, f"LLM request failed with HTTP {exc.code}: {detail}")
        except URLError as exc:
            return LLMReview(False, False, f"LLM network error: {exc.reason}")
        except Exception as exc:  # noqa: BLE001 - returned to the UI for diagnosis
            return LLMReview(False, False, f"LLM request failed: {exc}")

    def test_connection(self, settings: dict[str, Any]) -> LLMReview:
        """Perform a minimal request to verify endpoint, model, and API key."""
        api_key = self._api_key(settings)
        if not api_key:
            return LLMReview(False, False, "No API key found. Paste one in Settings.")
        provider = str(settings.get("llm_provider", "none")).lower()
        if provider == "none":
            return LLMReview(False, False, "LLM provider is disabled. Set it in Settings.")
        endpoint, model = self._provider_defaults(settings)
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: SurveyQC connection OK"}],
            "temperature": 0,
        }).encode("utf-8")
        request = Request(
            endpoint.rstrip("/") + "/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - configured endpoint
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return LLMReview(True, True, "Connection verified.", str(content))
        except HTTPError as exc:
            return LLMReview(False, False, f"Connection failed with HTTP {exc.code}: {self._error_body(exc)}")
        except URLError as exc:
            return LLMReview(False, False, f"Connection network error: {exc.reason}")
        except Exception as exc:  # noqa: BLE001 - returned to the UI
            return LLMReview(False, False, f"Connection failed: {exc}")

    def review(
        self,
        analysis: AgentAnalysis,
        settings: dict[str, Any],
        questionnaire_text: str = "",
    ) -> LLMReview:
        """Run the full LLM review and return status plus usable recommendations."""
        api_key = self._api_key(settings)
        provider = str(settings.get("llm_provider", "none")).lower()
        if provider == "none":
            return LLMReview(False, False, "LLM provider is disabled in Settings.")
        if not api_key:
            return LLMReview(False, False, "No API key found. Paste one in Settings.")
        endpoint, model = self._provider_defaults(settings)
        return self.llm_recommendations(
            analysis,
            endpoint,
            model,
            api_key,
            questionnaire_text,
        )

    def chat(
        self,
        analysis: AgentAnalysis,
        settings: dict[str, Any],
        user_message: str,
        questionnaire_text: str = "",
        history: list[tuple[str, str]] | None = None,
    ) -> LLMReview:
        """Answer one QC staff question using the current study/data context."""
        api_key = self._api_key(settings)
        provider = str(settings.get("llm_provider", "none")).lower()
        if provider == "none":
            return LLMReview(False, False, "LLM provider is disabled in Settings.")
        if not api_key:
            return LLMReview(False, False, "No API key found. Paste one in Settings.")

        endpoint, model = self._provider_defaults(settings)
        context = build_study_context(analysis.dataframe, analysis, questionnaire_text)
        evidence = build_chat_evidence(analysis.dataframe, user_message)
        messages: list[dict[str, str]] = [{
            "role": "system",
            "content": (
                "You are the SurveyQC data-management analyst. Use the supplied questionnaire, "
                "schema, metrics, mappings, and bounded row sessions to answer the QC person's "
                "question. Explain evidence and uncertainty. Recommend actions, but never claim "
                "that you changed or cleaned data. Keep answers practical and concise.\n\n"
                + json.dumps(context, default=str)
                + "\n\nQuestion-specific evidence retrieved locally:\n"
                + json.dumps(evidence, default=str)
            ),
        }]
        for role, content in (history or [])[-8:]:
            messages.append({"role": role, "content": content[:4_000]})
        messages.append({"role": "user", "content": user_message[:8_000]})
        payload = json.dumps({"model": model, "messages": messages, "temperature": 0.2}).encode("utf-8")
        request = Request(
            endpoint.rstrip("/") + "/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:  # noqa: S310 - configured endpoint
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            return LLMReview(True, True, "LLM response received.", str(content))
        except HTTPError as exc:
            return LLMReview(False, False, f"Chat failed with HTTP {exc.code}: {self._error_body(exc)}")
        except URLError as exc:
            return LLMReview(False, False, f"Chat network error: {exc.reason}")
        except Exception as exc:  # noqa: BLE001 - returned to the chat UI
            return LLMReview(False, False, f"Chat failed: {exc}")

    def _api_key(self, settings: dict[str, Any]) -> str:
        try:
            return LLM_API_KEY_FILE.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return os.getenv(str(settings.get("llm_api_key_env", "GEMINI_API_KEY")), "")

    def _provider_defaults(self, settings: dict[str, Any]) -> tuple[str, str]:
        """Resolve provider defaults while keeping the current app config pattern intact."""
        provider = str(settings.get("llm_provider", "google_ai_studio")).lower()
        if provider in {"google", "google_ai_studio", "gemini"}:
            configured_endpoint = str(settings.get("llm_endpoint") or "")
            configured_model = str(settings.get("llm_model") or "")
            return (
                configured_endpoint if "generativelanguage.googleapis.com" in configured_endpoint
                else "https://generativelanguage.googleapis.com/v1beta/openai",
                configured_model if configured_model.startswith("gemini-") else "gemini-2.5-flash",
            )
        if provider == "groq":
            return (
                str(settings.get("llm_endpoint") or "https://api.groq.com/openai/v1"),
                str(settings.get("llm_model") or "openai/gpt-oss-120b"),
            )
        return (
            str(settings.get("llm_endpoint") or "https://api.deepseek.com/v1"),
            str(settings.get("llm_model") or "deepseek-chat"),
        )

    def _active_provider_name(self, endpoint: str, model: str) -> str:
        if "groq.com" in endpoint.lower():
            return "groq"
        return "gemini"

    def _provider_for_settings(self, settings: dict[str, Any]) -> Any:
        provider = str(settings.get("llm_provider", "google_ai_studio")).lower()
        api_key = self._api_key(settings)
        endpoint = str(settings.get("llm_endpoint") or "")
        model = str(settings.get("llm_model") or "")
        if provider in {"google", "google_ai_studio", "gemini"}:
            return GeminiProvider(model or "gemini-2.5-flash")
        if provider == "groq":
            return GroqProvider(model or "openai/gpt-oss-120b")
        return GeminiProvider(model or "gemini-2.5-flash")

    @staticmethod
    def _error_body(error: HTTPError) -> str:
        """Extract the provider's JSON/text error without exposing the API key."""
        try:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
                return json.dumps(parsed, ensure_ascii=False)[:2_000]
            except json.JSONDecodeError:
                return raw[:2_000]
        except Exception:
            return str(error.reason or error)

    def recommend(
        self,
        analysis: AgentAnalysis,
        settings: dict[str, Any],
        questionnaire_text: str = "",
        use_llm: bool = True,
    ) -> list[UXRecommendation]:
        """Return local advice and optional LLM advice, with safe fallback."""
        recommendations = self.local_recommendations(analysis)
        provider = str(settings.get("llm_provider", "none")).lower()
        api_key = self._api_key(settings)
        if use_llm and provider != "none" and api_key:
            endpoint, model = self._provider_defaults(settings)
            review = self.llm_recommendations(
                analysis,
                endpoint,
                model,
                api_key,
                questionnaire_text,
            )
            recommendations.extend(review.recommendations)
        return recommendations