import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API_BASE_URL = "http://127.0.0.1:8000/api"

REQUEST_TIMEOUT = 180

RESOURCE_SCAN_TIMEOUT = 600


# ============================================================
# STREAMLIT PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="XYZ AWS Auditor",
    page_icon="🔐",
    layout="wide",
)


# ============================================================
# API ERROR HANDLING
# ============================================================

def get_error_detail(
    response: requests.Response,
    default_message: str,
) -> str:
    """
    Safely extract backend API error message.
    """

    try:
        payload = response.json()

    except ValueError:
        return default_message

    detail = payload.get("detail")

    return (
        str(detail)
        if detail
        else default_message
    )


# ============================================================
# AWS VERIFY API
# ============================================================

def verify_aws_account(
    payload: dict,
) -> dict | None:
    """
    Verify AWS credentials through FastAPI -> MCP -> AWS.
    """

    try:

        with st.spinner(
            "Verifying AWS credentials through MCP..."
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
# AWS REGION DISCOVERY API
# ============================================================

def discover_aws_regions(
    credentials: dict,
) -> dict | None:
    """
    Discover AWS Regions dynamically through MCP.
    """

    try:

        with st.spinner(
            "Discovering AWS Regions through MCP..."
        ):

            response = requests.post(
                f"{API_BASE_URL}/aws/regions",
                json=credentials,
                timeout=REQUEST_TIMEOUT,
            )

        if response.status_code != 200:

            st.error(
                get_error_detail(
                    response,
                    "Unable to discover AWS Regions.",
                )
            )

            return None

        return response.json()

    except requests.RequestException as exc:

        st.error(
            f"AWS Region discovery failed: {exc}"
        )

        return None


# ============================================================
# AWS AVAILABILITY ZONE DISCOVERY API
# ============================================================

def discover_aws_zones(
    credentials: dict,
) -> dict | None:
    """
    Discover Availability Zones dynamically.

    Backend itself re-discovers enabled Regions and then
    fetches zones for those Regions.
    """

    try:

        with st.spinner(
            "Discovering AWS Availability Zones through MCP..."
        ):

            response = requests.post(
                f"{API_BASE_URL}/aws/zones",
                json=credentials,
                timeout=REQUEST_TIMEOUT,
            )

        if response.status_code != 200:

            st.error(
                get_error_detail(
                    response,
                    "Unable to discover AWS Availability Zones.",
                )
            )

            return None

        return response.json()

    except requests.RequestException as exc:

        st.error(
            "AWS Availability Zone "
            f"discovery failed: {exc}"
        )

        return None


# ============================================================
# AWS RESOURCE DISCOVERY API
# ============================================================

def discover_aws_resources(
    credentials: dict,
    enabled_regions: list[str],
) -> dict | None:
    """
    Discover actual AWS resources.

    enabled_regions come from our previous dynamic
    Region discovery result.
    """

    payload = {
        **credentials,
        "enabled_regions": enabled_regions,
    }

    try:

        with st.spinner(
            "Discovering AWS resources through MCP..."
        ):

            response = requests.post(
                (
                    f"{API_BASE_URL}"
                    "/aws/resources/discover"
                ),
                json=payload,
                timeout=RESOURCE_SCAN_TIMEOUT,
            )

        if response.status_code != 200:

            st.error(
                get_error_detail(
                    response,
                    "Unable to discover AWS resources.",
                )
            )

            return None

        return response.json()

    except requests.RequestException as exc:

        st.error(
            f"AWS resource discovery failed: {exc}"
        )

        return None


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def clear_aws_session() -> None:
    """
    Remove AWS account and scan information
    from current Streamlit session.
    """

    for key in (
        "aws_connection",
        "aws_credentials",
        "aws_regions",
        "aws_zones",
        "aws_resources",
    ):
        st.session_state.pop(
            key,
            None,
        )


def clear_scan_results() -> None:
    """
    Remove previous scan data when a new AWS
    account is connected.
    """

    for key in (
        "aws_regions",
        "aws_zones",
        "aws_resources",
    ):
        st.session_state.pop(
            key,
            None,
        )


# ============================================================
# HELPERS
# ============================================================

def get_enabled_regions(
    region_data: dict | None,
) -> list[str]:
    """
    Extract enabled Region names from
    AWS Region discovery result.
    """

    if not region_data:
        return []

    return [
        region["region_name"]
        for region
        in region_data.get(
            "regions",
            [],
        )
        if (
            region.get("enabled") is True
            and region.get("region_name")
        )
    ]


def get_disabled_regions(
    region_data: dict | None,
) -> list[dict]:
    """
    Return Regions which are not enabled
    for this AWS account.
    """

    if not region_data:
        return []

    return [
        region
        for region
        in region_data.get(
            "regions",
            [],
        )
        if region.get("enabled") is not True
    ]


# ============================================================
# HEADER
# ============================================================

st.title(
    "XYZ AWS Cloud Auditor"
)

st.caption(
    "Dynamic AWS infrastructure discovery "
    "through AWS Managed MCP Server."
)


# ============================================================
# AWS CONNECTION FORM
# ============================================================

with st.form(
    "aws_connection_form"
):

    st.subheader(
        "Connect AWS Account"
    )

    access_key_id = st.text_input(
        "AWS Access Key ID",
        placeholder="AKIA...",
    )

    secret_access_key = st.text_input(
        "AWS Secret Access Key",
        type="password",
    )

    session_token = st.text_area(
        "AWS Session Token (optional)",
        height=100,
    )

    connect = st.form_submit_button(
        "Verify AWS Account",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# VERIFY AWS ACCOUNT
# ============================================================

if connect:

    if (
        not access_key_id
        or not secret_access_key
    ):

        st.error(
            "Access Key ID and Secret "
            "Access Key are required."
        )

    else:

        credentials_payload = {
            "access_key_id": (
                access_key_id.strip()
            ),
            "secret_access_key": (
                secret_access_key
            ),
            "session_token": (
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

            # Remove previous account scan data.
            clear_scan_results()

            # Save verified identity.
            st.session_state[
                "aws_connection"
            ] = verification_data

            # Credentials remain only in current
            # Streamlit session for subsequent MCP calls.
            st.session_state[
                "aws_credentials"
            ] = credentials_payload

            st.success(
                "AWS account verified successfully."
            )

            st.rerun()


# ============================================================
# CURRENT AWS CONNECTION
# ============================================================

aws_connection = (
    st.session_state.get(
        "aws_connection"
    )
)


if aws_connection:

    st.divider()

    st.subheader(
        "Verified AWS Account"
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:

        st.metric(
            "Cloud Provider",
            aws_connection.get(
                "provider",
                "AWS",
            ),
        )

    with col2:

        st.metric(
            "AWS Account",
            aws_connection.get(
                "account_id",
                "-",
            ),
        )

    with col3:

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


    # ========================================================
    # SCAN CONTROLS
    # ========================================================

    action_col1, action_col2 = (
        st.columns(
            [3, 1]
        )
    )

    with action_col1:

        run_scan_clicked = st.button(
            "Start AWS Infrastructure Scan",
            type="primary",
            use_container_width=True,
        )

    with action_col2:

        disconnect_clicked = st.button(
            "Disconnect",
            use_container_width=True,
        )


    # ========================================================
    # DISCONNECT
    # ========================================================

    if disconnect_clicked:

        clear_aws_session()

        st.rerun()


    # ========================================================
    # FULL AWS INFRASTRUCTURE SCAN
    # ========================================================

    if run_scan_clicked:

        credentials = (
            st.session_state.get(
                "aws_credentials"
            )
        )

        if not credentials:

            st.error(
                "AWS credentials are no longer "
                "available in this session. "
                "Please verify the account again."
            )

        else:

            st.divider()

            st.subheader(
                "AWS Infrastructure Scan"
            )


            # =================================================
            # STEP 1 - REGION DISCOVERY
            # =================================================

            st.write(
                "### 1. Region Discovery"
            )

            region_data = (
                discover_aws_regions(
                    credentials
                )
            )

            if not region_data:

                st.error(
                    "AWS infrastructure scan "
                    "stopped because Region "
                    "discovery failed."
                )

                st.stop()

            st.session_state[
                "aws_regions"
            ] = region_data

            enabled_regions = (
                get_enabled_regions(
                    region_data
                )
            )

            st.success(
                "AWS Region discovery completed."
            )

            st.write(
                f"Enabled Regions discovered: "
                f"{len(enabled_regions)}"
            )


            # =================================================
            # VALIDATE ENABLED REGIONS
            # =================================================

            if not enabled_regions:

                st.warning(
                    "No enabled AWS Regions "
                    "were returned for this account."
                )

                st.stop()


            # =================================================
            # STEP 2 - AVAILABILITY ZONES
            # =================================================

            st.write(
                "### 2. Availability Zone Discovery"
            )

            zone_data = (
                discover_aws_zones(
                    credentials
                )
            )

            if zone_data:

                st.session_state[
                    "aws_zones"
                ] = zone_data

                st.success(
                    "AWS Availability Zone "
                    "discovery completed."
                )

                st.write(
                    "Availability Zones discovered: "
                    f"{zone_data.get('total_zones', 0)}"
                )

            else:

                st.session_state.pop(
                    "aws_zones",
                    None,
                )

                st.warning(
                    "Availability Zone discovery "
                    "failed. Resource discovery "
                    "will continue."
                )


            # =================================================
            # STEP 3 - RESOURCE DISCOVERY
            # =================================================

            st.write(
                "### 3. Resource Discovery"
            )

            resource_data = (
                discover_aws_resources(
                    credentials=credentials,
                    enabled_regions=(
                        enabled_regions
                    ),
                )
            )

            if not resource_data:

                st.error(
                    "AWS resource discovery "
                    "failed."
                )

                st.stop()

            st.session_state[
                "aws_resources"
            ] = resource_data

            st.success(
                "AWS infrastructure scan "
                "completed successfully."
            )

            st.rerun()


# ============================================================
# LOAD CURRENT SCAN RESULTS
# ============================================================

region_data = (
    st.session_state.get(
        "aws_regions"
    )
)

zone_data = (
    st.session_state.get(
        "aws_zones"
    )
)

resource_data = (
    st.session_state.get(
        "aws_resources"
    )
)


# ============================================================
# SCAN RESULTS
# ============================================================

if (
    region_data
    or zone_data
    or resource_data
):

    st.divider()

    st.header(
        "AWS Scan Results"
    )


# ============================================================
# REGION SUMMARY
# ============================================================

if region_data:

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


    enabled_region_rows = [
        region
        for region
        in region_data.get(
            "regions",
            [],
        )
        if region.get(
            "enabled"
        ) is True
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


    disabled_region_rows = (
        get_disabled_regions(
            region_data
        )
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
                "No disabled AWS Regions "
                "were returned."
            )


# ============================================================
# AVAILABILITY ZONE RESULTS
# ============================================================

if zone_data:

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
            "No Availability Zones "
            "were returned."
        )


# ============================================================
# RESOURCE INVENTORY RESULTS
# ============================================================

if resource_data:

    st.divider()

    st.subheader(
        "Infrastructure Inventory"
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


    used_regions = (
        resource_data.get(
            "used_regions",
            [],
        )
    )

    with inventory_col2:

        st.metric(
            "Used Regions",
            len(
                used_regions
            ),
        )


    detected_services = (
        resource_data.get(
            "detected_services",
            [],
        )
    )

    with inventory_col3:

        st.metric(
            "Detected Services",
            len(
                detected_services
            ),
        )


    # ========================================================
    # USED REGIONS
    # ========================================================

    st.subheader(
        "Regions Containing Resources"
    )

    if used_regions:

        used_region_rows = [
            {
                "region": region
            }
            for region
            in used_regions
        ]

        st.dataframe(
            used_region_rows,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No Regions containing "
            "resources were detected."
        )


    # ========================================================
    # DETECTED SERVICES
    # ========================================================

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
            "No AWS services with "
            "discoverable resources "
            "were detected."
        )


    # ========================================================
    # RESOURCE LIST
    # ========================================================

    resources = (
        resource_data.get(
            "resources",
            [],
        )
    )

    st.subheader(
        "Discovered AWS Resources"
    )

    if resources:

        # Avoid rendering potentially large nested
        # property structures in main table.
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


    # ========================================================
    # SCAN WARNINGS
    # ========================================================

    warnings = (
        resource_data.get(
            "warnings",
            [],
        )
    )

    if warnings:

        st.divider()

        st.subheader(
            "Scan Warnings"
        )

        st.warning(
            "The AWS scan completed "
            "with one or more warnings."
        )

        for warning in warnings:

            st.write(
                f"• {warning}"
            )


# ============================================================
# SCAN STATUS
# ============================================================

if aws_connection:

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
            "stage": "Used Region Detection",
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
# INFORMATION
# ============================================================

if aws_connection and not resource_data:

    st.info(
        "Start the AWS Infrastructure Scan to "
        "dynamically discover Regions, Availability "
        "Zones, resources, used Regions and detected "
        "AWS services."
    )