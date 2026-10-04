"""Send extracted chat messages to Google Gemini or a local Ollama model."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def get_config_value(name: str, default: Optional[str] = None) -> Optional[str]:
    """Read a setting from the process environment or the project .env file."""
    environment_value = os.getenv(name)
    if environment_value:
        return environment_value

    env_file = Path(__file__).with_name(".env")
    if not env_file.is_file():
        return default

    with env_file.open("r") as file:
        for line in file:
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            if entry.startswith("export "):
                entry = entry[7:].lstrip()
            setting_name, separator, value = entry.partition("=")
            if separator and setting_name.strip() == name:
                setting_value = value.strip().strip("\"'")
                return setting_value or default
    return default


def _post_json(
    url: str,
    payload: Dict[str, Any],
    timeout: int,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"AI provider returned HTTP {error.code}: {error_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Could not connect to AI provider: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("AI provider returned invalid JSON.") from error

    if not isinstance(result, dict):
        raise RuntimeError("AI provider returned an unexpected response.")
    return result


def _chat_prompt(
    messages: List[Dict[str, Any]], prompt: str
) -> str:
    serialized_messages = json.dumps(messages, ensure_ascii=False, indent=2)
    return (
        f"{prompt}\n\n"
        "Analyze the following extracted chat messages. Use their timestamps and "
        "details where relevant. Do not invent missing information.\n\n"
        f"{serialized_messages}"
    )


def analyze_chats(
    messages: List[Dict[str, Any]],
    prompt: str,
    provider: str = "gemini",
    *,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    ollama_url: Optional[str] = None,
    timeout: int = 120,
) -> str:
    """Analyze normalized chat messages using Gemini or Ollama.

    Configure Gemini with ``GEMINI_API_KEY``. Configure local Ollama with
    ``OLLAMA_BASE_URL`` (defaults to localhost:11434) and ``OLLAMA_MODEL``
    (defaults to ``gemma4:latest``).
    """
    if not messages:
        raise ValueError("At least one extracted chat message is required.")
    if not prompt.strip():
        raise ValueError("The analysis prompt cannot be empty.")

    provider_name = provider.strip().lower()
    content = _chat_prompt(messages, prompt.strip())

    if provider_name == "gemini":
        key = api_key or get_config_value("GEMINI_API_KEY")
        if not key:
            raise ValueError("Set GEMINI_API_KEY or pass api_key to use Gemini.")
        model_name = model or get_config_value("GEMINI_MODEL", "gemma-4-31b-it")
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(model_name, safe='')}:generateContent"
        )
        result = _post_json(
            endpoint,
            {
                "contents": [{"role": "user", "parts": [{"text": content}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout,
            headers={"x-goog-api-key": key},
        )
        try:
            parts = result["candidates"][0]["content"]["parts"]
            response = "\n".join(
                part["text"] for part in parts if isinstance(part.get("text"), str)
            )
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Gemini response did not include generated text.") from error
        if not response:
            raise RuntimeError("Gemini returned an empty response.")
        return response

    if provider_name == "ollama":
        base_url = (
            ollama_url
            or get_config_value("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        model_name = model or get_config_value("OLLAMA_MODEL", "gemma4:latest")
        result = _post_json(
            f"{base_url}/api/chat",
            {
                "model": model_name,
                "messages": [{"role": "user", "content": content}],
                "stream": False,
            },
            timeout,
        )
        try:
            response = result["message"]["content"]
        except (KeyError, TypeError) as error:
            raise RuntimeError("Ollama response did not include generated text.") from error
        if not isinstance(response, str) or not response:
            raise RuntimeError("Ollama returned an empty response.")
        return response

    raise ValueError("Unsupported provider. Choose 'gemini' or 'ollama'.")
