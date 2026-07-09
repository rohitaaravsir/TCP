"""
tests/unit/test_ai_provider.py

Unit tests for services/ai_provider_service.py (GeminiProvider)
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from services.ai_provider_service import GeminiProvider


@pytest.mark.asyncio
async def test_gemini_provider_missing_key_warning():
    """If api_key is missing, it should return a fallback warning message immediately."""
    provider = GeminiProvider(api_key="")
    response = await provider.generate_response("Hello")
    assert "unavailable" in response.lower() or "not configured" in response.lower()


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_gemini_provider_success(mock_post):
    """If API returns 200, it should parse and return the generated text response."""
    # Set up mock response
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Hello! I am Gemini, how can I help you today?"}]
                }
            }
        ]
    })
    
    # Mock context manager behavior
    mock_post.return_value.__aenter__.return_value = mock_resp

    provider = GeminiProvider(api_key="dummy_api_key", model="gemini-2.5-flash")
    response = await provider.generate_response("Hello")

    assert response == "Hello! I am Gemini, how can I help you today?"
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert payload["contents"][-1]["parts"][0]["text"] == "Hello"


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_gemini_provider_api_error(mock_post):
    """If API returns non-200 status, it should return a graceful error message."""
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="Internal Server Error")
    mock_post.return_value.__aenter__.return_value = mock_resp

    provider = GeminiProvider(api_key="dummy_api_key")
    response = await provider.generate_response("Hello")

    assert "error" in response.lower() or "try again" in response.lower()
