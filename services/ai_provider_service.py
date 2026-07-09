"""
services/ai_provider_service.py

Google Gemini REST API implementation of the AIProviderInterface.
"""

from __future__ import annotations

import logging
import aiohttp

from config import settings
from interfaces.ai_provider import AIProviderInterface

logger = logging.getLogger(__name__)


class GeminiProvider(AIProviderInterface):
    """
    Integrates Google Gemini models (e.g. gemini-2.5-flash)
    via raw HTTP POST requests to Google GenAI REST endpoint.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model or settings.gemini_model

    async def generate_response(
        self,
        prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Generate a reply from Gemini using the generateContent REST API.
        """
        if not self._api_key:
            logger.warning("Gemini API key is not configured. Falling back to default warning response.")
            return "⚠️ AI Support is currently unavailable (API key not configured)."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"

        # Build contents from history + prompt
        contents = []
        if chat_history:
            for msg in chat_history:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("text", "")}]
                })

        # Append current user prompt
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        system_instruction = (
            "You are a helpful and polite customer support AI assistant for the Telegram Commerce Platform. "
            "Help the customer answer queries about browsing products, product prices, placing orders, "
            "and submitting payment screenshots. Keep your answers concise, structured, and easy to read. "
            "If the customer asks for human support, wants to contact a human, or asks a complex question "
            "that you cannot answer, suggest that they type /human to connect with a support agent."
        )

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800,
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        logger.error("Gemini API error | status=%s | response=%s", resp.status, err_text)
                        return "⚠️ Sorry, I encountered an error while processing your request. Please try again later or type /human."

                    data = await resp.json()
                    
                    # Safely traverse the response json to get the generated text
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()

                    logger.error("Gemini API response missing generated text | response=%s", data)
                    return "⚠️ Sorry, I could not generate a response. Please try /human to contact support."

        except Exception as exc:
            logger.exception("Failed to connect to Gemini API | error=%s", exc)
            return "⚠️ Connection error to AI assistant. Please try /human."
