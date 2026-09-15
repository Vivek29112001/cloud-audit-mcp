import requests
import streamlit as st


API_BASE_URL = "http://127.0.0.1:8000/api"


st.set_page_config(
    page_title="XYZ AWS Auditor",
    page_icon="🔐",
    layout="wide",
)


st.title("XYZ AWS Cloud Auditor")

st.caption(
    "Dynamic AWS infrastructure discovery "
    "through AWS Managed MCP Server."
)


with st.form("aws_connection_form"):

    st.subheader("Connect AWS Account")

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
        use_container_width=True,
    )


if connect:

    if not access_key_id or not secret_access_key:
        st.error(
            "Access Key ID and Secret Access Key are required."
        )

    else:
        payload = {
            "access_key_id": access_key_id,
            "secret_access_key": secret_access_key,
            "session_token": session_token or None,
        }

        try:
            with st.spinner(
                "Verifying AWS credentials through MCP..."
            ):
                response = requests.post(
                    f"{API_BASE_URL}/aws/verify",
                    json=payload,
                    timeout=180,
                )

            if response.status_code == 200:

                data = response.json()

                st.session_state[
                    "aws_connection"
                ] = data

                st.success(
                    "AWS account verified successfully."
                )

                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Cloud Provider",
                        data["provider"],
                    )

                    st.metric(
                        "AWS Account",
                        data["account_id"],
                    )

                with col2:
                    st.metric(
                        "Status",
                        data["connection_status"],
                    )

                st.subheader("Caller Identity")

                st.code(
                    data["arn"],
                    language=None,
                )

            else:

                detail = response.json().get(
                    "detail",
                    "Unable to verify AWS account.",
                )

                st.error(detail)

        except requests.RequestException as exc:
            st.error(
                f"Backend connection failed: {exc}"
            )