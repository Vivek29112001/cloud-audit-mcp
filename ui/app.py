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
# FULL AWS INFRASTRUCTURE SCAN API
# ============================================================

def run_aws_scan(
    credentials: dict,
) -> dict | None:
    """
    Run the complete AWS infrastructure scan.

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
            "Scanning AWS infrastructure through "
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
                    "AWS infrastructure scan failed.",
                )
            )
            return None

        return response.json()

    except requests.RequestException as exc:
        st.error(
            f"AWS infrastructure scan failed: {exc}"
        )
        return None


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


def render_ec2_deep_scan(
    ec2_data: dict,
) -> None:
    """
    Render EC2/VPC/EBS deep scan results.
    """

    instances = ec2_data.get(
        "instances",
        [],
    )

    security_groups = ec2_data.get(
        "security_groups",
        [],
    )

    volumes = ec2_data.get(
        "volumes",
        [],
    )

    subnets = ec2_data.get(
        "subnets",
        [],
    )

    route_tables = ec2_data.get(
        "route_tables",
        [],
    )

    st.markdown(
        "### EC2 / VPC"
    )

    metric_col1, metric_col2, metric_col3 = (
        st.columns(3)
    )

    with metric_col1:
        st.metric(
            "EC2 Instances",
            len(instances),
        )

    with metric_col2:
        st.metric(
            "Security Groups",
            len(security_groups),
        )

    with metric_col3:
        st.metric(
            "EBS Volumes",
            len(volumes),
        )

    network_col1, network_col2 = (
        st.columns(2)
    )

    with network_col1:
        st.metric(
            "Subnets",
            len(subnets),
        )

    with network_col2:
        st.metric(
            "Route Tables",
            len(route_tables),
        )

    with st.expander(
        "EC2 Instances",
        expanded=True,
    ):
        if instances:
            st.dataframe(
                instances,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No EC2 instances were returned."
            )

    with st.expander(
        "Security Groups"
    ):
        if security_groups:
            st.json(
                security_groups
            )
        else:
            st.info(
                "No security groups were returned."
            )

    with st.expander(
        "EBS Volumes"
    ):
        if volumes:
            st.dataframe(
                volumes,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No EBS volumes were returned."
            )

    with st.expander(
        "Subnets"
    ):
        if subnets:
            st.dataframe(
                subnets,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No subnets were returned."
            )

    with st.expander(
        "Route Tables"
    ):
        if route_tables:
            st.json(
                route_tables
            )
        else:
            st.info(
                "No route tables were returned."
            )

    ec2_warnings = ec2_data.get(
        "warnings",
        [],
    )

    if ec2_warnings:
        with st.expander(
            "EC2 Collector Warnings"
        ):
            for warning in ec2_warnings:
                st.warning(
                    warning
                )


def render_generic_deep_service(
    service_name: str,
    service_data,
) -> None:
    """
    Generic renderer for future S3/RDS/IAM/Lambda collectors.
    """

    st.markdown(
        f"### {service_name.upper()}"
    )

    if isinstance(
        service_data,
        dict,
    ):
        st.json(
            service_data
        )
    else:
        st.write(
            service_data
        )


def render_deep_scan(
    deep_scan_data: dict | None,
) -> None:
    """
    Render service-specific detailed scan results.
    """

    if not deep_scan_data:
        return

    st.divider()

    st.subheader(
        "Deep Configuration Scan"
    )

    services = deep_scan_data.get(
        "services",
        {},
    )

    if not services:
        st.info(
            "No service-specific deep scan results are available yet."
        )
        return

    for service_name, service_data in services.items():
        if (
            service_name.lower()
            == "ec2"
            and isinstance(
                service_data,
                dict,
            )
        ):
            render_ec2_deep_scan(
                service_data
            )
        else:
            render_generic_deep_service(
                service_name,
                service_data,
            )


def render_scan_status(
    aws_connection: dict | None,
    scan_data: dict | None,
    region_data: dict | None,
    zone_data: dict | None,
    resource_data: dict | None,
    deep_scan_data: dict | None,
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

    deep_services = (
        deep_scan_data.get(
            "services",
            {},
        )
        if deep_scan_data
        else {}
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
            "stage": "Deep Configuration Scan",
            "status": (
                "Completed"
                if deep_services
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
# HEADER
# ============================================================

st.title(
    "XYZ AWS Cloud Auditor"
)

st.caption(
    "Dynamic AWS infrastructure discovery through "
    "the official AWS Managed MCP Server."
)

st.info(
    "AWS scanning is orchestrated by the backend. "
    "The UI does not directly call AWS APIs, boto3, "
    "or AWS CLI commands."
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
            "Access Key ID and Secret Access Key "
            "are required."
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

        verification_data = verify_aws_account(
            credentials_payload
        )

        if verification_data:
            # A newly verified account invalidates
            # results from any previous AWS account.
            clear_scan_results()

            st.session_state[
                "aws_connection"
            ] = verification_data

            # For the POC, credentials remain only in the
            # active Streamlit session. They are not rendered
            # back to the user and should not be logged.
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

aws_connection = st.session_state.get(
    "aws_connection"
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
        credentials = st.session_state.get(
            "aws_credentials"
        )

        if not credentials:
            st.error(
                "AWS credentials are no longer "
                "available in this session. "
                "Please verify the account again."
            )

        else:
            scan_data = run_aws_scan(
                credentials
            )

            if scan_data:
                st.session_state[
                    "aws_scan"
                ] = scan_data

                if (
                    scan_data.get(
                        "status"
                    )
                    == "COMPLETED"
                ):
                    st.success(
                        "AWS infrastructure scan "
                        "completed successfully."
                    )
                else:
                    st.error(
                        "AWS infrastructure scan "
                        "did not complete successfully."
                    )

                st.rerun()


# ============================================================
# LOAD CURRENT SCAN
# ============================================================

scan_data = st.session_state.get(
    "aws_scan"
)

region_data = None
zone_data = None
resource_data = None
deep_scan_data = None

if scan_data:
    region_data = scan_data.get(
        "regions"
    )

    zone_data = scan_data.get(
        "zones"
    )

    resource_data = scan_data.get(
        "resources"
    )

    deep_scan_data = scan_data.get(
        "deep_scan"
    )


# ============================================================
# OVERALL SCAN SUMMARY
# ============================================================

if scan_data:
    st.divider()

    st.header(
        "AWS Infrastructure Scan"
    )

    status_value = scan_data.get(
        "status",
        "UNKNOWN",
    )

    account = scan_data.get(
        "account",
        {},
    ) or {}

    summary = scan_data.get(
        "summary",
        {},
    ) or {}

    scan_col1, scan_col2, scan_col3 = (
        st.columns(3)
    )

    with scan_col1:
        st.metric(
            "Scan Status",
            status_value,
        )

    with scan_col2:
        st.metric(
            "AWS Account",
            account.get(
                "account_id",
                "-",
            ),
        )

    with scan_col3:
        st.metric(
            "Resources",
            summary.get(
                "discovered_resources",
                0,
            ),
        )

    region_col1, region_col2, region_col3 = (
        st.columns(3)
    )

    with region_col1:
        st.metric(
            "Enabled Regions",
            summary.get(
                "enabled_regions",
                0,
            ),
        )

    with region_col2:
        st.metric(
            "Used Regions",
            summary.get(
                "used_regions",
                0,
            ),
        )

    with region_col3:
        st.metric(
            "Availability Zones",
            summary.get(
                "availability_zones",
                0,
            ),
        )

    service_col1, service_col2 = (
        st.columns(2)
    )

    with service_col1:
        st.metric(
            "Detected Services",
            summary.get(
                "detected_services",
                0,
            ),
        )

    with service_col2:
        st.metric(
            "Deep Scanned Services",
            summary.get(
                "deep_scanned_services",
                0,
            ),
        )

    scan_id = scan_data.get(
        "scan_id"
    )

    if scan_id:
        st.caption(
            f"Scan ID: {scan_id}"
        )

    started_at = scan_data.get(
        "started_at"
    )

    completed_at = scan_data.get(
        "completed_at"
    )

    if started_at or completed_at:
        time_col1, time_col2 = (
            st.columns(2)
        )

        with time_col1:
            st.caption(
                f"Started: {started_at or '-'}"
            )

        with time_col2:
            st.caption(
                f"Completed: {completed_at or '-'}"
            )


# ============================================================
# DETAILED SCAN RESULTS
# ============================================================

render_region_results(
    region_data
)

render_zone_results(
    zone_data
)

render_resource_inventory(
    resource_data
)

render_deep_scan(
    deep_scan_data
)


# ============================================================
# SCAN WARNINGS
# ============================================================

warnings = (
    scan_data.get(
        "warnings",
        [],
    )
    if scan_data
    else []
)

render_scan_warnings(
    warnings
)


# ============================================================
# SCAN STATUS
# ============================================================

render_scan_status(
    aws_connection=aws_connection,
    scan_data=scan_data,
    region_data=region_data,
    zone_data=zone_data,
    resource_data=resource_data,
    deep_scan_data=deep_scan_data,
)


# ============================================================
# INFORMATION
# ============================================================

if aws_connection and not scan_data:
    st.info(
        "Start the AWS Infrastructure Scan to dynamically "
        "discover Regions, Availability Zones, resources, "
        "used Regions, detected AWS services and available "
        "deep configuration inventory through the official "
        "AWS Managed MCP Server."
    )

elif not aws_connection:
    st.info(
        "Verify an AWS account to begin dynamic "
        "AWS infrastructure discovery."
    )
