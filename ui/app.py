from time import perf_counter
from html import escape

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

    /* ========================================================
       CLEAN CHATGPT-STYLE SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        min-width: 300px !important;
        max-width: 300px !important;
        background: #0c1d33 !important;
        border-right: 1px solid rgba(255,255,255,0.07);
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.6rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    section[data-testid="stSidebar"] * {
        box-sizing: border-box;
    }

    section[data-testid="stSidebar"] .stMarkdown {
        margin: 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
        margin: 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"] pre,
    section[data-testid="stSidebar"] code {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    section[data-testid="stSidebar"] .stButton {
        margin: 0.08rem 0 !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        min-height: 38px;
        padding: 0.45rem 0.68rem;
        justify-content: flex-start;
        text-align: left;
        border-radius: 9px;
        border: 1px solid transparent;
        background: transparent;
        box-shadow: none;
        font-size: 0.83rem;
        font-weight: 600;
        color: #dbe7f5 !important;
        transition:
            background 0.14s ease,
            border-color 0.14s ease;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.075);
        border-color: rgba(255,255,255,0.06);
        transform: none;
    }

    section[data-testid="stSidebar"] button[kind="primary"] {
        background: rgba(88,135,255,0.16) !important;
        border-color: rgba(110,151,255,0.20) !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] button:disabled {
        opacity: 0.42;
    }

    .cc-sidebar-brand {
        padding: 0.35rem 0.15rem 0.55rem 0.15rem;
    }

    .cc-sidebar-brand-row {
        display: flex;
        align-items: center;
        gap: 0.65rem;
    }

    .cc-sidebar-logo {
        width: 34px;
        height: 34px;
        flex: 0 0 34px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        background: rgba(255,255,255,0.09);
        color: #ffffff;
        font-size: 1rem;
    }

    .cc-sidebar-title {
        color: #ffffff;
        font-size: 1rem;
        line-height: 1.2;
        font-weight: 800;
        letter-spacing: -0.01em;
    }

    .cc-sidebar-subtitle {
        margin-top: 0.13rem;
        color: #879ab2;
        font-size: 0.69rem;
        line-height: 1.2;
    }

    .cc-sidebar-user {
        display: flex;
        align-items: center;
        gap: 0.58rem;
        margin: 0.25rem 0 0.75rem 0;
        padding: 0.58rem 0.62rem;
        border-radius: 10px;
        background: rgba(255,255,255,0.045);
        border: 1px solid rgba(255,255,255,0.055);
    }

    .cc-user-avatar {
        width: 30px;
        height: 30px;
        flex: 0 0 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        background: #203b5b;
        color: #ffffff;
        font-size: 0.77rem;
        font-weight: 800;
    }

    .cc-user-copy {
        min-width: 0;
        flex: 1;
    }

    .cc-user-name {
        overflow: hidden;
        color: #f8fbff;
        font-size: 0.78rem;
        font-weight: 700;
        line-height: 1.15;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .cc-user-email {
        overflow: hidden;
        margin-top: 0.13rem;
        color: #8093aa;
        font-size: 0.65rem;
        line-height: 1.15;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .cc-sidebar-label {
        margin: 0.3rem 0.18rem 0.28rem 0.18rem;
        color: #6f829a;
        font-size: 0.64rem;
        font-weight: 800;
        letter-spacing: 0.075em;
        text-transform: uppercase;
    }

    .cc-chat-label {
        margin-top: 0.65rem;
    }

    .cc-sidebar-divider {
        height: 1px;
        margin: 0.75rem 0 0.65rem 0;
        background: rgba(255,255,255,0.065);
    }

    .cc-empty-chats {
        padding: 0.45rem 0.5rem 0.6rem 0.5rem;
        color: #8a9cb1;
        font-size: 0.72rem;
        line-height: 1.35;
    }

    .cc-empty-chats span {
        color: #64778f;
        font-size: 0.66rem;
    }

    .cc-footer-divider {
        margin-top: 0.8rem;
    }

    .cc-account-card {
        margin: 0.25rem 0 0.5rem 0;
        padding: 0.62rem 0.66rem;
        border-radius: 10px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.055);
    }

    .cc-account-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: #6f829a;
        font-size: 0.61rem;
        font-weight: 800;
        letter-spacing: 0.065em;
    }

    .cc-account-dot {
        color: #54d6a1;
        font-size: 0.62rem;
    }

    .cc-account-dot-off {
        color: #e8b64c;
    }

    .cc-account-id {
        overflow: hidden;
        margin-top: 0.28rem;
        color: #edf5ff;
        font-size: 0.75rem;
        font-weight: 700;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .cc-account-meta {
        overflow: hidden;
        margin-top: 0.17rem;
        color: #788ba2;
        font-size: 0.64rem;
        text-overflow: ellipsis;
        white-space: nowrap;
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
# PHASE 2 AUTHENTICATION
# ============================================================

def get_auth_headers() -> dict[str, str]:
    """
    Return the current Bearer token header for authenticated backend calls.
    """
    token = st.session_state.get("access_token")
    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}",
    }


def register_user(
    username: str,
    email: str,
    password: str,
) -> tuple[bool, str]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
            },
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code not in (200, 201):
            return False, get_error_detail(
                response,
                "Unable to register user.",
            )

        return True, "Registration successful. You can now sign in."

    except requests.RequestException as exc:
        return False, f"Backend connection failed: {exc}"


def login_user(
    username: str,
    password: str,
) -> tuple[bool, str]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "username": username,
                "password": password,
            },
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return False, get_error_detail(
                response,
                "Unable to sign in.",
            )

        payload = response.json()

        st.session_state["access_token"] = payload["access_token"]
        st.session_state["current_user"] = payload["user"]

        return True, "Signed in successfully."

    except requests.RequestException as exc:
        return False, f"Backend connection failed: {exc}"


def logout_user() -> None:
    """
    Clear application authentication and transient AWS credentials.
    """
    disconnect_aws_backend_session()
    clear_aws_session()

    for key in (
        "access_token",
        "current_user",
    ):
        st.session_state.pop(
            key,
            None,
        )


def render_auth_screen() -> None:
    """
    Phase 2 login/register gate.
    """
    st.markdown(
        """
        <div class="overview-title">AWS AI Auditor</div>
        <div class="overview-subtitle">
            Sign in to access cloud discovery and persisted audit history.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    login_tab, register_tab = st.tabs(
        ["Sign In", "Create Account"]
    )

    with login_tab:
        with st.form("phase2_login_form"):
            login_name = st.text_input(
                "Username or Email",
                key="phase2_login_name",
            )

            login_password = st.text_input(
                "Password",
                type="password",
                key="phase2_login_password",
            )

            login_clicked = st.form_submit_button(
                "Sign In",
                type="primary",
                use_container_width=True,
            )

        if login_clicked:
            if not login_name.strip() or not login_password:
                st.error("Username/email and password are required.")
            else:
                ok, message = login_user(
                    login_name.strip(),
                    login_password,
                )

                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    with register_tab:
        with st.form("phase2_register_form"):
            register_username = st.text_input(
                "Username",
                key="phase2_register_username",
            )

            register_email = st.text_input(
                "Email",
                key="phase2_register_email",
            )

            register_password = st.text_input(
                "Password",
                type="password",
                key="phase2_register_password",
            )

            register_confirm = st.text_input(
                "Confirm Password",
                type="password",
                key="phase2_register_confirm",
            )

            register_clicked = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )

        if register_clicked:
            if not register_username.strip():
                st.error("Username is required.")
            elif not register_email.strip():
                st.error("Email is required.")
            elif len(register_password) < 8:
                st.error("Password must contain at least 8 characters.")
            elif register_password != register_confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = register_user(
                    register_username.strip(),
                    register_email.strip(),
                    register_password,
                )

                if ok:
                    st.success(message)
                else:
                    st.error(message)


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
                headers=get_auth_headers(),
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
        -> FastAPI /api/aws/scans
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
                headers=get_auth_headers(),
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
    scan_id: str,
    question: str,
) -> dict | None:
    """
    Send a natural-language AWS question using only the persisted scan_id.

    AWS credentials are no longer sent from Streamlit for each query.
    The backend loads:
      - scan context from SQLite using scan_id
      - transient AWS credentials from the authenticated user's server session

    The backend remains the source of truth for query timing.
    The UI also measures the complete Streamlit -> FastAPI -> Streamlit
    round trip for development visibility.
    """

    payload = {
        "scan_id": scan_id,
        "question": question,
    }

    request_started = perf_counter()

    try:
        response = requests.post(
            f"{API_BASE_URL}/aws/query",
            json=payload,
            headers=get_auth_headers(),
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
# PHASE 2 PERSISTED SCAN HISTORY
# ============================================================

def get_scan_history() -> list[dict]:
    try:
        response = requests.get(
            f"{API_BASE_URL}/aws/scans",
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return []

        payload = response.json()
        return payload if isinstance(payload, list) else []

    except requests.RequestException:
        return []


def get_persisted_scan(
    scan_id: str,
) -> dict | None:
    try:
        response = requests.get(
            f"{API_BASE_URL}/aws/scans/{scan_id}",
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return None

        payload = response.json()

        return payload if isinstance(payload, dict) else None

    except requests.RequestException:
        return None


def get_active_scan(
    account_id: str | None = None,
) -> dict | None:
    """Restore the persisted active snapshot without triggering AWS discovery."""
    try:
        params = {"account_id": account_id} if account_id else None
        response = requests.get(
            f"{API_BASE_URL}/aws/scans/active",
            params=params,
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            return None
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except requests.RequestException:
        return None


def activate_scan(scan_id: str) -> dict | None:
    """Manually select one immutable historical snapshot as active."""
    try:
        response = requests.put(
            f"{API_BASE_URL}/aws/scans/{scan_id}/activate",
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            st.error(get_error_detail(response, "Unable to activate saved scan."))
            return None
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except requests.RequestException as exc:
        st.error(f"Unable to activate saved scan: {exc}")
        return None


def refresh_aws_scan() -> dict | None:
    """Explicitly create a fresh immutable discovery snapshot."""
    try:
        with st.spinner(
            "Refreshing AWS discovery and creating a new saved snapshot..."
        ):
            response = requests.post(
                f"{API_BASE_URL}/aws/scan/refresh",
                headers=get_auth_headers(),
                timeout=FULL_SCAN_TIMEOUT,
            )
        if response.status_code != 200:
            st.error(get_error_detail(response, "Unable to refresh AWS discovery."))
            return None
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except requests.RequestException as exc:
        st.error(f"AWS discovery refresh failed: {exc}")
        return None


# ============================================================
# PHASE 2 PERSISTED CHAT API
# ============================================================

def create_chat(
    scan_id: str,
    title: str = "New AWS Chat",
    context: dict | None = None,
) -> dict | None:
    """Create a persisted chat linked to one immutable discovery snapshot."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chats",
            json={
                "scan_id": scan_id,
                "title": title,
                "context": context or {},
            },
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code not in (200, 201):
            st.error(
                get_error_detail(
                    response,
                    "Unable to create chat.",
                )
            )
            return None

        payload = response.json()
        return payload if isinstance(payload, dict) else None

    except requests.RequestException as exc:
        st.error(f"Unable to create chat: {exc}")
        return None


def get_chat_history() -> list[dict]:
    """Return the authenticated user's persisted chat sessions."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/chats",
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return []

        payload = response.json()
        return payload if isinstance(payload, list) else []

    except requests.RequestException:
        return []


def get_chat(
    chat_id: int,
) -> dict | None:
    """Load one chat and its persisted message history."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/chats/{chat_id}",
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            st.error(
                get_error_detail(
                    response,
                    "Unable to load chat.",
                )
            )
            return None

        payload = response.json()
        return payload if isinstance(payload, dict) else None

    except requests.RequestException as exc:
        st.error(f"Unable to load chat: {exc}")
        return None


def query_chat(
    chat_id: int,
    question: str,
) -> dict | None:
    """Ask from the saved scan; backend escalates to live AWS only when needed."""
    request_started = perf_counter()

    try:
        response = requests.post(
            f"{API_BASE_URL}/chats/{chat_id}/query",
            json={"question": question},
            headers=get_auth_headers(),
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
                "answer": f"HTTP {response.status_code}: {response.text}",
            }

        if not isinstance(body, dict):
            body = {
                "status": "ERROR",
                "answer": str(body),
            }

        body["client_round_trip_seconds"] = round_trip_seconds

        if response.status_code != 200:
            detail = body.get("detail")
            return {
                **body,
                "status": str(body.get("status", "ERROR")).upper(),
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
            "answer": f"AWS chat query failed: {exc}",
            "client_round_trip_seconds": round(
                perf_counter() - request_started,
                2,
            ),
        }


def _open_chat_session(
    chat_id: int,
) -> None:
    """Select a persisted chat and restore its linked scan when necessary."""
    chat = get_chat(chat_id)
    if not chat:
        return

    scan_id = chat.get("scan_id")
    current_scan = st.session_state.get("aws_scan") or {}

    if scan_id and current_scan.get("scan_id") != scan_id:
        restored = get_persisted_scan(str(scan_id))
        if restored:
            st.session_state["aws_scan"] = restored
            st.session_state["aws_connection"] = restored.get("account", {})

    st.session_state["active_chat_id"] = chat_id
    st.session_state["active_page"] = "chat"
    st.session_state["active_chat"] = chat


def _open_context_chat(
    *,
    context: dict,
    title: str,
) -> None:
    """Create a chat anchored to the current scan and structured UI selection."""
    scan_data = st.session_state.get("aws_scan") or {}
    scan_id = scan_data.get("scan_id")
    if not scan_id:
        st.error("A completed saved discovery scan is required before opening chat.")
        return

    structured_context = {
        **context,
        "scan_id": str(scan_id),
    }
    created = create_chat(
        scan_id=str(scan_id),
        title=title[:200],
        context=structured_context,
    )
    if not created:
        return

    st.session_state["active_chat_id"] = created.get("id")
    st.session_state["active_chat"] = created
    st.session_state["active_page"] = "chat"
    st.rerun()


def _service_context_from_classification(item: dict) -> dict:
    billing_services = item.get("billing_services") or []
    regions = item.get("regions") or []
    display_name = (
        (billing_services[0] if billing_services else None)
        or item.get("discovered_service")
        or item.get("key")
        or "AWS Service"
    )
    return {
        "context_type": "SERVICE",
        "label": str(display_name),
        "service": item.get("discovered_service"),
        "service_key": item.get("key"),
        "billing_service": billing_services[0] if billing_services else None,
        "category": item.get("category"),
        "financial_status": item.get("financial_status"),
        "billing_amount": item.get("billing_amount"),
        "currency": item.get("currency"),
        "regions": regions,
    }


def _render_discovered_service_chat_buttons(
    items: list[dict] | None,
) -> None:
    clean = [item for item in (items or []) if isinstance(item, dict) and item.get("service")]
    if not clean:
        return
    st.caption("Select a discovered service to open contextual chat.")
    columns = st.columns(3)
    for index, item in enumerate(clean):
        namespace = str(item.get("service"))
        with columns[index % len(columns)]:
            if st.button(
                f"💬 {namespace}",
                key=f"discovered_service_chat_{index}_{namespace}",
                use_container_width=True,
            ):
                _open_context_chat(
                    context={
                        "context_type": "SERVICE",
                        "label": namespace,
                        "service": namespace,
                        "resource_count": item.get("resource_count"),
                        "regions": item.get("regions") or [],
                        "category": "DISCOVERED_RESOURCE_BACKED",
                    },
                    title=f"{namespace} · Saved Scan",
                )


def _render_service_chat_buttons(
    items: list[dict] | None,
    *,
    key_prefix: str,
) -> None:
    clean_items = [item for item in (items or []) if isinstance(item, dict)]
    if not clean_items:
        return

    st.caption("Select a service to open a chat anchored to this saved scan.")
    columns = st.columns(3)
    for index, item in enumerate(clean_items):
        context = _service_context_from_classification(item)
        label = str(context.get("label") or "AWS Service")
        with columns[index % len(columns)]:
            if st.button(
                f"💬 {label}",
                key=f"{key_prefix}_{index}_{item.get('key') or label}",
                use_container_width=True,
            ):
                _open_context_chat(
                    context=context,
                    title=f"{label} · Saved Scan",
                )


def _render_region_chat_buttons(
    items: list[dict] | None,
    *,
    key_prefix: str,
) -> None:
    clean_items = [item for item in (items or []) if isinstance(item, dict) and item.get("region")]
    if not clean_items:
        return
    columns = st.columns(4)
    for index, item in enumerate(clean_items):
        region = str(item.get("region"))
        with columns[index % len(columns)]:
            if st.button(
                f"💬 {region}",
                key=f"{key_prefix}_{index}_{region}",
                use_container_width=True,
            ):
                _open_context_chat(
                    context={
                        "context_type": "REGION",
                        "label": region,
                        "region": region,
                        "category": item.get("category"),
                        "billing_amount": item.get("billing_amount"),
                        "resource_count": item.get("resource_count"),
                    },
                    title=f"{region} · Saved Scan",
                )


def _render_billing_service_chat_selector(
    service_costs: list[dict] | None,
) -> None:
    clean = [item for item in (service_costs or []) if isinstance(item, dict) and item.get("billing_service")]
    if not clean:
        return
    options = [""] + [str(item.get("billing_service")) for item in clean]
    selector_version = int(st.session_state.get("billing_service_selector_version", 0))
    selected = st.selectbox(
        "Open billing service in Chat",
        options=options,
        index=0,
        key=f"billing_service_context_selector_{selector_version}",
        placeholder="Choose a Cost Explorer service group...",
    )
    if not selected:
        return
    item = next((row for row in clean if str(row.get("billing_service")) == selected), None)
    if not item:
        return
    st.session_state["billing_service_selector_version"] = selector_version + 1
    _open_context_chat(
        context={
            "context_type": "BILLING_SERVICE",
            "label": selected,
            "billing_service": selected,
            "billing_amount": item.get("amount"),
            "currency": item.get("unit"),
        },
        title=f"{selected} · Billing Snapshot",
    )


def _render_zone_chat_selector(zones: list[dict] | None) -> None:
    clean = [item for item in (zones or []) if isinstance(item, dict) and item.get("zone_name")]
    if not clean:
        return
    options = [""] + [str(item.get("zone_name")) for item in clean]
    version = int(st.session_state.get("zone_selector_version", 0))
    selected = st.selectbox(
        "Open Availability Zone in Chat",
        options=options,
        index=0,
        key=f"zone_context_selector_{version}",
        placeholder="Choose an Availability Zone...",
    )
    if not selected:
        return
    item = next((row for row in clean if str(row.get("zone_name")) == selected), None)
    if not item:
        return
    st.session_state["zone_selector_version"] = version + 1
    _open_context_chat(
        context={
            "context_type": "AVAILABILITY_ZONE",
            "label": selected,
            "availability_zone": selected,
            "zone_id": item.get("zone_id"),
            "region": item.get("region_name"),
            "state": item.get("state"),
            "zone_type": item.get("zone_type"),
        },
        title=f"{selected} · Saved Scan",
    )


def _render_resource_chat_selector(resources: list[dict] | None) -> None:
    clean = [item for item in (resources or []) if isinstance(item, dict)]
    if not clean:
        return

    options: list[str] = [""]
    mapping: dict[str, dict] = {}
    for index, item in enumerate(clean):
        resource_id = item.get("resource_id") or item.get("arn") or f"resource-{index + 1}"
        service = item.get("service") or "aws"
        region = item.get("region") or "global/unknown"
        label = f"{resource_id} · {service} · {region}"
        # Make duplicate display values unique without changing evidence.
        if label in mapping:
            label = f"{label} · #{index + 1}"
        options.append(label)
        mapping[label] = item

    selector_version = int(st.session_state.get("resource_selector_version", 0))
    selected = st.selectbox(
        "Open discovered resource in Chat",
        options=options,
        index=0,
        key=f"resource_context_selector_{selector_version}",
        placeholder="Choose a discovered AWS resource...",
    )
    if not selected:
        return

    item = mapping[selected]
    resource_id = item.get("resource_id") or item.get("arn") or "AWS Resource"
    # Reset before changing page so returning to Discovery does not reopen it.
    st.session_state["resource_selector_version"] = selector_version + 1
    _open_context_chat(
        context={
            "context_type": "RESOURCE",
            "label": str(resource_id),
            "resource_id": item.get("resource_id"),
            "arn": item.get("arn"),
            "service": item.get("service"),
            "resource_type": item.get("resource_type"),
            "region": item.get("region"),
            "owning_account_id": item.get("owning_account_id"),
        },
        title=f"{resource_id} · Saved Scan",
    )


# ============================================================
# BACKEND AWS SESSION
# ============================================================

def get_aws_backend_session_status() -> bool:
    """Return True when the backend still has active transient AWS credentials."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/aws/session/status",
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return False

        payload = response.json()
        return bool(
            isinstance(payload, dict)
            and payload.get("connected") is True
        )

    except requests.RequestException:
        return False


def disconnect_aws_backend_session() -> None:
    """Best-effort removal of transient AWS credentials from the backend."""
    if not st.session_state.get("access_token"):
        return

    try:
        requests.delete(
            f"{API_BASE_URL}/aws/session",
            headers=get_auth_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        pass


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
        "active_chat_id",
        "active_chat",
        "active_snapshot_bootstrapped",
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
    st.session_state.pop(
        "active_chat_id",
        None,
    )
    st.session_state.pop(
        "active_chat",
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
        _render_region_chat_buttons(
            [
                {
                    "region": item.get("region_name"),
                    "category": "ENABLED_REGION",
                }
                for item in enabled_region_rows
            ],
            key_prefix="enabled_region_chat",
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
        _render_zone_chat_selector(zones)
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
        "Resource-backed AWS Services"
    )

    if detected_services:
        service_rows = []
        for item in detected_services:
            if not isinstance(item, dict):
                continue
            namespace = str(item.get("service") or "").strip()
            if not namespace:
                continue
            service_rows.append(
                {
                    "service_namespace": namespace,
                    "resources": item.get("resource_count", 0),
                    "regions": ", ".join(
                        map(str, item.get("regions") or [])
                    ) or "-",
                    "evidence": "Resource Explorer resource",
                }
            )

        if service_rows:
            st.dataframe(
                service_rows,
                use_container_width=True,
                hide_index=True,
            )
            _render_discovered_service_chat_buttons(detected_services)
        else:
            st.info("No resource-backed AWS services were detected.")
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

        _render_resource_chat_selector(resources)

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


def _format_currency_amount(
    amount: object,
    currency: str = "USD",
) -> str:
    """Format backend billing values safely for UI display."""
    try:
        numeric_amount = float(amount or 0)
    except (TypeError, ValueError):
        numeric_amount = 0.0

    normalized_currency = str(currency or "USD").strip() or "USD"
    return f"{normalized_currency} {numeric_amount:,.2f}"


def _classified_service_rows(
    services: list[dict] | None,
) -> list[dict]:
    """Flatten classified service objects into readable table rows."""
    rows: list[dict] = []

    for item in services or []:
        if not isinstance(item, dict):
            continue

        billing_services = item.get("billing_services") or []
        regions = item.get("regions") or []
        related = item.get("related_primary_services") or []

        # Prefer the official Cost Explorer SERVICE label for user-facing
        # display. The discovered namespace is still retained separately as
        # technical evidence. This prevents SDK/API identifiers from becoming
        # the main service name shown to the auditor.
        service_name = (
            (billing_services[0] if billing_services else None)
            or item.get("discovered_service")
            or "-"
        )

        confidence = item.get("billing_match_confidence")
        if isinstance(confidence, (int, float)):
            confidence_display = round(float(confidence), 3)
        else:
            confidence_display = None

        rows.append(
            {
                "service": service_name,
                "resource_namespace": item.get("discovered_service") or "-",
                "category": item.get("category", "-"),
                "financial_status": item.get("financial_status", "-"),
                "paid": bool(item.get("paid")),
                "cost": _format_currency_amount(
                    item.get("billing_amount"),
                    str(item.get("currency") or "USD"),
                ),
                "resources": item.get("resource_count", 0),
                "regions": ", ".join(map(str, regions)) if regions else "-",
                "billing_services": (
                    ", ".join(map(str, billing_services))
                    if billing_services
                    else "-"
                ),
                "related_primary_services": (
                    ", ".join(map(str, related))
                    if related
                    else "-"
                ),
                "billing_match": item.get("billing_match_method") or "-",
                "match_confidence": confidence_display,
            }
        )

    return rows


def _classified_region_rows(
    regions: list[dict] | None,
) -> list[dict]:
    """Flatten classified Region objects into readable table rows."""
    rows: list[dict] = []

    for item in regions or []:
        if not isinstance(item, dict):
            continue

        rows.append(
            {
                "region": item.get("region", "-"),
                "category": item.get("category", "-"),
                "cost": _format_currency_amount(
                    item.get("billing_amount"),
                    str(item.get("currency") or "USD"),
                ),
                "resources": item.get("resource_count", 0),
                "enabled": bool(item.get("enabled")),
            }
        )

    return rows


def render_billing_results(
    billing_data: dict | None,
) -> None:
    """Render dynamic Cost Explorer evidence returned by the backend."""
    if not billing_data:
        return

    st.divider()
    st.subheader("Billing Evidence")

    available = billing_data.get("available") is True
    currency = str(billing_data.get("currency") or "USD")
    service_costs = billing_data.get("service_costs") or []
    region_costs = billing_data.get("region_costs") or []
    components = billing_data.get("components") or []

    billing_cols = st.columns(4)

    with billing_cols[0]:
        st.metric("Billing Access", "Available" if available else "Unavailable")

    with billing_cols[1]:
        st.metric(
            "Current Period Cost",
            _format_currency_amount(
                billing_data.get("total_cost"),
                currency,
            ),
        )

    with billing_cols[2]:
        st.metric("Billed Services", len(service_costs))

    with billing_cols[3]:
        st.metric("Billing Regions", len(region_costs))

    period_start = billing_data.get("period_start")
    period_end = billing_data.get("period_end_exclusive")
    metric = billing_data.get("metric") or "UnblendedCost"

    if period_start or period_end:
        st.caption(
            f"Billing window: {period_start or '-'} to {period_end or '-'} "
            f"(end exclusive) · Metric: {metric}"
        )

    if not available:
        st.warning(
            "Billing data is unavailable for this scan. Infrastructure discovery "
            "can still be used, but paid/primary classification may be incomplete."
        )

    service_tab, region_tab, component_tab = st.tabs(
        ["Service Cost", "Region Cost", "Billing Components"]
    )

    with service_tab:
        if service_costs:
            rows = []
            for item in service_costs:
                if not isinstance(item, dict):
                    continue
                try:
                    amount = float(item.get("amount") or 0)
                except (TypeError, ValueError):
                    amount = 0.0

                if amount > 1e-9:
                    cost_status = "POSITIVE_COST"
                elif amount < -1e-9:
                    cost_status = "CREDIT_OR_ADJUSTMENT"
                else:
                    cost_status = "ZERO_COST"

                rows.append(
                    {
                        "billing_service": item.get("billing_service", "-"),
                        "amount": amount,
                        "unit": item.get("unit", currency),
                        "cost_status": cost_status,
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
            _render_billing_service_chat_selector(service_costs)
        else:
            st.info("No service-level billing groups were returned.")

    with region_tab:
        if region_costs:
            rows = [
                {
                    "region": item.get("region", "-"),
                    "amount": item.get("amount", 0),
                    "unit": item.get("unit", currency),
                }
                for item in region_costs
                if isinstance(item, dict)
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No Region-level billing groups were returned.")

    with component_tab:
        if components:
            rows = [
                {
                    "billing_service": item.get("billing_service", "-"),
                    "usage_type": item.get("usage_type", "-"),
                    "amount": item.get("amount", 0),
                    "unit": item.get("unit", currency),
                }
                for item in components
                if isinstance(item, dict)
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No SERVICE + USAGE_TYPE billing components were returned.")

    with st.expander("View Complete Billing Data", expanded=False):
        st.json(billing_data)


def render_classification_results(
    classification_data: dict | None,
) -> None:
    """Render billing-aware service and Region classification."""
    if not classification_data:
        return

    st.divider()
    st.subheader("Infrastructure Classification")

    primary = classification_data.get("primary_paid_services") or []
    zero_cost = classification_data.get("zero_cost_services") or []
    supporting = classification_data.get("supporting_services") or []
    unbilled = classification_data.get("discovered_unbilled_services") or []
    billing_only = classification_data.get("billing_only_services") or []
    non_positive = classification_data.get("non_positive_billing_services") or []

    # New scans keep billing-only Cost Explorer groups separate in the backend.
    # The fallback below also handles older persisted scans created before that
    # field existed. No service names are hard-coded.
    primary_resource_backed = [
        item
        for item in primary
        if isinstance(item, dict) and item.get("discovered_service")
    ]
    legacy_billing_only = [
        item
        for item in primary
        if isinstance(item, dict) and not item.get("discovered_service")
    ]
    billing_only_primary = [
        *[item for item in billing_only if isinstance(item, dict)],
        *legacy_billing_only,
    ]

    paid_regions = classification_data.get("paid_regions") or []
    used_unbilled_regions = (
        classification_data.get("used_unbilled_regions") or []
    )
    enabled_unused_regions = (
        classification_data.get("enabled_unused_regions") or []
    )
    billed_only_regions = classification_data.get("billed_only_regions") or []
    relationships = classification_data.get("relationships") or []

    summary_cols = st.columns(5)
    with summary_cols[0]:
        st.metric("Primary Paid AWS Services", len(primary_resource_backed))
    with summary_cols[1]:
        st.metric("Zero-Cost Candidates", len(zero_cost))
    with summary_cols[2]:
        st.metric("Supporting Services", len(supporting))
    with summary_cols[3]:
        st.metric("Discovered Unbilled", len(unbilled))
    with summary_cols[4]:
        st.metric("Paid Regions", len(paid_regions))

    st.caption(
        "Primary/paid AWS services require discovered resource evidence plus "
        "positive billing cost. A Zero-Cost / Free-Tier Candidate has a matched "
        "Cost Explorer SERVICE record whose net cost is zero; this does not by "
        "itself prove AWS Free Tier or trial eligibility. Supporting classification "
        "is derived from resource relationships. No fixed service allow/deny list "
        "is used."
    )

    service_tab, region_tab, relationship_tab = st.tabs(
        ["Service Classification", "Region Classification", "Relationships"]
    )

    with service_tab:
        st.markdown("#### Primary / Paid AWS Services")
        rows = _classified_service_rows(primary_resource_backed)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
            _render_service_chat_buttons(
                primary_resource_backed,
                key_prefix="primary_service_chat",
            )
        else:
            st.info(
                "No positively billed services were mapped to discovered "
                "AWS infrastructure for this scan."
            )

        if billing_only_primary:
            with st.expander(
                "Billing entries not mapped to discovered infrastructure "
                f"({len(billing_only_primary)})",
                expanded=False,
            ):
                st.caption(
                    "These values came from Cost Explorer SERVICE groups but "
                    "were not matched to a resource-backed service namespace, "
                    "so they are not shown as discovered AWS infrastructure."
                )
                st.dataframe(
                    _classified_service_rows(billing_only_primary),
                    use_container_width=True,
                    hide_index=True,
                )

        st.markdown("#### Zero-Cost / Free-Tier Candidates")
        zero_rows = _classified_service_rows(zero_cost)
        if zero_rows:
            st.caption(
                "These services have discovered resource evidence and a matched "
                "Cost Explorer SERVICE record with net cost 0. They may be Free "
                "Tier/trial, permanently free usage, discounted usage, credits, "
                "or another zero-cost case; the scan does not claim the exact "
                "commercial reason without stronger billing evidence."
            )
            st.dataframe(zero_rows, use_container_width=True, hide_index=True)
            _render_service_chat_buttons(
                zero_cost,
                key_prefix="zero_cost_service_chat",
            )
        else:
            st.info("No resource-backed zero-cost billing services were classified.")

        st.markdown("#### Supporting / Related AWS Services")
        rows = _classified_service_rows(supporting)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
            _render_service_chat_buttons(
                supporting,
                key_prefix="supporting_service_chat",
            )
        else:
            st.info("No supporting service relationships were classified.")

        with st.expander(
            f"Discovered but Unbilled Services ({len(unbilled)})",
            expanded=False,
        ):
            rows = _classified_service_rows(unbilled)
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
                _render_service_chat_buttons(
                    unbilled,
                    key_prefix="unbilled_service_chat",
                )
            else:
                st.info("No discovered unbilled services were classified.")

        if non_positive:
            with st.expander(
                f"Non-Positive Billing Services ({len(non_positive)})",
                expanded=False,
            ):
                st.dataframe(
                    _classified_service_rows(non_positive),
                    use_container_width=True,
                    hide_index=True,
                )

    with region_tab:
        region_groups = [
            ("Paid / Primary Regions", paid_regions),
            ("Used but Unbilled Regions", used_unbilled_regions),
            ("Enabled but Unused Regions", enabled_unused_regions),
            ("Billing-Only Regions", billed_only_regions),
        ]

        for title, items in region_groups:
            st.markdown(f"#### {title}")
            rows = _classified_region_rows(items)
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
                _render_region_chat_buttons(
                    items,
                    key_prefix=f"region_chat_{title.lower().replace(' ', '_').replace('/', '_')}",
                )
            else:
                st.caption("No Regions in this category.")

    with relationship_tab:
        if relationships:
            relationship_rows = []
            for item in relationships:
                if not isinstance(item, dict):
                    continue
                relationship_rows.append(
                    {
                        "source_service": item.get("source_service") or "-",
                        "source_resource": (
                            item.get("source_resource_id")
                            or item.get("source_arn")
                            or "-"
                        ),
                        "target_service": item.get("target_service") or "-",
                        "target_resource": (
                            item.get("target_resource_id")
                            or item.get("target_arn")
                            or "-"
                        ),
                        "evidence": item.get("evidence") or "-",
                    }
                )

            st.dataframe(
                relationship_rows,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No resource-to-resource relationships were inferred.")

    classification_warnings = classification_data.get("warnings") or []
    if classification_warnings:
        with st.expander(
            f"Classification Warnings ({len(classification_warnings)})",
            expanded=False,
        ):
            for warning in classification_warnings:
                st.warning(str(warning))

    with st.expander("View Complete Classification Data", expanded=False):
        st.json(classification_data)


# Deep service scan renderers removed. Detailed configuration is queried
# on demand through the NLP -> generic read-only AWS MCP query flow.


def render_scan_status(
    aws_connection: dict | None,
    scan_data: dict | None,
    region_data: dict | None,
    zone_data: dict | None,
    resource_data: dict | None,
    billing_data: dict | None,
    classification_data: dict | None,
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
        {
            "stage": "Billing Discovery",
            "status": (
                (
                    "Completed"
                    if billing_data.get("available") is True
                    else "Unavailable / Partial"
                )
                if billing_data
                else "Pending"
            ),
        },
        {
            "stage": "Billing-Aware Classification",
            "status": (
                "Completed"
                if classification_data
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
    """
    Compact ChatGPT-style sidebar.

    Important:
    HTML passed to st.markdown is intentionally kept left-aligned
    (no Markdown indentation), otherwise Markdown can interpret the
    indented HTML as a code block and render large white rectangles.
    """

    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "home"

    active_page = st.session_state.get(
        "active_page",
        "home",
    )

    active_chat_id = st.session_state.get(
        "active_chat_id"
    )

    current_user = st.session_state.get(
        "current_user",
        {},
    )

    with st.sidebar:

        # ====================================================
        # BRAND
        # ====================================================

        st.markdown(
            """<div class="cc-sidebar-brand">
<div class="cc-sidebar-brand-row">
<div class="cc-sidebar-logo">☁</div>
<div>
<div class="cc-sidebar-title">AWS AI Auditor</div>
<div class="cc-sidebar-subtitle">Cloud audit intelligence</div>
</div>
</div>
</div>""",
            unsafe_allow_html=True,
        )

        # ====================================================
        # USER
        # ====================================================

        if current_user:
            username = escape(
                str(
                    current_user.get(
                        "username",
                        "User",
                    )
                )
            )

            email = escape(
                str(
                    current_user.get(
                        "email",
                        "",
                    )
                )
            )

            initial = (
                username[:1].upper()
                if username
                else "U"
            )

            st.markdown(
                f"""<div class="cc-sidebar-user">
<div class="cc-user-avatar">{initial}</div>
<div class="cc-user-copy">
<div class="cc-user-name">{username}</div>
<div class="cc-user-email">{email}</div>
</div>
</div>""",
                unsafe_allow_html=True,
            )

        # ====================================================
        # MAIN NAVIGATION
        # ====================================================

        st.markdown(
            '<div class="cc-sidebar-label">Workspace</div>',
            unsafe_allow_html=True,
        )

        navigation = [
            ("home", "⌂", "Home"),
            ("discovery", "⌕", "Discovery"),
            ("chat", "◌", "Chat"),
            ("settings", "⚙", "Settings"),
        ]

        for page_key, icon, title in navigation:
            selected = active_page == page_key

            if st.button(
                f"{icon}   {title}",
                use_container_width=True,
                key=f"sidebar_nav_{page_key}",
                type=(
                    "primary"
                    if selected
                    else "secondary"
                ),
            ):
                # Home/Discovery always return to the persisted active snapshot.
                # Historical chats remain tied to their own scan while open.
                if page_key in {"home", "discovery"}:
                    active_snapshot = get_active_scan()
                    if active_snapshot:
                        st.session_state["aws_scan"] = active_snapshot
                        st.session_state["aws_connection"] = active_snapshot.get(
                            "account", {}
                        )
                st.session_state[
                    "active_page"
                ] = page_key
                st.rerun()

        # ====================================================
        # CHAT HISTORY
        # ====================================================

        st.markdown(
            '<div class="cc-sidebar-divider"></div>',
            unsafe_allow_html=True,
        )

        can_create_chat = bool(
            scan_data
            and scan_data.get("status") == "COMPLETED"
            and scan_data.get("scan_id")
        )

        if st.button(
            "＋  New Chat",
            use_container_width=True,
            key="sidebar_new_chat",
            disabled=not can_create_chat,
        ):
            created = create_chat(
                scan_id=str(
                    scan_data.get(
                        "scan_id"
                    )
                ),
                title="New AWS Chat",
            )

            if created:
                chat_id = created.get("id")

                st.session_state[
                    "active_chat_id"
                ] = chat_id

                st.session_state[
                    "active_chat"
                ] = created

                st.session_state[
                    "active_page"
                ] = "chat"

                st.rerun()

        st.markdown(
            '<div class="cc-sidebar-label cc-chat-label">Recent chats</div>',
            unsafe_allow_html=True,
        )

        chats = get_chat_history()

        if chats:
            for chat in chats[:25]:
                chat_id = chat.get("id")

                if chat_id is None:
                    continue

                title = str(
                    chat.get("title")
                    or f"Chat {chat_id}"
                ).strip()

                if len(title) > 29:
                    title = title[:26] + "..."

                is_active = (
                    active_chat_id
                    == chat_id
                )

                if st.button(
                    (
                        f"●  {title}"
                        if is_active
                        else f"◦  {title}"
                    ),
                    use_container_width=True,
                    key=f"sidebar_chat_{chat_id}",
                    type=(
                        "primary"
                        if is_active
                        else "secondary"
                    ),
                ):
                    _open_chat_session(
                        int(chat_id)
                    )
                    st.rerun()
        else:
            st.markdown(
                """<div class="cc-empty-chats">
No saved chats yet.<br>
<span>Start a chat after discovery.</span>
</div>""",
                unsafe_allow_html=True,
            )

        # ====================================================
        # ACCOUNT / FOOTER
        # ====================================================

        st.markdown(
            '<div class="cc-sidebar-divider cc-footer-divider"></div>',
            unsafe_allow_html=True,
        )

        if aws_connection:
            account_id = escape(
                str(
                    aws_connection.get(
                        "account_id",
                        "-",
                    )
                )
            )

            connection_status = escape(
                str(
                    aws_connection.get(
                        "connection_status",
                        "VERIFIED",
                    )
                )
            )

            scan_status = (
                escape(
                    str(
                        scan_data.get(
                            "status",
                            "UNKNOWN",
                        )
                    )
                )
                if scan_data
                else "Not scanned"
            )

            st.markdown(
                f"""<div class="cc-account-card">
<div class="cc-account-top">
<span>AWS ACCOUNT</span>
<span class="cc-account-dot">●</span>
</div>
<div class="cc-account-id">{account_id}</div>
<div class="cc-account-meta">{connection_status} · {scan_status}</div>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div class="cc-account-card">
<div class="cc-account-top">
<span>AWS ACCOUNT</span>
<span class="cc-account-dot cc-account-dot-off">●</span>
</div>
<div class="cc-account-id">Not connected</div>
<div class="cc-account-meta">Connect from Home</div>
</div>""",
                unsafe_allow_html=True,
            )

        if st.button(
            "↪  Sign Out",
            use_container_width=True,
            key="sidebar_sign_out",
        ):
            logout_user()
            st.rerun()


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

    completed_at = scan_data.get("completed_at") or scan_data.get("started_at")
    active_label = "Active saved snapshot" if scan_data.get("is_active") else "Saved historical snapshot"
    st.caption(
        f"{active_label} · Scan ID: {str(scan_data.get('scan_id') or '-')[:16]}"
        + (f" · Scanned: {completed_at}" if completed_at else "")
    )

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

    billing_metric_cols = st.columns(5)

    with billing_metric_cols[0]:
        st.metric(
            "💳 Billing",
            "Available"
            if summary.get("billing_available")
            else "Unavailable",
        )

    with billing_metric_cols[1]:
        st.metric(
            "Paid Services",
            summary.get("primary_paid_services", 0),
        )

    with billing_metric_cols[2]:
        st.metric(
            "Zero-Cost",
            summary.get("zero_cost_services", 0),
        )

    with billing_metric_cols[3]:
        st.metric(
            "Supporting Services",
            summary.get("supporting_services", 0),
        )

    with billing_metric_cols[4]:
        st.metric(
            "Paid Regions",
            summary.get("paid_regions", 0),
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

    source = result.get("source")
    if source:
        st.caption(f"Evidence source: {source}")

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
    """Render the persisted chat interface for the selected chat session."""

    if scan_data.get("status") != "COMPLETED":
        st.warning(
            "Run or restore a completed discovery scan before opening chat."
        )
        return

    scan_id = scan_data.get("scan_id")

    if not scan_id:
        st.error(
            "This discovery result does not contain a scan_id. "
            "Run or restore a persisted scan first."
        )
        return

    backend_session_active = get_aws_backend_session_status()

    active_chat_id = st.session_state.get("active_chat_id")

    # If no chat is selected, select the newest chat linked to this scan.
    if active_chat_id is None:
        chats = get_chat_history()
        matching = [
            item
            for item in chats
            if str(item.get("scan_id")) == str(scan_id)
        ]

        if matching:
            active_chat_id = matching[0].get("id")
            st.session_state["active_chat_id"] = active_chat_id
        else:
            created = create_chat(
                scan_id=str(scan_id),
                title="New AWS Chat",
            )
            if created:
                active_chat_id = created.get("id")
                st.session_state["active_chat_id"] = active_chat_id

    chat = (
        get_chat(int(active_chat_id))
        if active_chat_id is not None
        else None
    )

    if not chat:
        st.info(
            "Select a chat from the sidebar or create a new chat."
        )
        return

    st.session_state["active_chat"] = chat

    header_col, session_col = st.columns([5.6, 1.4])

    with header_col:
        st.markdown(
            f"""
            <div class="chat-heading">🤖 {chat.get("title") or "AWS AI Assistant"}</div>
            <div class="chat-subtitle">
                Ask naturally about the saved discovery snapshot. Questions that truly
                require current AWS state can automatically use live read-only AWS MCP
                when a live AWS session is connected.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with session_col:
        if backend_session_active:
            st.success("Live AWS connected")
        else:
            st.info("Live AWS not connected")

    st.caption(
        f"Chat #{chat.get('id')} · Snapshot: {str(scan_id)[:12]}… · "
        "Messages and selected context are saved in SQLite."
    )

    chat_context = chat.get("context") or {}
    if chat_context:
        context_type = chat_context.get("context_type") or "CONTEXT"
        context_label = chat_context.get("label") or chat_context.get("resource_id") or chat_context.get("region") or "Selected item"
        st.info(f"Selected {context_type}: {context_label}")

    if not backend_session_active:
        st.info(
            "Saved-snapshot questions remain available. Live AWS credentials are kept only "
            "in backend memory and may be cleared by a server restart/reload. Reconnect "
            "only for current/live AWS queries or a manual refresh."
        )

    messages = chat.get("messages") or []

    if not messages:
        with st.chat_message("assistant"):
            st.markdown(
                "Hello! I'm your AWS AI Assistant. Ask me about the infrastructure "
                "discovered for this AWS account."
            )
    else:
        for message in messages:
            role = str(message.get("role", "assistant"))
            content = str(message.get("content", ""))

            with st.chat_message(role):
                st.markdown(content)

                if role == "assistant":
                    evidence = message.get("evidence") or {}
                    source = evidence.get("source") if isinstance(evidence, dict) else None
                    if source == "PERSISTED_DISCOVERY_SNAPSHOT":
                        st.caption("Source: saved immutable discovery snapshot")
                    elif source == "LIVE_AWS_MCP":
                        st.caption("Source: live read-only AWS MCP query")

                    response_time_ms = message.get("response_time_ms")
                    if response_time_ms is not None:
                        try:
                            seconds = float(response_time_ms) / 1000
                            st.caption(f"⏱ Answered in {seconds:.2f} seconds")
                        except (TypeError, ValueError):
                            pass

    question = st.chat_input(
        "Ask about this saved AWS snapshot or request current/live AWS state...",
        disabled=False,
        key=f"chat_input_{chat.get('id')}",
    )

    if not question:
        return

    question = question.strip()
    if not question:
        return

    # Render the new message immediately in this run.
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(
            "Resolving the question from the saved snapshot or live AWS evidence..."
        ):
            query_result = query_chat(
                chat_id=int(chat.get("id")),
                question=question,
            )

        answer = _extract_query_answer(query_result)
        query_status = _query_status_label(query_result)

        if query_status == "SUCCESS":
            st.markdown(answer)
        else:
            st.warning(answer)

        if isinstance(query_result, dict):
            source = query_result.get("source")
            if source == "PERSISTED_DISCOVERY_SNAPSHOT":
                st.caption("Source: saved immutable discovery snapshot")
            elif source == "LIVE_AWS_MCP":
                st.caption("Source: live read-only AWS MCP query")
            _render_query_timing(query_result)

            with st.expander(
                "View AWS evidence",
                expanded=False,
            ):
                _render_query_evidence(query_result)

    # Reload persisted history so sidebar/chat stay in sync.
    refreshed = get_chat(int(chat.get("id")))
    if refreshed:
        st.session_state["active_chat"] = refreshed

    st.rerun()


def render_reconnect_aws_form(expected_account_id: str | None = None) -> None:
    """Reconnect transient AWS credentials without replacing the saved snapshot."""
    with st.expander("Reconnect AWS for live queries / manual refresh", expanded=False):
        st.caption(
            "Saved discovery data remains available without credentials. Reconnect only "
            "when you need live AWS data or want to manually create a fresh snapshot."
        )
        with st.form("reconnect_aws_credentials_form"):
            access_key_id = st.text_input(
                "AWS Access Key ID",
                placeholder="AKIA...",
                key="reconnect_access_key_id",
            )
            secret_access_key = st.text_input(
                "AWS Secret Access Key",
                type="password",
                key="reconnect_secret_access_key",
            )
            session_token = st.text_input(
                "AWS Session Token (optional)",
                type="password",
                key="reconnect_session_token",
            )
            submitted = st.form_submit_button(
                "Reconnect AWS Session",
                type="primary",
                use_container_width=True,
            )

        if not submitted:
            return
        if not access_key_id or not secret_access_key:
            st.error("Access Key ID and Secret Access Key are required.")
            return

        payload = {
            "access_key_id": access_key_id.strip(),
            "secret_access_key": secret_access_key,
            "session_token": session_token.strip() if session_token.strip() else None,
        }
        verified = verify_aws_account(payload)
        if not verified:
            return

        verified_account_id = str(verified.get("account_id") or "")
        if expected_account_id and verified_account_id != str(expected_account_id):
            disconnect_aws_backend_session()
            st.error(
                "These credentials belong to a different AWS account. The saved "
                "snapshot was not changed."
            )
            return

        st.session_state["aws_connection"] = verified
        st.session_state["aws_credentials"] = payload
        st.success("AWS live session reconnected. Saved snapshot remains unchanged.")
        st.rerun()


# ============================================================
# PAGE RENDERERS
# ============================================================

def render_home_page(
    aws_connection: dict | None,
    scan_data: dict | None,
) -> None:
    """
    Home also acts as the AWS connection page.

    When no AWS account is connected:
        show the AWS credential form.

    When an account is connected:
        show account/discovery overview and quick actions.
    """

    st.markdown(
        """
        <div class="overview-title">AWS AI Auditor</div>
        <div class="overview-subtitle">
            Connect a client AWS account, discover its infrastructure,
            and ask live read-only audit questions through the official
            AWS Managed MCP Server.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    # ========================================================
    # NOT CONNECTED -> CONNECT DIRECTLY FROM HOME
    # ========================================================

    if not aws_connection:

        st.info(
            "No AWS account is connected. "
            "Enter the client credentials below to begin."
        )

        with st.form(
            "home_aws_connection_form"
        ):
            st.subheader(
                "Connect AWS Account"
            )

            access_key_id = st.text_input(
                "AWS Access Key ID",
                placeholder="AKIA...",
            )

            secret_access_key = (
                st.text_input(
                    "AWS Secret Access Key",
                    type="password",
                )
            )

            session_token = (
                st.text_input(
                    "AWS Session Token (optional)",
                    type="password",
                )
            )

            connect_clicked = (
                st.form_submit_button(
                    "Verify AWS Account",
                    type="primary",
                    use_container_width=True,
                )
            )

        if connect_clicked:

            if (
                not access_key_id
                or not secret_access_key
            ):
                st.error(
                    "Access Key ID and Secret Access Key are required."
                )

            else:
                credentials_payload = {
                    "access_key_id":
                        access_key_id.strip(),

                    "secret_access_key":
                        secret_access_key,

                    "session_token":
                        (
                            session_token.strip()
                            if session_token.strip()
                            else None
                        ),
                }

                verification_data = (
                    verify_aws_account(
                        credentials_payload
                    )
                )

                if verification_data:
                    st.session_state[
                        "aws_connection"
                    ] = verification_data

                    st.session_state[
                        "aws_credentials"
                    ] = credentials_payload

                    # Reuse the previously saved active snapshot for this account.
                    # Verification never triggers a discovery refresh automatically.
                    saved_scan = get_active_scan(
                        str(verification_data.get("account_id") or "")
                    )
                    if saved_scan:
                        st.session_state["aws_scan"] = saved_scan
                    else:
                        clear_scan_results()

                    st.success(
                        "AWS account verified successfully."
                    )

                    st.rerun()

        return

    # ========================================================
    # CONNECTED ACCOUNT SUMMARY
    # ========================================================

    account_id = aws_connection.get(
        "account_id",
        "-",
    )

    top_cols = st.columns(
        [2.2, 1, 1]
    )

    live_session_active = get_aws_backend_session_status()

    with top_cols[0]:
        if live_session_active:
            st.success(f"AWS account {account_id} · live session connected.")
        else:
            st.info(f"AWS account {account_id} · saved snapshot loaded.")

    with top_cols[1]:
        st.metric(
            "Provider",
            aws_connection.get(
                "provider",
                "AWS",
            ),
        )

    with top_cols[2]:
        st.metric(
            "Runtime",
            "Live" if live_session_active else "Snapshot",
        )

    with st.expander(
        "AWS connection details",
        expanded=False,
    ):
        st.write(
            f"**Account ID:** {account_id}"
        )

        st.write(
            "**Caller ARN:** "
            f"{aws_connection.get('arn', 'ARN not returned')}"
        )

        st.write(
            "**Backend session:** "
            + (
                "Active"
                if get_aws_backend_session_status()
                else "Not active"
            )
        )

        if st.button(
            "Disconnect Live AWS Session",
            use_container_width=True,
            key="home_disconnect_aws",
        ):
            disconnect_aws_backend_session()
            st.session_state.pop("aws_credentials", None)
            # Keep the persisted discovery snapshot loaded. Disconnecting only
            # removes live AWS credentials; saved evidence remains available.
            st.session_state[
                "active_page"
            ] = "home"
            st.rerun()

    # ========================================================
    # CONNECTED BUT NO DISCOVERY
    # ========================================================

    if not scan_data:
        st.write("")

        st.info(
            "The AWS account is verified. "
            "Run Discovery to establish Regions, Availability Zones, resources, "
            "billing evidence, and dynamic service/Region classification."
        )

        if st.button(
            "Open Discovery",
            type="primary",
            use_container_width=True,
            key="home_open_discovery",
        ):
            st.session_state[
                "active_page"
            ] = "discovery"

            st.rerun()

        return

    # ========================================================
    # COMPLETED / EXISTING DISCOVERY
    # ========================================================

    st.write("")

    render_template1_overview(
        aws_connection=aws_connection,
        scan_data=scan_data,
    )

    if (
        scan_data.get("status")
        == "COMPLETED"
    ):
        st.write("")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "Open Chat",
                type="primary",
                use_container_width=True,
                key="home_open_chat",
            ):
                st.session_state[
                    "active_page"
                ] = "chat"

                st.rerun()

        with col2:
            if st.button(
                "View Discovery Details",
                use_container_width=True,
                key="home_view_discovery",
            ):
                st.session_state[
                    "active_page"
                ] = "discovery"

                st.rerun()


def render_discovery_page(
    aws_connection: dict | None,
    scan_data: dict | None,
) -> None:
    st.markdown(
        """
        <div class="overview-title">AWS Discovery</div>
        <div class="overview-subtitle">
            Discover AWS infrastructure, billing evidence, and dynamically classified services/Regions for live NLP queries.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    if not aws_connection:
        st.info("Connect an AWS account before running discovery.")
        if st.button("Go to Connect", type="primary"):
            st.session_state["active_page"] = "connect"
            st.rerun()
        return

    if not scan_data:
        st.success(
            f"Connected to AWS account {aws_connection.get('account_id', '-')}"
        )
        backend_session_active = get_aws_backend_session_status()

        if backend_session_active:
            run_scan_clicked = st.button(
                "Create First Discovery Snapshot",
                type="primary",
                use_container_width=True,
                key="start_aws_discovery_scan",
            )
            if run_scan_clicked:
                new_scan_data = refresh_aws_scan()
                if new_scan_data:
                    st.session_state["aws_scan"] = new_scan_data
                    st.session_state["active_chat_id"] = None
                    st.session_state["active_chat"] = None
                    st.rerun()
        else:
            st.info(
                "No saved snapshot exists for this account and the live AWS session "
                "is not active. Reconnect to create the first snapshot."
            )
            render_reconnect_aws_form(
                expected_account_id=str(aws_connection.get("account_id") or "")
            )
        return

    render_template1_overview(
        aws_connection=aws_connection,
        scan_data=scan_data,
    )

    backend_session_active = get_aws_backend_session_status()
    snapshot_time = scan_data.get("completed_at") or scan_data.get("started_at") or "-"
    st.info(
        f"This page is using saved scan {str(scan_data.get('scan_id') or '-')[:16]} "
        f"from {snapshot_time}. It will remain unchanged until you manually refresh "
        "or activate another historical scan."
    )

    refresh_col, session_col = st.columns([1.4, 2.6])
    with refresh_col:
        refresh_clicked = st.button(
            "Refresh Discovery Snapshot",
            type="primary",
            use_container_width=True,
            key="manual_refresh_discovery_snapshot",
            disabled=not backend_session_active,
        )
        if refresh_clicked:
            new_scan_data = refresh_aws_scan()
            if new_scan_data:
                st.session_state["aws_scan"] = new_scan_data
                st.session_state["aws_connection"] = new_scan_data.get("account", aws_connection)
                # Existing chats stay tied to their original immutable scan. New chat
                # selection starts from the newly active snapshot.
                st.session_state["active_chat_id"] = None
                st.session_state["active_chat"] = None
                st.rerun()

    with session_col:
        if backend_session_active:
            st.success("Live AWS connected · manual refresh/live queries available")
        else:
            st.info("Live AWS not connected · saved snapshot/chat still available")

    if not backend_session_active:
        render_reconnect_aws_form(
            expected_account_id=str((scan_data.get("account") or {}).get("account_id") or aws_connection.get("account_id") or "")
        )

    render_scan_status(
        aws_connection=aws_connection,
        scan_data=scan_data,
        region_data=scan_data.get("regions"),
        zone_data=scan_data.get("zones"),
        resource_data=scan_data.get("resources"),
        billing_data=scan_data.get("billing"),
        classification_data=scan_data.get("classification"),
    )

    # Billing-aware results are shown before raw inventory so the auditor
    # immediately sees what is paid/primary and how Regions are classified.
    render_billing_results(scan_data.get("billing"))
    render_classification_results(scan_data.get("classification"))

    render_region_results(scan_data.get("regions"))
    render_zone_results(scan_data.get("zones"))
    render_resource_inventory(scan_data.get("resources"))
    render_scan_warnings(scan_data.get("warnings") or [])

    if scan_data.get("status") == "COMPLETED":
        st.write("")
        if st.button(
            "Open AI Chat",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["active_page"] = "chat"
            st.rerun()


def render_settings_page(
    aws_connection: dict | None,
    scan_data: dict | None,
) -> None:
    st.markdown(
        """
        <div class="overview-title">Settings</div>
        <div class="overview-subtitle">
            Current authenticated and AWS runtime session state.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    user = st.session_state.get("current_user") or {}
    st.write(f"**Signed in user:** {user.get('username', '-')}")
    st.write(f"**Email:** {user.get('email', '-')}")
    st.write(
        "**Live AWS credentials:** "
        + ("Connected" if get_aws_backend_session_status() else "Not connected")
    )

    if aws_connection:
        st.write(f"**AWS account:** {aws_connection.get('account_id', '-')}")

    if scan_data:
        st.write(f"**Active scan:** {scan_data.get('scan_id', '-')}")


# ============================================================
# PHASE 2 AUTHENTICATION GATE
# ============================================================

if not st.session_state.get("access_token"):
    render_auth_screen()
    st.stop()


# ============================================================
# APPLICATION SESSION DEFAULTS
# ============================================================

if "active_page" not in st.session_state:
    st.session_state["active_page"] = "home"


# ============================================================
# APPLICATION SHELL
# ============================================================

# On login/page reload, restore the persisted active snapshot from SQLite.
# This is a read-only DB restore; it never performs AWS discovery automatically.
if not st.session_state.get("active_snapshot_bootstrapped"):
    if not st.session_state.get("aws_scan"):
        restored_active_scan = get_active_scan()
        if restored_active_scan:
            st.session_state["aws_scan"] = restored_active_scan
            st.session_state["aws_connection"] = restored_active_scan.get("account", {})
    st.session_state["active_snapshot_bootstrapped"] = True

aws_connection = st.session_state.get("aws_connection")
scan_data = st.session_state.get("aws_scan")

render_app_sidebar(
    aws_connection=aws_connection,
    scan_data=scan_data,
)

# Sidebar actions can rerun and change session state, so refresh local state.
aws_connection = st.session_state.get("aws_connection")
scan_data = st.session_state.get("aws_scan")
active_page = st.session_state.get("active_page", "home")

# Persisted discovery history remains available from every page.
with st.sidebar:
    if active_page != "chat":
        persisted_scans = get_scan_history()

        if persisted_scans:
            with st.expander(
                "Previous Discovery Scans",
                expanded=False,
            ):
                for item in persisted_scans[:10]:
                    account = item.get("account") or {}
                    account_id = account.get("account_id", "AWS")
                    scan_id = item.get("scan_id")

                    if not scan_id:
                        continue

                    active_marker = " ✓ active" if item.get("is_active") else ""
                    label = f"{account_id} · {str(scan_id)[:8]}{active_marker}"

                    if st.button(
                        label,
                        use_container_width=True,
                        key=f"restore_scan_{scan_id}",
                    ):
                        restored = activate_scan(str(scan_id))

                        if restored:
                            st.session_state["aws_scan"] = restored
                            st.session_state["aws_connection"] = restored.get(
                                "account",
                                {},
                            )
                            st.session_state["active_chat_id"] = None
                            st.session_state["active_chat"] = None
                            st.session_state["active_page"] = "discovery"
                            st.rerun()


# ============================================================
# PAGE ROUTER
# ============================================================

if active_page == "discovery":
    render_discovery_page(
        aws_connection=aws_connection,
        scan_data=scan_data,
    )

elif active_page == "chat":
    if (
        not scan_data
        or scan_data.get("status") != "COMPLETED"
    ):
        st.markdown(
            """
            <div class="overview-title">AWS AI Chat</div>
            <div class="overview-subtitle">
                Chat requires a completed discovery scan.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info(
            "Run or restore a completed AWS discovery scan first."
        )

        if st.button(
            "Open Discovery",
            type="primary",
        ):
            st.session_state[
                "active_page"
            ] = "discovery"

            st.rerun()

    else:
        render_aws_ai_chat(
            aws_connection=(
                aws_connection
                or {}
            ),
            scan_data=scan_data,
        )

elif active_page == "settings":
    render_settings_page(
        aws_connection=aws_connection,
        scan_data=scan_data,
    )

else:
    #
    # Home is also the AWS Connect page.
    #
    render_home_page(
        aws_connection=aws_connection,
        scan_data=scan_data,
    )

