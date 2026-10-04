import streamlit as st

from ai_chat_processor import analyze_chats, get_config_value
from chat_extractor import extract_chat_messages

st.set_page_config(
    page_title="Promise Radar",
    page_icon="🔮",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f3f8fc 0%, #ffffff 58%, #edf4f8 100%);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e5f2fa 0%, #f5f8fa 100%);
        border-right: 1px solid #d4e0e8;
    }
    h1, h2, h3 {
        color: #263746;
    }
    h1 {
        padding-bottom: 0.35rem;
        border-bottom: 3px solid #c4455a;
    }
    div.stButton > button {
        color: #ffffff;
        background: linear-gradient(90deg, #bd3e53, #d55b68);
        border: 1px solid #ad3449;
        border-radius: 8px;
    }
    div.stButton > button:hover {
        color: #ffffff;
        background: #a93246;
        border-color: #92283c;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d9e2e8;
        border-left: 4px solid #8fc5e3;
        padding: 0.85rem;
        border-radius: 9px;
        box-shadow: 0 2px 8px rgba(38, 55, 70, 0.06);
    }
    div.stButton {
        width: 100%;
    }
    div.stButton > button {
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Helpers ----------
def detect_chat_source(file_name: str) -> str:
    name = file_name.lower()
    if "whatsapp" in name:
        return "WhatsApp"
    if "team" in name or "microsoft" in name:
        return "Microsoft Teams"
    return "Text / Generic Chat"


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def submit_chat_input() -> None:
    chat_text = st.session_state.get("chat_text_input", "").strip()
    uploaded_files = st.session_state.get("chat_upload_input", [])
    if not chat_text and not uploaded_files:
        st.session_state["chat_submit_error"] = (
            "Paste a conversation or upload at least one chat file to continue."
        )
        return

    messages = []
    sources = []
    try:
        if chat_text:
            messages.extend(extract_chat_messages(chat_text, "pasted_chat.txt"))
            sources.append("Pasted chat")

        for uploaded_file in uploaded_files:
            file_messages = extract_chat_messages(
                uploaded_file.getvalue(), uploaded_file.name
            )
            messages.extend(file_messages)
            sources.append(uploaded_file.name)
    except ValueError as error:
        st.session_state["chat_submit_error"] = str(error)
        return

    if not messages:
        st.session_state["chat_submit_error"] = (
            "No chat messages were found in the provided text or uploaded files."
        )
        return

    st.session_state["chat_messages"] = messages
    st.session_state["chat_source_label"] = ", ".join(sources)
    st.session_state["chat_submit_error"] = ""
    st.session_state["ai_result"] = ""
    st.session_state["selected_tab"] = "Output Interface"


def refresh_gemini_model() -> None:
    configured_model = get_config_value("GEMINI_MODEL", "gemma-4-31b-it")
    st.session_state["gemini_model"] = configured_model
    st.session_state["_gemini_model_config"] = configured_model


# ---------- App header ----------
st.title("Promise Radar")
st.caption("AI-powered conversation intelligence for promises, commitments, and follow-ups")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Navigation")
    st.write("Track promises across chat conversations")
    st.markdown("---")
    st.write("Supported sources:")
    st.write("• WhatsApp chats")
    st.write("• Plain text conversations")
    st.write("• Microsoft Teams exports")

# ---------- Tabs ----------
if "selected_tab" not in st.session_state:
    st.session_state["selected_tab"] = "Profile"

selected_tab = st.radio(
    "Select a tab",
    ["Profile", "About", "Chat Upload", "Output Interface", "Dummy"],
    horizontal=True,
    key="selected_tab",
)

if selected_tab == "Profile":
    st.subheader("User Profile")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(
            """
            <div style='background:linear-gradient(135deg,#dff1fb,#f2f5f7); padding:20px; border:1px solid #d2e3ec; border-radius:12px; text-align:center;'>
                <h3 style='margin:0; color:#b83a50;'>👤</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        name = st.text_input("Name", value="Aarav Sharma")
        role = st.text_input("Role", value="Project Lead")
        team = st.text_input("Team / Organization", value="Promise Radar Team")

    st.markdown("---")

    metric_cols = st.columns(3)
    metric_cols[0].metric("Active Promises", "12", "+3")
    metric_cols[1].metric("Pending Follow-ups", "05", "-2")
    metric_cols[2].metric("Risk Alerts", "02", "Low")

    st.markdown("### Quick Notes")
    st.text_area(
        "Profile summary",
        value="Focuses on tracking commitments made in conversational data and turning them into actionable progress indicators.",
        height=120,
    )

elif selected_tab == "About":
    st.subheader("About Promise Radar")
    st.markdown(
        """
        Promise Radar is a lightweight AI interface designed to extract promises, commitments, deadlines,
        and follow-up actions from chat conversations.

        It helps users review information from multiple conversation sources and turn scattered chat history into
        a clear, actionable view of what was promised and what still needs attention.
        """
    )

    st.markdown("### Features")
    st.markdown(
        """
        - Upload WhatsApp, text, and Teams chat exports
        - Detect and organize chat sources
        - Extract tasks, commitments, deadlines, and action items
        - Generate a structured AI output using a custom prompt
        - Provide a clean dashboard for future reporting and monitoring
        """
    )

elif selected_tab == "Chat Upload":
    st.subheader("Chat Input")
    st.write("Enter a conversation, upload a chat file, or use both. Either input is optional.")
    st.text_area(
        "Enter chat text (optional)",
        key="chat_text_input",
        height=220,
        placeholder="Example:\nAlice: I will send the report by Friday.\nBob: Thanks, I will review it.",
    )
    uploaded_files = st.file_uploader(
        "Upload chat files (optional)",
        type=["txt", "csv", "json", "log"],
        accept_multiple_files=True,
        key="chat_upload_input",
    )

    if uploaded_files:
        st.success(
            "{} file(s) selected. You can submit these without entering text.".format(
                len(uploaded_files)
            )
        )
        for file in uploaded_files:
            source_type = detect_chat_source(file.name)
            st.markdown(
                f"### {file.name}\n"
                f"- Source: {source_type}\n"
                f"- Size: {format_file_size(file.size)}\n"
            )

            preview_text = file.getvalue().decode("utf-8", errors="replace")
            preview_sample = preview_text[:700]
            st.code(preview_sample if preview_sample else "No content available for preview.")
            st.markdown("---")

    st.button("Submit and View Output", on_click=submit_chat_input)
    if st.session_state.get("chat_submit_error"):
        st.error(st.session_state["chat_submit_error"])

    st.markdown("### Supported format summary")
    summary_cols = st.columns(3)
    summary_cols[0].write("📱 WhatsApp")
    summary_cols[1].write("📝 Text / CSV / JSON")
    summary_cols[2].write("💼 Microsoft Teams")

elif selected_tab == "Output Interface":
    st.subheader("Conversation Analysis")
    messages = st.session_state.get("chat_messages", [])

    if not messages:
        st.info("Enter chat text or upload a chat file in Chat Upload, then submit it to view and analyze it here.")
    else:
        participants = sorted(set(message["user"] for message in messages))
        summary_cols = st.columns(3)
        summary_cols[0].metric("Messages", str(len(messages)))
        summary_cols[1].metric("Participants", str(len(participants)))
        summary_cols[2].metric("Source", st.session_state.get("chat_source_label", "Chat"))

        analyze_clicked = st.button("Analyze Conversation")

        st.markdown("### Extracted conversation")
        for message in messages:
            timestamp = message.get("timestamp")
            heading = message["user"]
            if timestamp:
                heading += " · " + timestamp
            st.markdown("**{}**".format(heading))
            st.write(message["text"])
            details = message.get("details", {})
            if details:
                st.caption("Additional details: {}".format(details))
            st.markdown("---")

        st.markdown("### Generate an AI analysis")
        provider = st.selectbox(
            "AI provider",
            ["Gemini", "Local Gemma (Ollama)"],
            key="analysis_provider",
        )
        provider_key = "gemini" if provider == "Gemini" else "ollama"
        if provider_key == "gemini":
            configured_model = get_config_value(
                "GEMINI_MODEL", "gemma-4-31b-it"
            )
            if st.session_state.get("_gemini_model_config") != configured_model:
                st.session_state["gemini_model"] = configured_model
                st.session_state["_gemini_model_config"] = configured_model

            model_col, refresh_col = st.columns([4, 1])
            with model_col:
                model = st.text_input(
                    "Gemini API model",
                    key="gemini_model",
                    help="Loaded from GEMINI_MODEL in .env. Use the exact model ID supported by the Gemini API.",
                )
            with refresh_col:
                st.markdown("<br>", unsafe_allow_html=True)
                st.button(
                    "Reload model",
                    on_click=refresh_gemini_model,
                    help="Read GEMINI_MODEL from .env again.",
                )
            api_key = st.text_input(
                "Gemini API key",
                type="password",
                key="gemini_api_key",
                help="Enter your key here, or set GEMINI_API_KEY in the environment.",
            )
        else:
            model = st.text_input(
                "Ollama model tag",
                value="gemma4:latest",
                key="ollama_model",
                help="Use the exact model tag installed in Ollama.",
            )
            api_key = None
            st.caption("Ollama must be running locally with the selected model available.")

        custom_prompt = st.text_area(
            "Analysis instructions",
            value=(
                "Summarize the promises, commitments, owners, deadlines, and action items. "
                "Highlight unresolved follow-ups and risks. Do not invent missing details."
            ),
            height=120,
        )
        if analyze_clicked:
            st.session_state["ai_result"] = ""
            try:
                with st.spinner("Generating analysis..."):
                    result = analyze_chats(
                        messages,
                        custom_prompt,
                        provider=provider_key,
                        model=model.strip() or None,
                        api_key=api_key or None,
                    )
            except (ValueError, RuntimeError) as error:
                st.error(str(error))
            else:
                st.session_state["ai_result"] = result

        if st.session_state.get("ai_result"):
            st.markdown("### AI Analysis")
            st.markdown(st.session_state["ai_result"])

else:
    st.subheader("Dummy Tab")
    st.markdown("This section is intentionally left as a placeholder for future features such as dashboards, filters, or additional analysis modules.")

    st.write("Planned additions:")
    st.write("- Promise risk scoring")
    st.write("- Meeting summary")
    st.write("- Team-wise progress dashboard")
    st.write("- Export to PDF / CSV")

# ---------- Footer ----------
st.markdown("---")
st.caption("Promise Radar • built for AI-powered conversation analysis")
