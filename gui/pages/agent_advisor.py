"""Agent Advisor page for data-management workflow improvements."""

from __future__ import annotations

import threading

import customtkinter as ctk

from core.llm_advisor import DataManagementAdvisor, LLMReview
from gui import theme
from gui.pages.base_page import BasePage
from gui.widgets import hint_label


class AgentAdvisorPage(BasePage):
    """Show actionable recommendations for understanding and cleaning data."""

    title = "Agent Advisor"

    def build(self) -> None:
        hint_label(
            self.body,
            "Review workflow improvements suggested from the current data profile. "
            "Recommendations never change data automatically.",
        ).pack(fill="x", pady=(0, theme.PAD_M))
        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, theme.PAD_M))
        self._refresh_button = ctk.CTkButton(
            toolbar, text="Refresh local analysis", command=self.refresh
        )
        self._refresh_button.pack(side="left")
        self._llm_button = ctk.CTkButton(
            toolbar, text="Ask LLM", command=self.ask_llm
        )
        self._llm_button.pack(side="left", padx=theme.PAD_S)
        self._test_button = ctk.CTkButton(
            toolbar, text="Test connection", command=self.test_connection
        )
        self._test_button.pack(side="left", padx=theme.PAD_S)
        self._status = ctk.CTkLabel(toolbar, text="Local analysis is immediate.", text_color=theme.COLOR_MUTED)
        self._status.pack(side="left", padx=theme.PAD_S)
        self._scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)
        response_bar = ctk.CTkFrame(self.body, fg_color="transparent")
        response_bar.pack(fill="x", pady=(theme.PAD_M, 0))
        ctk.CTkLabel(response_bar, text="LLM response", anchor="w").pack(side="left")
        ctk.CTkButton(response_bar, text="Copy response", width=110, command=self.copy_response).pack(side="right")
        self._response = ctk.CTkTextbox(self.body, height=140, wrap="word")
        self._response.pack(fill="x", pady=(theme.PAD_S, 0))
        chat_label = ctk.CTkLabel(self.body, text="Ask about this study or dataset", anchor="w")
        chat_label.pack(fill="x", pady=(theme.PAD_M, 0))
        self._chat = ctk.CTkTextbox(self.body, height=180, wrap="word")
        self._chat.pack(fill="both", expand=True, pady=(theme.PAD_S, theme.PAD_S))
        chat_controls = ctk.CTkFrame(self.body, fg_color="transparent")
        chat_controls.pack(fill="x")
        self._chat_input = ctk.CTkEntry(
            chat_controls, placeholder_text="Ask: Which questions have missing or inconsistent responses?"
        )
        self._chat_input.pack(side="left", fill="x", expand=True)
        self._chat_input.bind("<Return>", lambda _event: self.send_chat())
        self._send_button = ctk.CTkButton(chat_controls, text="Send", width=80, command=self.send_chat)
        self._send_button.pack(side="left", padx=(theme.PAD_S, 0))
        self._chat_history: list[tuple[str, str]] = []
        self.refresh()

    def on_show(self) -> None:
        if self._built:
            self.refresh()

    def refresh(self) -> None:
        analysis = self.state.agent_analysis
        if analysis is None:
            self._clear_recommendations()
            ctk.CTkLabel(self._scroll, text="Load a data file to receive recommendations.").pack(anchor="w")
            return
        recommendations = DataManagementAdvisor().recommend(analysis, self.config.settings, use_llm=False)
        self._render_recommendations(recommendations)

    def ask_llm(self) -> None:
        """Request optional LLM advice without blocking the Tk event loop."""
        analysis = self.state.agent_analysis
        if analysis is None:
            self._status.configure(text="Load a data file first.")
            return
        self._llm_button.configure(state="disabled")
        self._test_button.configure(state="disabled")
        self._status.configure(text="LLM is reviewing the study context...")

        def worker() -> None:
            try:
                review = DataManagementAdvisor().review(
                    analysis,
                    self.config.settings,
                    self.state.questionnaire_text,
                )
                self.after(0, lambda: self._llm_complete(review))
            except Exception as exc:  # noqa: BLE001 - report in UI
                error_message = f"LLM review failed: {exc}"
                self.after(0, lambda: self._llm_complete(LLMReview(False, False, error_message)))

        threading.Thread(target=worker, daemon=True).start()

    def test_connection(self) -> None:
        """Verify the configured provider, model, and API key."""
        self._test_button.configure(state="disabled")
        self._llm_button.configure(state="disabled")
        self._status.configure(text="Testing LLM connection...")

        def worker() -> None:
            review = DataManagementAdvisor().test_connection(self.config.settings)
            self.after(0, lambda: self._connection_complete(review))

        threading.Thread(target=worker, daemon=True).start()

    def _connection_complete(self, review: LLMReview) -> None:
        self._test_button.configure(state="normal")
        self._llm_button.configure(state="normal")
        self._status.configure(text=review.status)
        self._set_response(review.response_text)

    def _llm_complete(self, review: LLMReview) -> None:
        self._llm_button.configure(state="normal")
        self._test_button.configure(state="normal")
        self._status.configure(text=review.status)
        self._set_response(review.response_text)
        if review.succeeded:
            self._render_recommendations(review.recommendations)

    def _set_response(self, text: str) -> None:
        self._response.delete("1.0", "end")
        self._response.insert("1.0", text or "No model response received.")

    def copy_response(self) -> None:
        """Copy the displayed response for review or project notes."""
        self.clipboard_clear()
        self.clipboard_append(self._response.get("1.0", "end").strip())
        self._status.configure(text="LLM response copied to clipboard.")

    def send_chat(self) -> None:
        """Send a QC question in the background using the loaded data context."""
        analysis = self.state.agent_analysis
        message = self._chat_input.get().strip()
        if analysis is None:
            self._status.configure(text="Load a data file first.")
            return
        if not message:
            return
        self._chat_input.delete(0, "end")
        self._append_chat("You", message)
        self._send_button.configure(state="disabled")
        self._status.configure(text="LLM is reviewing the questionnaire and data for your question...")

        def worker() -> None:
            review = DataManagementAdvisor().chat(
                analysis,
                self.config.settings,
                message,
                self.state.questionnaire_text,
                self._chat_history,
            )
            self.after(0, lambda: self._chat_complete(message, review))

        threading.Thread(target=worker, daemon=True).start()

    def _chat_complete(self, message: str, review: LLMReview) -> None:
        self._send_button.configure(state="normal")
        self._status.configure(text=review.status)
        answer = review.response_text or review.status
        self._append_chat("AI", answer)
        self._chat_history.extend([("user", message), ("assistant", answer)])
        self._chat_history = self._chat_history[-8:]

    def _append_chat(self, speaker: str, message: str) -> None:
        self._chat.configure(state="normal")
        self._chat.insert("end", f"{speaker}:\n{message}\n\n")
        self._chat.see("end")
        self._chat.configure(state="disabled")

    def _render_recommendations(self, recommendations) -> None:
        self._clear_recommendations()
        for recommendation in recommendations:
            frame = ctk.CTkFrame(self._scroll, fg_color=theme.COLOR_CARD, corner_radius=theme.CORNER_RADIUS)
            frame.pack(fill="x", pady=theme.PAD_S)
            ctk.CTkLabel(
                frame,
                text=f"{recommendation.priority.upper()}  {recommendation.title}",
                anchor="w",
                font=ctk.CTkFont(*theme.FONT_BODY),
            ).pack(fill="x", padx=theme.PAD_M, pady=(theme.PAD_M, 2))
            ctk.CTkLabel(frame, text=recommendation.rationale, anchor="w", wraplength=800).pack(
                fill="x", padx=theme.PAD_M, pady=2
            )
            ctk.CTkLabel(frame, text=f"Action: {recommendation.action}", anchor="w", wraplength=800).pack(
                fill="x", padx=theme.PAD_M, pady=(2, theme.PAD_M)
            )

    def _clear_recommendations(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()