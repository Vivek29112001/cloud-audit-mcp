def build_iam_inventory_script() -> str:

    return r'''
result = {
    "account_summary": {},
    "password_policy": None,
    "users": [],
    "roles": [],
    "warnings": []
}

iam_region = "us-east-1"


#
# ---------------------------------------
# ACCOUNT SUMMARY
# ---------------------------------------
#

try:

    summary = await call_boto3(
        service_name="iam",
        operation_name="GetAccountSummary",
        region_name=iam_region,
        params={}
    )

    result[
        "account_summary"
    ] = summary.get(
        "SummaryMap",
        {}
    )

except Exception as exc:

    result[
        "warnings"
    ].append(
        "GetAccountSummary failed: "
        + str(exc)
    )


#
# ---------------------------------------
# ACCOUNT PASSWORD POLICY
# ---------------------------------------
#

try:

    response = await call_boto3(
        service_name="iam",
        operation_name="GetAccountPasswordPolicy",
        region_name=iam_region,
        params={}
    )

    policy = response.get(
        "PasswordPolicy",
        {}
    )

    result[
        "password_policy"
    ] = {
        "minimum_password_length":
            policy.get(
                "MinimumPasswordLength"
            ),

        "require_symbols":
            policy.get(
                "RequireSymbols"
            ),

        "require_numbers":
            policy.get(
                "RequireNumbers"
            ),

        "require_uppercase_characters":
            policy.get(
                "RequireUppercaseCharacters"
            ),

        "require_lowercase_characters":
            policy.get(
                "RequireLowercaseCharacters"
            ),

        "allow_users_to_change_password":
            policy.get(
                "AllowUsersToChangePassword"
            ),

        "expire_passwords":
            policy.get(
                "ExpirePasswords"
            ),

        "max_password_age":
            policy.get(
                "MaxPasswordAge"
            ),

        "password_reuse_prevention":
            policy.get(
                "PasswordReusePrevention"
            ),

        "hard_expiry":
            policy.get(
                "HardExpiry"
            )
    }

except Exception as exc:

    result[
        "warnings"
    ].append(
        "GetAccountPasswordPolicy "
        "failed or policy not configured: "
        + str(exc)
    )


#
# ---------------------------------------
# USERS
# ---------------------------------------
#

marker = None

while True:

    params = {
        "MaxItems": 1000
    }

    if marker:
        params["Marker"] = marker

    response = await call_boto3(
        service_name="iam",
        operation_name="ListUsers",
        region_name=iam_region,
        params=params
    )

    for user in response.get(
        "Users",
        []
    ):

        user_name = user.get(
            "UserName"
        )

        user_result = {
            "user_name":
                user_name,

            "user_id":
                user.get(
                    "UserId"
                ),

            "arn":
                user.get(
                    "Arn"
                ),

            "path":
                user.get(
                    "Path"
                ),

            "create_date":
                (
                    str(
                        user.get(
                            "CreateDate"
                        )
                    )
                    if user.get(
                        "CreateDate"
                    )
                    else None
                ),

            "password_last_used":
                (
                    str(
                        user.get(
                            "PasswordLastUsed"
                        )
                    )
                    if user.get(
                        "PasswordLastUsed"
                    )
                    else None
                ),

            "mfa_devices": [],

            "access_keys": [],

            "groups": [],

            "attached_policies": [],

            "inline_policy_names": []
        }


        #
        # MFA DEVICES
        #

        try:

            mfa_marker = None

            while True:

                mfa_params = {
                    "UserName":
                        user_name,

                    "MaxItems": 1000
                }

                if mfa_marker:
                    mfa_params[
                        "Marker"
                    ] = mfa_marker

                mfa_response = await call_boto3(
                    service_name="iam",
                    operation_name="ListMFADevices",
                    region_name=iam_region,
                    params=mfa_params
                )

                for device in mfa_response.get(
                    "MFADevices",
                    []
                ):

                    user_result[
                        "mfa_devices"
                    ].append({
                        "serial_number":
                            device.get(
                                "SerialNumber"
                            ),

                        "enable_date":
                            (
                                str(
                                    device.get(
                                        "EnableDate"
                                    )
                                )
                                if device.get(
                                    "EnableDate"
                                )
                                else None
                            )
                    })

                if not mfa_response.get(
                    "IsTruncated"
                ):
                    break

                mfa_marker = (
                    mfa_response.get(
                        "Marker"
                    )
                )

        except Exception as exc:

            result[
                "warnings"
            ].append(
                "ListMFADevices failed "
                "for "
                + str(user_name)
                + ": "
                + str(exc)
            )


        #
        # ACCESS KEYS
        #

        try:

            key_marker = None

            while True:

                key_params = {
                    "UserName":
                        user_name,

                    "MaxItems": 1000
                }

                if key_marker:
                    key_params[
                        "Marker"
                    ] = key_marker

                key_response = await call_boto3(
                    service_name="iam",
                    operation_name="ListAccessKeys",
                    region_name=iam_region,
                    params=key_params
                )

                for key in key_response.get(
                    "AccessKeyMetadata",
                    []
                ):

                    user_result[
                        "access_keys"
                    ].append({
                        "access_key_id":
                            key.get(
                                "AccessKeyId"
                            ),

                        "status":
                            key.get(
                                "Status"
                            ),

                        "create_date":
                            (
                                str(
                                    key.get(
                                        "CreateDate"
                                    )
                                )
                                if key.get(
                                    "CreateDate"
                                )
                                else None
                            )
                    })

                if not key_response.get(
                    "IsTruncated"
                ):
                    break

                key_marker = (
                    key_response.get(
                        "Marker"
                    )
                )

        except Exception as exc:

            result[
                "warnings"
            ].append(
                "ListAccessKeys failed "
                "for "
                + str(user_name)
                + ": "
                + str(exc)
            )


        #
        # GROUP MEMBERSHIP
        #

        try:

            group_response = await call_boto3(
                service_name="iam",
                operation_name="ListGroupsForUser",
                region_name=iam_region,
                params={
                    "UserName":
                        user_name
                }
            )

            user_result[
                "groups"
            ] = [
                group.get(
                    "GroupName"
                )
                for group
                in group_response.get(
                    "Groups",
                    []
                )
                if group.get(
                    "GroupName"
                )
            ]

        except Exception as exc:

            result[
                "warnings"
            ].append(
                "ListGroupsForUser failed "
                "for "
                + str(user_name)
                + ": "
                + str(exc)
            )


        #
        # ATTACHED USER POLICIES
        #

        try:

            attached = await call_boto3(
                service_name="iam",
                operation_name=(
                    "ListAttachedUserPolicies"
                ),
                region_name=iam_region,
                params={
                    "UserName":
                        user_name
                }
            )

            user_result[
                "attached_policies"
            ] = [
                policy.get(
                    "PolicyArn"
                )
                for policy
                in attached.get(
                    "AttachedPolicies",
                    []
                )
                if policy.get(
                    "PolicyArn"
                )
            ]

        except Exception as exc:

            result[
                "warnings"
            ].append(
                "ListAttachedUserPolicies "
                "failed for "
                + str(user_name)
                + ": "
                + str(exc)
            )


        #
        # INLINE USER POLICIES
        #

        try:

            policies = await call_boto3(
                service_name="iam",
                operation_name=(
                    "ListUserPolicies"
                ),
                region_name=iam_region,
                params={
                    "UserName":
                        user_name
                }
            )

            user_result[
                "inline_policy_names"
            ] = policies.get(
                "PolicyNames",
                []
            )

        except Exception as exc:

            result[
                "warnings"
            ].append(
                "ListUserPolicies failed "
                "for "
                + str(user_name)
                + ": "
                + str(exc)
            )


        result[
            "users"
        ].append(
            user_result
        )

    if not response.get(
        "IsTruncated"
    ):
        break

    marker = response.get(
        "Marker"
    )


#
# ---------------------------------------
# ROLES
# ---------------------------------------
#

marker = None

while True:

    params = {
        "MaxItems": 1000
    }

    if marker:
        params[
            "Marker"
        ] = marker

    response = await call_boto3(
        service_name="iam",
        operation_name="ListRoles",
        region_name=iam_region,
        params=params
    )

    for role in response.get(
        "Roles",
        []
    ):

        role_name = role.get(
            "RoleName"
        )

        role_result = {
            "role_name":
                role_name,

            "role_id":
                role.get(
                    "RoleId"
                ),

            "arn":
                role.get(
                    "Arn"
                ),

            "path":
                role.get(
                    "Path"
                ),

            "create_date":
                (
                    str(
                        role.get(
                            "CreateDate"
                        )
                    )
                    if role.get(
                        "CreateDate"
                    )
                    else None
                ),

            "max_session_duration":
                role.get(
                    "MaxSessionDuration"
                ),

            "attached_policies": [],

            "inline_policy_names": []
        }

        try:

            attached = await call_boto3(
                service_name="iam",
                operation_name=(
                    "ListAttachedRolePolicies"
                ),
                region_name=iam_region,
                params={
                    "RoleName":
                        role_name
                }
            )

            role_result[
                "attached_policies"
            ] = [
                policy.get(
                    "PolicyArn"
                )
                for policy
                in attached.get(
                    "AttachedPolicies",
                    []
                )
                if policy.get(
                    "PolicyArn"
                )
            ]

        except Exception as exc:

            result[
                "warnings"
            ].append(
                "ListAttachedRolePolicies "
                "failed for "
                + str(role_name)
                + ": "
                + str(exc)
            )

        try:

            inline = await call_boto3(
                service_name="iam",
                operation_name=(
                    "ListRolePolicies"
                ),
                region_name=iam_region,
                params={
                    "RoleName":
                        role_name
                }
            )

            role_result[
                "inline_policy_names"
            ] = inline.get(
                "PolicyNames",
                []
            )

        except Exception as exc:

            result[
                "warnings"
            ].append(
                "ListRolePolicies failed "
                "for "
                + str(role_name)
                + ": "
                + str(exc)
            )

        result[
            "roles"
        ].append(
            role_result
        )

    if not response.get(
        "IsTruncated"
    ):
        break

    marker = response.get(
        "Marker"
    )


result
'''