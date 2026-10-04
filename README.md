# Promise Radar

A Streamlit-based AI web interface for analyzing chat conversations, extracting commitments, and surfacing follow-up actions.

## Overview

Promise Radar is designed for users who want to review chat histories from multiple sources and identify promises, deadlines, and unresolved obligations. The interface supports:

- WhatsApp chat uploads
- Plain text chat files
- Microsoft Teams-style conversation exports
- A simple prompt-driven output screen for AI-generated summaries

## Project structure

```text
.
├── app.py
├── chat_extractor.py
├── ai_chat_processor.py
├── requirements.txt
├── .gitignore
├── .streamlit/
│   └── config.toml
├── README.md
└── data/            # Optional folder for sample chat data
```

## Setup

```bash
cd "e:\MLH Hackathon\MLH-Hackathon-Indore-Pydata"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

The app opens on **Chat Upload** and provides five tabs:

1. Profile
2. About
3. Chat Upload
4. Output Interface
5. Dummy Analysis

The **Dummy Analysis** tab demonstrates sample AI commitments grouped into
owner-wise tables. It does not call an AI provider.

## Using chat input

In the **Chat Upload** tab, either enter chat text, upload one or more supported
chat files (`.txt`, `.log`, `.csv`, or `.json`), or provide both. Submit to
extract the messages and navigate to **Output Interface**, where you can review
the conversation and run an AI analysis.

## Chat extraction and AI analysis

`chat_extractor.py` normalizes `.txt`, `.log`, `.csv`, and `.json` chat exports into
records containing `user`, `text`, `timestamp`, and any extra `details`.
`ai_chat_processor.py` sends those records and a prompt to either Google Gemini
or a local Ollama model. Both modules use Python's standard library, so no
additional package installation is needed.

Example:

```python
from ai_chat_processor import analyze_chats
from chat_extractor import extract_chat_messages

with open("chat.txt", encoding="utf-8") as chat_file:
    messages = extract_chat_messages(chat_file.read(), "chat.txt")

answer = analyze_chats(
    messages,
    "Extract promises, owners, deadlines, and unresolved follow-ups.",
    provider="gemini",  # or "ollama"
)
print(answer)
```

On the Output Interface, select **Gemini API** or **Local Gemma 4 (Ollama)**.
For Gemini, enter the API key in the password field or
replace the empty `GEMINI_API_KEY=` value in the local `.env` file. The app reads
that file on each app rerun and analysis request. Set `GEMINI_MODEL` to the
exact API model ID (defaults to `gemma-4-31b-it`); use **Reload model** on the
Output Interface to refresh the model field from `.env`. Never put API keys in
source code. If a key was previously added to source code, revoke it and create
a replacement. For local analysis, start Ollama and pull/run an available Gemma 4
model before selecting local mode; the app calls Ollama's local chat API. The
default Ollama model tag is `gemma4:latest`; set
`OLLAMA_MODEL` if the tag available on your machine differs. The Ollama server
URL defaults to `http://localhost:11434` and can be changed with
`OLLAMA_BASE_URL`.

AI results are requested as a JSON array containing `owner`, `commitment`,
`committed_date`, `deadline`, `status`, `confidence`, `evidence`, and
`special_remarks`. The output shows owner-wise details, dates, status,
confidence, and the exact supporting chat quote. Missing fields display as
“Not specified”; committed dates are only included when the source message has
a timestamp.

After analysis, **Participant status profiles** provide an expandable profile
for each chat participant, with assigned commitments grouped as Done, In
Progress, Pending, Blocked, or Unclear. Work assigned to a name that does not
match a chat participant is listed separately.

Temporary AI provider errors (HTTP 500, 502, 503, or 504) are retried up to
three times. If the provider continues to fail, check service status and confirm
the configured Gemini model ID supports the `generateContent` API. The output
screen shows the commitment evidence but does not repeat the full source chat.
