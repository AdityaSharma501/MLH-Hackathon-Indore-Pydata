import streamlit as st

from ai_chat_processor import analyze_chats, get_config_value, parse_commitments
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
        background: #ffffff;
        color: #102a43;
    }
    [data-testid="stSidebar"] {
        background: #f2f5f8;
        border-right: 1px solid #d8e0e8;
    }
    h2, h3 {
        color: #102a43;
    }
    h1 {
        padding-bottom: 0.35rem;
        color: #ff9f1c;
        border-bottom: 3px solid #ff9f1c;
    }
    [data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"],
    [data-testid="stMarkdownContainer"] {
        color: #102a43;
    }
    div.stButton > button {
        color: #ffffff;
        background: linear-gradient(90deg, #f28c00, #ffad33);
        border: 1px solid #e88700;
        border-radius: 8px;
    }
    div.stButton > button:hover {
        color: #ffffff;
        background: #d97700;
        border-color: #c66d00;
    }
    [data-testid="stMetric"] {
        background: #f2f5f8;
        border: 1px solid #d8e0e8;
        border-left: 4px solid #ff9f1c;
        padding: 0.85rem;
        border-radius: 9px;
        box-shadow: 0 2px 8px rgba(16, 42, 67, 0.08);
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: #102a43;
    }
    .home-description {
        background: linear-gradient(120deg, #15324d, #102a43);
        border: 1px solid #294963;
        border-left: 5px solid #ff9f1c;
        border-radius: 12px;
        color: #ffffff;
        margin: 0.5rem 0 1.5rem;
        padding: 1rem 1.5rem;
    }
    .home-description ul {
        margin: 0;
        padding-left: 1.3rem;
    }
    .home-description li {
        color: #ffffff;
        margin: 0.35rem 0;
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


if "selected_tab" not in st.session_state:
    st.session_state["selected_tab"] = "Chat Upload"

# ---------- App header ----------
st.title("Promise Radar (Evidence Based)")
st.caption("AI-powered conversation intelligence for promises, commitments, and follow-ups")
if st.session_state["selected_tab"] == "Chat Upload":
    st.markdown(
        """
        <div class="home-description">
            <ul>
                <li>Turn conversations into clear commitments.</li>
                <li>See who is responsible and when work is due.</li>
                <li>Review each finding with its original chat proof.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
                <h3 style='margin:0; color:#f28c00;'>👤</h3>
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

        st.markdown("### Commitment analysis")
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
            "Analysis instructions (optional)",
            value=(
                "Extract each explicit or strongly implied promise, commitment, task, "
                "or follow-up from the chat. Return ONLY valid JSON in this exact shape: "
                '{"commitments":[{"commitment":"short description",'
                '"committer_name":"person responsible",'
                '"status":"Pending | In progress | Done | Unclear",'
                '"expected_done_date":"date or deadline exactly as stated, otherwise Not specified",'
                '"special_remarks":"risks, dependencies, or other useful note; otherwise Not specified",'
                '"proof":"exact supporting chat quote, with speaker and timestamp if available"}]}. '
                "Use an empty commitments array if there are no commitments. Do not infer "
                "a date, owner, status, or evidence that the chat does not support."
            ),
            height=210,
        )
        analyze_clicked = st.button("Analyze Conversation")

        if analyze_clicked:
            st.session_state["ai_result"] = ""
            st.session_state["ai_commitments"] = None
            try:
                with st.spinner("Generating analysis..."):
                    result = analyze_chats(
                        messages,
                        custom_prompt,
                        provider=provider_key,
                        model=model.strip() or None,
                        api_key=api_key or None,
                    )
                    commitments = parse_commitments(result)
            except (ValueError, RuntimeError) as error:
                st.error(str(error))
            else:
                st.session_state["ai_result"] = result
                st.session_state["ai_commitments"] = commitments

        commitments = st.session_state.get("ai_commitments")
        if commitments is not None:
            st.markdown("### AI results")
            if commitments:
                display_rows = [
                    {
                        "Commitment": item["commitment"],
                        "Committer": item["committer_name"],
                        "Status": item["status"],
                        "Expected done date": item["expected_done_date"],
                        "Special remarks": item["special_remarks"],
                        "Chat proof": item["proof"],
                    }
                    for item in commitments
                ]
                st.table(display_rows)
            else:
                st.info("The AI found no commitments supported by the provided chat.")

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
