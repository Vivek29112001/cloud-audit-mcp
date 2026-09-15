class AWSConnectionError(Exception):
    """Base AWS connection error."""


class InvalidAWSCredentialsError(AWSConnectionError):
    """AWS rejected the provided credentials."""


class AWSMCPExecutionError(AWSConnectionError):
    """AWS MCP could not execute the requested operation."""