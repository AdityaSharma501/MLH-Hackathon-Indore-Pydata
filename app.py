from html import escape

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
    .demo-metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
        margin: 1rem 0 1.5rem;
    }
    .demo-metric {
        color: #ffffff;
        padding: 1rem 1.2rem;
        border-radius: 12px;
        box-shadow: 0 5px 14px rgba(16, 42, 67, 0.12);
    }
    .demo-metric strong {
        display: block;
        font-size: 1.8rem;
        line-height: 1.2;
    }
    .demo-metric span {
        font-size: 0.9rem;
        opacity: 0.95;
    }
    .demo-metric--blue {
        background: linear-gradient(120deg, #176b87, #2589a2);
    }
    .demo-metric--orange {
        background: linear-gradient(120deg, #e87500, #ffa52e);
    }
    .demo-metric--green {
        background: linear-gradient(120deg, #23805b, #38a879);
    }
    .demo-owner {
        margin: 1.5rem 0 0.75rem;
        padding: 0.8rem 1rem;
        color: #ffffff;
        background: linear-gradient(100deg, #102a43, #176b87);
        border-left: 5px solid #ff9f1c;
        border-radius: 9px;
        font-size: 1.15rem;
        font-weight: 700;
    }
    .demo-table-wrap {
        overflow-x: auto;
        border: 1px solid #d6e0e8;
        border-radius: 10px;
        box-shadow: 0 4px 14px rgba(16, 42, 67, 0.08);
    }
    table.demo-table {
        width: 100%;
        border-collapse: collapse;
        background: #ffffff;
        color: #102a43;
    }
    .demo-table th {
        padding: 0.75rem;
        text-align: left;
        background: #eaf2f7;
        color: #102a43;
        border-bottom: 2px solid #ff9f1c;
        white-space: nowrap;
    }
    .demo-table td {
        padding: 0.75rem;
        vertical-align: top;
        border-bottom: 1px solid #e4ebf0;
    }
    .demo-table tbody tr:nth-child(even) {
        background: #f7fafc;
    }
    .demo-table tbody tr:last-child td {
        border-bottom: 0;
    }
    .demo-status {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-weight: 700;
        white-space: nowrap;
    }
    .demo-status--done {
        color: #17623f;
        background: #d9f3e5;
    }
    .demo-status--progress {
        color: #145b78;
        background: #d9f0fa;
    }
    .demo-status--pending {
        color: #815000;
        background: #fff0ce;
    }
    .demo-status--blocked {
        color: #8a2637;
        background: #fde1e5;
    }
    .demo-status--unclear {
        color: #4d5965;
        background: #e8edf1;
    }
    .demo-confidence {
        color: #176b87;
        font-weight: 700;
        white-space: nowrap;
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


def commitment_status_bucket(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in ("done", "complete", "completed", "finished", "closed"):
        return "Done"
    if normalized in ("in progress", "in-progress", "ongoing", "started"):
        return "In Progress"
    if normalized in ("pending", "open", "to do", "todo", "not started"):
        return "Pending"
    if "block" in normalized:
        return "Blocked"
    return "Unclear"


def render_commitment_table(owner: str, commitments: list) -> None:
    status_styles = {
        "Done": "demo-status--done",
        "In Progress": "demo-status--progress",
        "Pending": "demo-status--pending",
        "Blocked": "demo-status--blocked",
        "Unclear": "demo-status--unclear",
    }
    table_rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td>"
        '<td><span class="demo-status {}">{}</span></td>'
        '<td><span class="demo-confidence">{}</span></td>'
        "<td>{}</td><td>{}</td></tr>".format(
            escape(str(item.get("commitment") or "Not specified")),
            escape(str(item.get("committed_date") or "Not specified")),
            escape(
                str(
                    item.get("deadline")
                    or item.get("expected_done_date")
                    or "Not specified"
                )
            ),
            status_styles[
                commitment_status_bucket(str(item.get("status") or "Unclear"))
            ],
            escape(str(item.get("status") or "Unclear").title()),
            (
                "{:.0%}".format(item["confidence"])
                if isinstance(item.get("confidence"), (int, float))
                else "Not specified"
            ),
            escape(
                str(item.get("special_remarks") or "Not specified")
            ),
            escape(
                str(item.get("evidence") or item.get("proof") or "Not specified")
            ),
        )
        for item in commitments
    )
    st.markdown(
        '<div class="demo-owner">👤 {}</div>'
        '<div class="demo-table-wrap"><table class="demo-table">'
        "<thead><tr><th>Committed task</th><th>Committed date</th>"
        "<th>Deadline</th><th>Status</th><th>Confidence</th>"
        "<th>Special remarks</th><th>Chat evidence</th></tr></thead>"
        "<tbody>{}</tbody></table></div>".format(escape(owner), table_rows),
        unsafe_allow_html=True,
    )


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
    ["Profile", "About", "Chat Upload", "Output Interface", "Dummy Analysis"],
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
        provider = st.radio(
            "Choose an analysis provider",
            ["Gemini API", "Local Gemma 4 (Ollama)"],
            horizontal=True,
            key="analysis_provider_choice",
        )
        provider_key = "gemini" if provider == "Gemini API" else "ollama"
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
                help="Enter your key here, or set GEMINI_API_KEY in .env.",
            )
            st.caption(
                "Gemini sends the conversation to Google's API. Your API key can "
                "be read from .env when the field is left blank."
            )
        else:
            configured_ollama_model = get_config_value(
                "OLLAMA_MODEL", "gemma4:latest"
            )
            model = st.text_input(
                "Local Gemma 4 model tag",
                value=configured_ollama_model,
                key="ollama_model",
                help="Must match the Gemma 4 model tag installed in Ollama.",
            )
            api_key = None
            st.caption(
                "Local mode sends the conversation to Ollama on this machine. "
                "Start Ollama and ensure the selected Gemma 4 model is available."
            )

        custom_prompt = st.text_area(
            "Analysis instructions (optional)",
            value=(
                "Extract explicit or strongly implied promises, commitments, tasks, or "
                "follow-ups. Return ONLY a valid JSON array (not markdown and no wrapper "
                "object). Every item must use exactly these keys: owner (speaker who "
                "commits to do the work, or null), commitment (short task description), "
                "committed_date (date/time of the source message, or null if unavailable), "
                "deadline (stated due date or null), status (pending, in progress, done, "
                "blocked, or unclear), confidence (number from 0 to 1), evidence (exact "
                "supporting chat quote), special_remarks (short note or null). Example: "
                '[{"owner":"Amit","commitment":"Complete PostgreSQL migration",'
                '"committed_date":null,"deadline":"Friday","status":"pending",'
                '"confidence":0.96,"evidence":"I\'ll complete the PostgreSQL migration by Friday.",'
                '"special_remarks":null}]. Use [] if no commitments. Never invent a date, '
                "owner, status, confidence, or evidence. Only set committed_date when "
                "a timestamp is present on the message that made the commitment."
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
                owners = sorted(set(item["owner"] for item in commitments))
                pending_count = sum(
                    1
                    for item in commitments
                    if commitment_status_bucket(item["status"]) == "Pending"
                )
                st.markdown(
                    """
                    <div class="demo-metrics">
                        <div class="demo-metric demo-metric--blue">
                            <strong>{}</strong><span>Total commitments</span>
                        </div>
                        <div class="demo-metric demo-metric--orange">
                            <strong>{}</strong><span>Owners</span>
                        </div>
                        <div class="demo-metric demo-metric--green">
                            <strong>{}</strong><span>Pending tasks</span>
                        </div>
                    </div>
                    """.format(len(commitments), len(owners), pending_count),
                    unsafe_allow_html=True,
                )
                st.markdown("### Commitments by owner")
                for owner in owners:
                    owner_commitments = [
                        item for item in commitments if item["owner"] == owner
                    ]
                    render_commitment_table(owner, owner_commitments)
            else:
                st.info("The AI found no commitments supported by the provided chat.")

            st.markdown("### Participant status profiles")
            st.caption(
                "Open a participant to see their AI-assigned work, grouped by status."
            )
            status_order = ("Done", "In Progress", "Pending", "Blocked", "Unclear")
            participant_keys = set(
                participant.strip().casefold() for participant in participants
            )
            assigned_work = []

            for participant in participants:
                participant_work = [
                    item for item in commitments
                    if item["owner"].strip().casefold()
                    == participant.strip().casefold()
                ]
                grouped_work = dict((status, []) for status in status_order)
                for item in participant_work:
                    grouped_work[commitment_status_bucket(item["status"])].append(item)

                counts = [
                    "{} {}".format(len(grouped_work[status]), status.lower())
                    for status in status_order
                    if grouped_work[status]
                ]
                title = participant
                if counts:
                    title += " — " + ", ".join(counts)
                else:
                    title += " — no assigned work"

                with st.expander(title):
                    metric_cols = st.columns(len(status_order))
                    for index, status in enumerate(status_order):
                        metric_cols[index].metric(
                            status, str(len(grouped_work[status]))
                        )

                    if not participant_work:
                        st.info(
                            "No commitments were assigned to this participant in the AI results."
                        )
                    for status in status_order:
                        status_work = grouped_work[status]
                        if status_work:
                            st.markdown("#### {}".format(status))
                            for item in status_work:
                                st.markdown("**{}**".format(item["commitment"]))
                                st.write(
                                    "Committed date: {}".format(
                                        item["committed_date"]
                                    )
                                )
                                st.write(
                                    "Deadline: {}".format(item["deadline"])
                                )
                                if item["confidence"] is not None:
                                    st.write(
                                        "Confidence: {:.0%}".format(
                                            item["confidence"]
                                        )
                                    )
                                if item["special_remarks"] != "Not specified":
                                    st.write(
                                        "Remark: {}".format(
                                            item["special_remarks"]
                                        )
                                    )
                                st.caption("Evidence: {}".format(item["evidence"]))

            for item in commitments:
                assignee = item["owner"].strip().casefold()
                if assignee not in participant_keys:
                    assigned_work.append(item)

            if assigned_work:
                with st.expander(
                    "Unassigned or unmatched work ({})".format(len(assigned_work))
                ):
                    st.caption(
                        "The AI assignee was not an exact match for a participant name "
                        "in the extracted chat."
                    )
                    for item in assigned_work:
                        st.markdown(
                            "**{}** — {} · {}".format(
                                item["commitment"],
                                item["owner"],
                                commitment_status_bucket(item["status"]),
                            )
                        )
                        st.caption("Evidence: {}".format(item["evidence"]))

elif selected_tab == "Dummy Analysis":
    st.subheader("Sample AI Commitment Analysis")
    st.caption(
        "Preview of the structured Gemma/Gemini response, grouped by owner. "
        "The committed date is shown as unavailable because it is not present in the sample."
    )
    sample_commitments = parse_commitments(
        """
        [
          {
            "owner": "Amit",
            "commitment": "Complete PostgreSQL migration",
            "deadline": "Friday",
            "status": "pending",
            "confidence": 0.96,
            "evidence": "I'll complete the PostgreSQL migration by Friday."
          },
          {
            "owner": "Amit",
            "commitment": "Check authentication API",
            "deadline": "Tomorrow",
            "status": "pending",
            "confidence": 0.91,
            "evidence": "Yes, I'll do that tomorrow."
          },
          {
            "owner": "Priya",
            "commitment": "Review migration",
            "deadline": null,
            "status": "pending",
            "confidence": 0.89,
            "evidence": "I'll review the migration once it's ready."
          }
        ]
        """
    )
    sample_owners = sorted(
        set(
            str(
                item.get("owner")
                or item.get("committer_name")
                or "Unassigned"
            )
            for item in sample_commitments
        )
    )
    pending_count = sum(
        1
        for item in sample_commitments
        if commitment_status_bucket(item["status"]) == "Pending"
    )
    st.markdown(
        """
        <div class="demo-metrics">
            <div class="demo-metric demo-metric--blue">
                <strong>{}</strong><span>Total commitments</span>
            </div>
            <div class="demo-metric demo-metric--orange">
                <strong>{}</strong><span>Owners</span>
            </div>
            <div class="demo-metric demo-metric--green">
                <strong>{}</strong><span>Pending tasks</span>
            </div>
        </div>
        """.format(len(sample_commitments), len(sample_owners), pending_count),
        unsafe_allow_html=True,
    )

    st.markdown("### Commitments by owner")
    for owner in sample_owners:
        owner_items = [
            item
            for item in sample_commitments
            if str(
                item.get("owner")
                or item.get("committer_name")
                or "Unassigned"
            )
            == owner
        ]
        render_commitment_table(owner, owner_items)

# ---------- Footer ----------
st.markdown("---")
st.caption("Promise Radar • built for AI-powered conversation analysis")
