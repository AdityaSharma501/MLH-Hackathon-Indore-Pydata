"""Send extracted chat messages to Google Gemini or a local Ollama model."""

import json
import os
import re
import time
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
    result = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            if error.code in (500, 502, 503, 504) and attempt < 2:
                time.sleep(attempt + 1)
                continue
            if error.code in (500, 502, 503, 504):
                raise RuntimeError(
                    "AI provider returned HTTP {} after 3 attempts. This is usually "
                    "a temporary provider or model issue; wait and retry, and verify "
                    "that the configured model supports generateContent. Details: {}"
                    .format(error.code, error_body)
                ) from error
            raise RuntimeError(
                "AI provider returned HTTP {}: {}".format(error.code, error_body)
            ) from error
        except URLError as error:
            raise RuntimeError(
                f"Could not connect to AI provider: {error.reason}"
            ) from error
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


def parse_commitments(response: str) -> List[Dict[str, Any]]:
    """Parse AI commitment records into the app's stable output schema."""
    content = response.strip()
    fenced_match = re.match(
        r"^```(?:json)?\s*(.*?)\s*```$", content, flags=re.IGNORECASE | re.DOTALL
    )
    if fenced_match:
        content = fenced_match.group(1)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(
            "The AI response was not valid commitments JSON. Please analyze again."
        ) from error

    if isinstance(parsed, dict):
        parsed = parsed.get("commitments")
    if not isinstance(parsed, list):
        raise ValueError("The AI response must contain a JSON list of commitments.")

    rows = []
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError("Each AI commitment must be a JSON object.")
        owner = item.get("owner", item.get("committer_name"))
        deadline = item.get("deadline", item.get("expected_done_date"))
        remarks = item.get("special_remarks")
        evidence = item.get("evidence", item.get("proof"))
        raw_confidence = item.get("confidence")
        if raw_confidence is None or raw_confidence == "":
            confidence = None
        else:
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError) as error:
                raise ValueError("Commitment confidence must be a number from 0 to 1.") from error
            if not 0 <= confidence <= 1:
                raise ValueError("Commitment confidence must be between 0 and 1.")

        def display_value(value: Any) -> str:
            return (
                str(value).strip()
                if value is not None and str(value).strip()
                else "Not specified"
            )

        row = {
            "owner": display_value(owner),
            "commitment": display_value(item.get("commitment")),
            "committed_date": display_value(item.get("committed_date")),
            "deadline": display_value(deadline),
            "status": display_value(item.get("status")),
            "confidence": confidence,
            "special_remarks": display_value(remarks),
            "evidence": display_value(evidence),
        }
        rows.append(row)
    return rows


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
