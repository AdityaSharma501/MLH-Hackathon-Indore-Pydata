"""Extract normalized chat messages from text, CSV, and JSON exports."""

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


_SENDER_KEYS = (
    "sender",
    "user",
    "username",
    "user_name",
    "display_name",
    "author",
    "from",
    "from_name",
    "name",
)
_TEXT_KEYS = ("text", "message", "message_text", "chat_text", "body", "content")
_TIME_KEYS = (
    "timestamp",
    "sent_at",
    "sent_time",
    "message_time",
    "time",
    "date",
    "datetime",
    "created_at",
)
_COLLECTION_KEYS = ("messages", "chats", "conversation", "items", "data")

_TIMESTAMP = (
    r"(?:\d{4}-\d{1,2}-\d{1,2}[T ]\d{1,2}:\d{2}"
    r"(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?"
    r"|\d{1,2}[./-]\d{1,2}[./-]\d{2,4},?\s+\d{1,2}:\d{2}"
    r"(?:\s*[APap][Mm])?)"
)
_TIMESTAMPED_LINE = re.compile(
    rf"^\s*\[?(?P<timestamp>{_TIMESTAMP})\]?\s*[-–]\s*"
    r"(?P<user>[^:]{1,120}):\s?(?P<text>.*)$"
)
_SENDER_LINE = re.compile(r"^\s*(?P<user>[^:]{1,120}):\s?(?P<text>.*)$")


def _normalized_keys(record: Dict[str, Any]) -> Dict[str, str]:
    return {str(key).strip().lower().replace(" ", "_"): key for key in record}


def _text_value(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("name", "display_name", "username", "id"):
            if key in value and value[key] is not None:
                return str(value[key])
    if value is None:
        return ""
    return str(value)


def _from_mapping(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    keys = _normalized_keys(record)
    sender_key = next((keys[key] for key in _SENDER_KEYS if key in keys), None)
    text_key = next((keys[key] for key in _TEXT_KEYS if key in keys), None)

    if text_key is None:
        return None

    timestamp_key = next((keys[key] for key in _TIME_KEYS if key in keys), None)
    known_keys = {key for key in (sender_key, text_key, timestamp_key) if key is not None}
    details = {str(key): value for key, value in record.items() if key not in known_keys}

    return {
        "user": _text_value(record[sender_key]) if sender_key is not None else "Unknown",
        "text": _text_value(record[text_key]),
        "timestamp": (
            _text_value(record[timestamp_key]) if timestamp_key is not None else None
        ),
        "details": details,
    }


def _json_messages(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, list):
        messages = []  # type: List[Dict[str, Any]]
        for item in value:
            messages.extend(_json_messages(item))
        return messages

    if not isinstance(value, dict):
        return []

    message = _from_mapping(value)
    if message is not None:
        return [message]

    keys = _normalized_keys(value)
    for collection_name in _COLLECTION_KEYS:
        if collection_name in keys:
            return _json_messages(value[keys[collection_name]])
    return []


def _csv_messages(text: str) -> List[Dict[str, Any]]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    messages = []  # type: List[Dict[str, Any]]
    for row in reader:
        if row is None:
            continue
        message = _from_mapping(dict(row))
        if message is not None:
            messages.append(message)
    return messages


def _text_messages(text: str) -> List[Dict[str, Any]]:
    messages = []  # type: List[Dict[str, Any]]
    for line in text.splitlines():
        if not line.strip():
            continue

        match = _TIMESTAMPED_LINE.match(line)
        if match:
            messages.append(
                {
                    "user": match.group("user").strip(),
                    "text": match.group("text"),
                    "timestamp": match.group("timestamp").strip(),
                    "details": {},
                }
            )
            continue

        match = _SENDER_LINE.match(line)
        if match:
            messages.append(
                {
                    "user": match.group("user").strip(),
                    "text": match.group("text"),
                    "timestamp": None,
                    "details": {},
                }
            )
            continue

        if messages:
            messages[-1]["text"] += "\n" + line
        else:
            messages.append(
                {"user": "Unknown", "text": line, "timestamp": None, "details": {}}
            )
    return messages


def extract_chat_messages(
    content: Union[str, bytes], file_name: str = ""
) -> List[Dict[str, Any]]:
    """Return chat messages with user, text, timestamp, and extra details.

    JSON and CSV input must contain recognizable message/text columns. Plain-text
    exports may use ``[timestamp] - Name: message`` or ``Name: message`` lines.
    """
    if isinstance(content, bytes):
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content.lstrip("\ufeff")

    suffix = Path(file_name).suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON chat export: {error}") from error
        messages = _json_messages(data)
        collection_present = isinstance(data, dict) and any(
            key in _normalized_keys(data) for key in _COLLECTION_KEYS
        )
        if not messages and data and not collection_present:
            raise ValueError("JSON does not contain recognizable chat messages.")
        return messages

    if suffix == ".csv":
        messages = _csv_messages(text)
        if text.strip() and not messages:
            raise ValueError("CSV does not contain recognizable chat columns.")
        return messages

    return _text_messages(text)
