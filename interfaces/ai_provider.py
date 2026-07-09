"""
interfaces/ai_provider.py

Abstract base class for AI response generation providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIProviderInterface(ABC):
    """
    Contract for AI text generation.

    Implementations can connect to Google Gemini, Groq, OpenRouter, etc.
    """

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Generate a text reply for the user based on prompt and conversation history.

        Args:
            prompt:       The incoming message text from the user.
            chat_history: A list of dicts representing past messages,
                          e.g. [{"role": "user", "text": "..."}, {"role": "ai", "text": "..."}]

        Returns:
            The generated response string.
        """
        pass
