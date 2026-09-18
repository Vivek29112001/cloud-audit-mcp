from time import perf_counter

import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API_BASE_URL = "http://127.0.0.1:8000/api"

REQUEST_TIMEOUT = 180
FULL_SCAN_TIMEOUT = 1800


# ============================================================
# STREAMLIT PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="XYZ AWS Auditor",
    page_icon="🔐",
    layout="wide",
)


# ============================================================
# APPLICATION UI THEME - TEMPLATE 1
# UI ONLY: backend/API/session logic remains unchanged.
# ============================================================

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}

    .stApp {
        background: #f5f7fb;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }

    section[data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, #10253f 0%, #0c1d33 55%, #09182a 100%);
        border-right: 1px solid rgba(255,255,255,0.07);
    }

    section[data-testid="stSidebar"] * {
        color: #f7faff;
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        border: 1px solid transparent;
        background: transparent;
        color: #e8eef7;
        border-radius: 10px;
        padding: 0.7rem 0.85rem;
        font-weight: 600;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(80, 145, 255, 0.17);
        border-color: rgba(120, 169, 255, 0.22);
    }

    .overview-title {
        font-size: 2rem;
        font-weight: 800;
        color: #0d1b32;
        letter-spacing: -0.03em;
        line-height: 1.15;
        margin: 0;
    }

    .overview-subtitle {
        color: #64748b;
        margin-top: 0.35rem;
        font-size: 0.98rem;
    }

    .ready-pill {
        display: inline-block;
        padding: 0.55rem 0.9rem;
        border-radius: 10px;
        background: #dff8ee;
        color: #078b63;
        font-weight: 700;
        font-size: 0.9rem;
        border: 1px solid #c8f0e2;
    }

    .status-pill {
        display: inline-block;
        padding: 0.45rem 0.8rem;
        border-radius: 999px;
        background: #edf4ff;
        color: #2563eb;
        font-weight: 700;
        font-size: 0.84rem;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #dfe7f2;
        border-radius: 14px;
        padding: 1.1rem 1rem;
        box-shadow: 0 3px 12px rgba(25, 53, 88, 0.04);
        min-height: 132px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        text-align: center;
    }

    div[data-testid="stMetric"] label {
        justify-content: center;
        color: #51627a !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #0e1c35;
        font-weight: 800;
    }

    .stButton > button {
        border-radius: 10px;
        min-height: 42px;
        font-weight: 700;
    }

    div[data-testid="stForm"] {
        background: #ffffff;
        border: 1px solid #dfe7f2;
        border-radius: 16px;
        padding: 1.15rem;
        box-shadow: 0 4px 18px rgba(24,49,83,0.045);
    }

    .chat-heading {
        font-size: 1.15rem;
        font-weight: 800;
        color: #10213b;
        margin-bottom: 0.15rem;
    }

    .chat-subtitle {
        color: #718096;
        font-size: 0.92rem;
        margin-bottom: 0.8rem;
    }

    div[data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 0.65rem 0.85rem;
        margin-bottom: 0.65rem;
    }

    div[data-testid="stChatInput"] {
        background: #ffffff;
        border-top: 1px solid #e4eaf2;
        padding-top: 0.6rem;
    }

    hr {
        border-color: #e7edf4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# ============================================================
# API ERROR HANDLING
# ============================================================

def get_error_detail(
    response: requests.Response,
    default_message: str,
) -> str:
    """
    Safely extract a backend API error message.
    """

    try:
        payload = response.json()
    except ValueError:
        return default_message

    detail = payload.get("detail")

    return str(detail) if detail else default_message


# ============================================================
# AWS VERIFY API
# ============================================================

def verify_aws_account(
    payload: dict,
) -> dict | None:
    """
    Verify AWS credentials through:

    Streamlit
        -> FastAPI
        -> AWSMCPClient
        -> Official AWS Managed MCP Server
        -> AWS STS GetCallerIdentity
    """

    try:
        with st.spinner(
            "Verifying AWS credentials through the official AWS MCP Server..."
        ):
            response = requests.post(
                f"{API_BASE_URL}/aws/verify",
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

        if response.status_code != 200:
            st.error(
                get_error_detail(
                    response,
                    "Unable to verify AWS account.",
                )
            )
            return None

        return response.json()

    except requests.RequestException as exc:
        st.error(
            f"Backend connection failed: {exc}"
        )
        return None


# ============================================================
# LIGHTWEIGHT AWS DISCOVERY SCAN API
# ============================================================

def run_aws_scan(
    credentials: dict,
) -> dict | None:
    """
    Run the lightweight AWS discovery scan.

    The frontend does not orchestrate AWS service calls.

    Flow:

    Streamlit
        -> FastAPI /api/aws/scan
        -> AWSScanOrchestrator
        -> AWSMCPClient
        -> Official AWS Managed MCP Server
        -> aws___run_script
        -> AWS APIs
        -> Client AWS Account
    """

    try:
        with st.spinner(
            "Discovering AWS Regions, Zones and services through "
            "the official AWS Managed MCP Server..."
        ):
            response = requests.post(
                f"{API_BASE_URL}/aws/scan",
                json=credentials,
                timeout=FULL_SCAN_TIMEOUT,
            )

        if response.status_code != 200:
            st.error(
                get_error_detail(
                    response,
                    "AWS discovery scan failed.",
                )
            )
            return None

        return response.json()

    except requests.RequestException as exc:
        st.error(
            f"AWS discovery scan failed: {exc}"
        )
        return None



# ============================================================
# AWS NLP QUERY API
# ============================================================

def query_aws_account(
    credentials: dict,
    question: str,
    scan_result: dict,
) -> dict | None:
    """
    Send a natural-language AWS question to the backend.

    The backend remains the source of truth for query timing.
    We also measure the complete Streamlit -> FastAPI -> Streamlit
    round-trip so network/UI overhead is visible during development.
    """

    payload = {
        **credentials,
        "question": question,
        "scan_result": scan_result,
    }

    request_started = perf_counter()

    try:
        response = requests.post(
            f"{API_BASE_URL}/aws/query",
            json=payload,
            timeout=FULL_SCAN_TIMEOUT,
        )

        round_trip_seconds = round(
            perf_counter() - request_started,
            2,
        )

        try:
            body = response.json()
        except ValueError:
            body = {
                "status": "ERROR",
                "answer": (
                    f"HTTP {response.status_code}: {response.text}"
                ),
            }

        if not isinstance(body, dict):
            body = {
                "status": "ERROR",
                "answer": str(body),
            }

        # Frontend/network timing is supplemental.
        body["client_round_trip_seconds"] = round_trip_seconds

        if response.status_code != 200:
            detail = body.get("detail")

            return {
                **body,
                "status": str(
                    body.get("status", "ERROR")
                ).upper(),
                "answer": str(
                    detail
                    or body.get("answer")
                    or "Unable to process the AWS question."
                ),
                "raw": body,
                "client_round_trip_seconds": round_trip_seconds,
            }

        return body

    except requests.RequestException as exc:
        return {
            "status": "ERROR",
            "answer": f"AWS query failed: {exc}",
            "client_round_trip_seconds": round(
                perf_counter() - request_started,
                2,
            ),
        }


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def clear_aws_session() -> None:
    """
    Remove all AWS connection and scan information
    from the current Streamlit session.
    """

    for key in (
        "aws_connection",
        "aws_credentials",
        "aws_scan",
        "aws_chat_history",
    ):
        st.session_state.pop(
            key,
            None,
        )


def clear_scan_results() -> None:
    """
    Remove a previous scan when a new AWS account is connected.
    """

    st.session_state.pop(
        "aws_scan",
        None,
    )
    st.session_state.pop(
        "aws_chat_history",
        None,
    )


# ============================================================
# UI HELPERS
# ============================================================

def render_scan_warnings(
    warnings: list,
) -> None:
    """
    Render scan warnings without hiding partial coverage.
    """

    if not warnings:
        return

    st.divider()

    st.subheader(
        "Scan Warnings"
    )

    st.warning(
        "The AWS scan completed with one or more warnings. "
        "Review these warnings before treating the inventory "
        "as complete."
    )

    for warning in warnings:
        st.write(
            f"• {warning}"
        )


def render_region_results(
    region_data: dict | None,
) -> None:
    """
    Render dynamic AWS Region discovery results.
    """

    if not region_data:
        return

    st.divider()

    st.subheader(
        "Region Summary"
    )

    region_col1, region_col2, region_col3 = (
        st.columns(3)
    )

    with region_col1:
        st.metric(
            "Total Regions",
            region_data.get(
                "total_regions",
                0,
            ),
        )

    with region_col2:
        st.metric(
            "Enabled Regions",
            region_data.get(
                "enabled_regions",
                0,
            ),
        )

    with region_col3:
        st.metric(
            "Disabled Regions",
            region_data.get(
                "disabled_regions",
                0,
            ),
        )

    regions = region_data.get(
        "regions",
        [],
    )

    enabled_region_rows = [
        region
        for region in regions
        if (
            region.get("enabled") is True
            and region.get("region_name")
        )
    ]

    disabled_region_rows = [
        region
        for region in regions
        if region.get("enabled") is not True
    ]

    st.subheader(
        "Enabled AWS Regions"
    )

    if enabled_region_rows:
        st.dataframe(
            enabled_region_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No enabled AWS Regions were returned."
        )

    with st.expander(
        "Disabled / Not Opted-In Regions "
        f"({len(disabled_region_rows)})"
    ):
        if disabled_region_rows:
            st.dataframe(
                disabled_region_rows,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No disabled AWS Regions were returned."
            )


def render_zone_results(
    zone_data: dict | None,
) -> None:
    """
    Render Availability Zone discovery results.
    """

    if not zone_data:
        return

    st.divider()

    st.subheader(
        "Availability Zones"
    )

    st.metric(
        "Total Availability Zones",
        zone_data.get(
            "total_zones",
            0,
        ),
    )

    zones = zone_data.get(
        "zones",
        [],
    )

    if zones:
        st.dataframe(
            zones,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No Availability Zones were returned."
        )


def render_resource_inventory(
    resource_data: dict | None,
) -> None:
    """
    Render broad resource inventory results.
    """

    if not resource_data:
        return

    st.divider()

    st.subheader(
        "Infrastructure Inventory"
    )

    used_regions = resource_data.get(
        "used_regions",
        [],
    )

    detected_services = resource_data.get(
        "detected_services",
        [],
    )

    inventory_col1, inventory_col2, inventory_col3 = (
        st.columns(3)
    )

    with inventory_col1:
        st.metric(
            "Resources",
            resource_data.get(
                "total_resources",
                0,
            ),
        )

    with inventory_col2:
        st.metric(
            "Used Regions",
            len(used_regions),
        )

    with inventory_col3:
        st.metric(
            "Detected Services",
            len(detected_services),
        )

    # --------------------------------------------------------
    # USED REGIONS
    # --------------------------------------------------------

    st.subheader(
        "Regions Containing Resources"
    )

    if used_regions:
        used_region_rows = [
            {
                "region": region
            }
            for region in used_regions
        ]

        st.dataframe(
            used_region_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No Regions containing resources were detected."
        )

    # --------------------------------------------------------
    # DETECTED SERVICES
    # --------------------------------------------------------

    st.subheader(
        "Detected AWS Services"
    )

    if detected_services:
        st.dataframe(
            detected_services,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No AWS services with discoverable resources "
            "were detected."
        )

    # --------------------------------------------------------
    # RESOURCE LIST
    # --------------------------------------------------------

    resources = resource_data.get(
        "resources",
        [],
    )

    st.subheader(
        "Discovered AWS Resources"
    )

    if resources:
        resource_table = []

        for resource in resources:
            resource_table.append(
                {
                    "resource_id": (
                        resource.get(
                            "resource_id"
                        )
                    ),
                    "service": (
                        resource.get(
                            "service"
                        )
                    ),
                    "resource_type": (
                        resource.get(
                            "resource_type"
                        )
                    ),
                    "region": (
                        resource.get(
                            "region"
                        )
                    ),
                    "account_id": (
                        resource.get(
                            "owning_account_id"
                        )
                    ),
                    "arn": (
                        resource.get(
                            "arn"
                        )
                    ),
                }
            )

        st.dataframe(
            resource_table,
            use_container_width=True,
            hide_index=True,
        )

        with st.expander(
            "View Complete Resource Data"
        ):
            st.json(
                resources
            )

    else:
        st.info(
            "No AWS resources were returned."
        )


# Deep service scan renderers removed. Detailed configuration is queried
# on demand through the NLP -> generic read-only AWS MCP query flow.


def render_scan_status(
    aws_connection: dict | None,
    scan_data: dict | None,
    region_data: dict | None,
    zone_data: dict | None,
    resource_data: dict | None,
) -> None:
    """
    Render the current scan pipeline status.
    """

    if not aws_connection:
        return

    st.divider()

    st.subheader(
        "Scan Status"
    )

    status_data = [
        {
            "stage": "AWS Account Verification",
            "status": (
                "Completed"
                if aws_connection
                else "Pending"
            ),
        },
        {
            "stage": "AWS MCP Infrastructure Scan",
            "status": (
                scan_data.get(
                    "status",
                    "Pending",
                )
                if scan_data
                else "Pending"
            ),
        },
        {
            "stage": "Region Discovery",
            "status": (
                "Completed"
                if region_data
                else "Pending"
            ),
        },
        {
            "stage": "Availability Zone Discovery",
            "status": (
                "Completed"
                if zone_data
                else "Pending"
            ),
        },
        {
            "stage": "Resource Discovery",
            "status": (
                "Completed"
                if resource_data
                else "Pending"
            ),
        },
        {
            "stage": "Service Detection",
            "status": (
                "Completed"
                if resource_data
                else "Pending"
            ),
        },
    ]

    st.dataframe(
        status_data,
        use_container_width=True,
        hide_index=True,
    )



# ============================================================
# TEMPLATE 1 APPLICATION UI HELPERS
# ============================================================

def render_app_sidebar(
    aws_connection: dict | None,
    scan_data: dict | None,
) -> None:
    with st.sidebar:
        st.markdown(
            """
            <div style="padding:0.45rem 0 1.1rem 0;">
                <div style="font-size:1.35rem;font-weight:800;">☁️ AWS AI Auditor</div>
                <div style="font-size:0.78rem;color:#9fb1c8;margin-top:0.2rem;">
                    Cloud discovery & live AI queries
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.button("⌂  Home", use_container_width=True, key="nav_home")
        st.button("⎋  Connect", use_container_width=True, key="nav_connect")
        st.button("⌕  Discovery", use_container_width=True, key="nav_discovery")
        st.button("◌  Chat", use_container_width=True, key="nav_chat")
        st.button("⚙  Settings", use_container_width=True, key="nav_settings")

        st.markdown("<div style='height:22rem'></div>", unsafe_allow_html=True)

        if aws_connection:
            st.markdown(
                f"""
                <div style="
                    border-top:1px solid rgba(255,255,255,.12);
                    padding-top:1rem;
                    font-size:.82rem;
                    color:#c9d5e5;
                ">
                    <div style="font-weight:700;color:#fff;">Connected AWS Account</div>
                    <div style="margin-top:.3rem;">{aws_connection.get("account_id", "-")}</div>
                    <div style="margin-top:.2rem;color:#79e2b8;">
                        ● {aws_connection.get("connection_status", "VERIFIED")}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if scan_data:
            st.markdown(
                f"""
                <div style="margin-top:.7rem;font-size:.78rem;color:#aebed3;">
                    Discovery: {scan_data.get("status", "UNKNOWN")}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_template1_overview(
    aws_connection: dict,
    scan_data: dict,
) -> None:
    summary = scan_data.get("summary", {}) or {}
    account = scan_data.get("account", {}) or {}

    account_id = (
        account.get("account_id")
        or aws_connection.get("account_id")
        or "-"
    )

    status = scan_data.get("status", "UNKNOWN")
    ready = status == "COMPLETED"

    top_left, top_right = st.columns([5, 1.35])

    with top_left:
        st.markdown(
            f"""
            <div class="overview-title">AWS Infrastructure Overview</div>
            <div class="overview-subtitle">
                Connected account: {account_id}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top_right:
        if ready:
            st.markdown(
                '<div class="ready-pill">✓ Ready for AI Assistant</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="status-pill">{status}</div>',
                unsafe_allow_html=True,
            )

    st.write("")

    metric_cols = st.columns(4)

    with metric_cols[0]:
        st.metric(
            "🌐 Regions",
            summary.get("enabled_regions", 0),
        )

    with metric_cols[1]:
        st.metric(
            "▱ Availability Zones",
            summary.get("availability_zones", 0),
        )

    with metric_cols[2]:
        st.metric(
            "◇ Services",
            summary.get("detected_services", 0),
        )

    with metric_cols[3]:
        st.metric(
            "▤ Resources",
            summary.get("discovered_resources", 0),
        )


def _query_status_label(result: dict | None) -> str:
    """Return a compact backend query status for the evidence panel."""
    if not result:
        return "NO_RESPONSE"

    return str(
        result.get("status", "UNKNOWN")
    ).upper()


def _format_seconds(
    value: object,
) -> str | None:
    """Safely format an arbitrary timing value as seconds."""
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None

    if seconds < 0:
        return None

    return f"{seconds:.2f}"


def _render_query_timing(
    result: dict | None,
) -> None:
    """
    Show the user the backend response time and expose the detailed
    timing breakdown only in an expandable developer view.
    """
    if not result:
        return

    backend_seconds = _format_seconds(
        result.get("response_time_seconds")
    )

    round_trip_seconds = _format_seconds(
        result.get("client_round_trip_seconds")
    )

    if backend_seconds is not None:
        st.caption(
            f"⏱ Answered in {backend_seconds} seconds"
        )
    elif round_trip_seconds is not None:
        # Fallback for older backend responses that do not yet return timing.
        st.caption(
            f"⏱ Response received in {round_trip_seconds} seconds"
        )

    timings = result.get("timings") or {}

    if not timings and round_trip_seconds is None:
        return

    with st.expander(
        "Performance details",
        expanded=False,
    ):
        if timings:
            timing_rows = []

            labels = {
                "intent_ms": "Groq query planning",
                "aws_mcp_ms": "AWS MCP execution",
                "answer_ms": "Groq answer formatting",
                "total_ms": "Backend total",
            }

            for key, label in labels.items():
                value = timings.get(key)
                if value is None:
                    continue

                try:
                    seconds = float(value) / 1000
                except (TypeError, ValueError):
                    continue

                timing_rows.append(
                    {
                        "Stage": label,
                        "Seconds": round(seconds, 2),
                    }
                )

            if timing_rows:
                st.dataframe(
                    timing_rows,
                    use_container_width=True,
                    hide_index=True,
                )

        if round_trip_seconds is not None:
            st.caption(
                "Complete Streamlit → FastAPI → Streamlit round trip: "
                f"{round_trip_seconds} seconds"
            )


def _render_query_evidence(result: dict) -> None:
    """
    Render backend evidence without reinterpreting AWS facts in Streamlit.

    The backend remains responsible for:
      Groq planning -> read-only validation -> AWS MCP execution ->
      multi-Region aggregation -> Groq answer generation.
    """
    status = _query_status_label(result)

    st.caption(f"Query status: {status}")

    intent = result.get("intent")
    if intent:
        st.markdown("**Resolved Query Plan**")
        st.json(intent)

    evidence = result.get("data")
    if evidence is not None:
        st.markdown("**AWS Evidence**")
        st.json(evidence)
    else:
        st.info(
            "No AWS evidence payload was returned for this query."
        )

    warnings = result.get("warnings") or []
    if warnings:
        st.markdown("**Query Warnings**")
        for warning in warnings:
            if isinstance(warning, dict):
                region = warning.get("region")
                error = warning.get("error") or warning
                prefix = f"{region}: " if region else ""
                st.warning(f"{prefix}{error}")
            else:
                st.warning(str(warning))

    raw_error = result.get("raw")
    if raw_error is not None:
        st.markdown("**Backend Error Payload**")
        st.json(raw_error)


def _extract_query_answer(
    result: dict | None,
) -> str:
    """Return the backend-generated natural-language answer."""
    if not result:
        return "No response was returned."

    status = str(
        result.get(
            "status",
            "",
        )
    ).upper()

    answer = result.get("answer")

    if status != "SUCCESS":
        return str(
            answer
            or result.get("detail")
            or "Unable to process the AWS question."
        )

    return str(
        answer
        or "The live AWS query completed successfully."
    )


def _render_chat_message(
    message: dict,
) -> None:
    """Render a persisted chat message including timing/evidence metadata."""
    role = message.get("role", "assistant")
    content = str(message.get("content", ""))

    with st.chat_message(role):
        st.markdown(content)

        if role != "assistant":
            return

        result = message.get("result")
        if not isinstance(result, dict):
            return

        _render_query_timing(result)

        with st.expander(
            "View AWS evidence",
            expanded=False,
        ):
            _render_query_evidence(result)


def render_aws_ai_chat(
    aws_connection: dict,
    scan_data: dict,
) -> None:

    if scan_data.get("status") != "COMPLETED":
        return

    credentials = st.session_state.get(
        "aws_credentials"
    )

    if not credentials:
        st.warning(
            "AWS credentials are no longer available in this session. "
            "Please verify the account again."
        )
        return

    if "aws_chat_history" not in st.session_state:
        st.session_state["aws_chat_history"] = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I'm your AWS AI Assistant. "
                    "Ask me about the AWS infrastructure discovered for this account."
                ),
            }
        ]

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    header_col, clear_col = st.columns(
        [6, 1]
    )

    with header_col:
        st.markdown(
            """
            <div class="chat-heading">🤖 AWS AI Assistant</div>
            <div class="chat-subtitle">
                Ask questions about your AWS infrastructure. Live read-only details are fetched through AWS MCP only when needed.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with clear_col:
        if st.button(
            "Clear Chat",
            use_container_width=True,
            key="clear_aws_chat",
        ):
            st.session_state["aws_chat_history"] = [
                {
                    "role": "assistant",
                    "content": (
                        "Hello! I'm your AWS AI Assistant. "
                        "What would you like to know about this AWS account?"
                    ),
                }
            ]
            st.rerun()

    # Re-render complete persisted chat, including response times and evidence.
    for message in st.session_state["aws_chat_history"]:
        _render_chat_message(message)

    question = st.chat_input(
        "Ask anything about your AWS account..."
    )

    if not question:
        return

    question = question.strip()
    if not question:
        return

    user_message = {
        "role": "user",
        "content": question,
    }

    st.session_state["aws_chat_history"].append(
        user_message
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(
            "Querying the live AWS account through the official AWS MCP Server..."
        ):
            query_result = query_aws_account(
                credentials=credentials,
                question=question,
                scan_result=scan_data,
            )

        answer = _extract_query_answer(
            query_result
        )

        status = _query_status_label(
            query_result
        )

        if status == "SUCCESS":
            st.markdown(answer)
        else:
            st.warning(answer)

        if isinstance(query_result, dict):
            _render_query_timing(
                query_result
            )

            with st.expander(
                "View AWS evidence",
                expanded=False,
            ):
                _render_query_evidence(
                    query_result
                )

    assistant_message = {
        "role": "assistant",
        "content": answer,
    }

    # Persist the complete structured response so timing/evidence does not
    # disappear when Streamlit reruns on the next user interaction.
    if isinstance(query_result, dict):
        assistant_message["result"] = (
            query_result
        )

    st.session_state["aws_chat_history"].append(
        assistant_message
    )


# ============================================================
# HEADER / APPLICATION SHELL
# ============================================================

aws_connection = st.session_state.get(
    "aws_connection"
)

scan_data = st.session_state.get(
    "aws_scan"
)

render_app_sidebar(
    aws_connection=aws_connection,
    scan_data=scan_data,
)

# ============================================================
# CONNECT / VERIFY
# ============================================================

if not aws_connection:

    st.markdown(
        """
        <div class="overview-title">Connect AWS Account</div>
        <div class="overview-subtitle">
            Verify the client AWS account through the official AWS Managed MCP Server.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    with st.form(
        "aws_connection_form"
    ):
        st.subheader(
            "AWS Credentials"
        )

        access_key_id = st.text_input(
            "AWS Access Key ID",
            placeholder="AKIA...",
        )

        secret_access_key = st.text_input(
            "AWS Secret Access Key",
            type="password",
        )

        session_token = st.text_input(
            "AWS Session Token (optional)",
            type="password",
        )

        connect = st.form_submit_button(
            "Verify AWS Account",
            type="primary",
            use_container_width=True,
        )

    if connect:
        if (
            not access_key_id
            or not secret_access_key
        ):
            st.error(
                "Access Key ID and Secret Access Key are required."
            )

        else:
            credentials_payload = {
                "access_key_id": access_key_id.strip(),
                "secret_access_key": secret_access_key,
                "session_token": (
                    session_token.strip()
                    if session_token.strip()
                    else None
                ),
            }

            verification_data = verify_aws_account(
                credentials_payload
            )

            if verification_data:
                clear_scan_results()

                st.session_state[
                    "aws_connection"
                ] = verification_data

                st.session_state[
                    "aws_credentials"
                ] = credentials_payload

                st.success(
                    "AWS account verified successfully."
                )

                st.rerun()

    st.info(
        "The UI does not call AWS APIs, boto3, or AWS CLI directly. "
        "AWS verification remains handled by the existing backend and "
        "the official AWS Managed MCP Server."
    )

# ============================================================
# VERIFIED ACCOUNT / DISCOVERY
# ============================================================

else:
    title_col, disconnect_col = st.columns(
        [5.5, 1]
    )

    with title_col:
        st.markdown(
            """
            <div class="overview-title">AWS AI Auditor</div>
            <div class="overview-subtitle">
                Discover the account first, then ask targeted infrastructure questions.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with disconnect_col:
        disconnect_clicked = st.button(
            "Disconnect",
            use_container_width=True,
            key="disconnect_account",
        )

    if disconnect_clicked:
        clear_aws_session()
        st.rerun()

    st.write("")

    if not scan_data:

        account_col1, account_col2, account_col3 = st.columns(3)

        with account_col1:
            st.metric(
                "Cloud Provider",
                aws_connection.get(
                    "provider",
                    "AWS",
                ),
            )

        with account_col2:
            st.metric(
                "AWS Account",
                aws_connection.get(
                    "account_id",
                    "-",
                ),
            )

        with account_col3:
            st.metric(
                "Status",
                aws_connection.get(
                    "connection_status",
                    "VERIFIED",
                ),
            )

        st.caption(
            "Caller Identity"
        )

        st.code(
            aws_connection.get(
                "arn",
                "ARN not returned",
            ),
            language=None,
        )

        run_scan_clicked = st.button(
            "Start AWS Discovery Scan",
            type="primary",
            use_container_width=True,
            key="start_aws_discovery_scan",
        )

        if run_scan_clicked:
            credentials = st.session_state.get(
                "aws_credentials"
            )

            if not credentials:
                st.error(
                    "AWS credentials are no longer available in this session. "
                    "Please verify the account again."
                )

            else:
                new_scan_data = run_aws_scan(
                    credentials
                )

                if new_scan_data:
                    st.session_state[
                        "aws_scan"
                    ] = new_scan_data

                    if (
                        new_scan_data.get(
                            "status"
                        )
                        == "COMPLETED"
                    ):
                        st.success(
                            "AWS discovery completed successfully."
                        )
                    else:
                        st.error(
                            "AWS discovery did not complete successfully."
                        )

                    st.rerun()

        st.info(
            "The discovery scan only establishes the account context, "
            "Regions, Availability Zones, detected services and lightweight "
            "resource metadata. Detailed configuration is queried later from chat."
        )

    else:
        render_template1_overview(
            aws_connection=aws_connection,
            scan_data=scan_data,
        )

        warnings = (
            scan_data.get(
                "warnings",
                [],
            )
            or []
        )

        if warnings:
            with st.expander(
                f"Discovery warnings ({len(warnings)})"
            ):
                for warning in warnings:
                    st.warning(
                        warning
                    )

        if (
            scan_data.get("status")
            == "COMPLETED"
        ):
            render_aws_ai_chat(
                aws_connection=aws_connection,
                scan_data=scan_data,
            )

        else:
            st.error(
                "The AWS discovery did not complete successfully. "
                "Reconnect or run the scan again after resolving the reported issue."
            )
