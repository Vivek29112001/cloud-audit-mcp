from dataclasses import dataclass


@dataclass(frozen=True)
class PaginationConfig:
    request_token: str
    response_token: str


PAGINATION_CONFIGS = {
    "NextToken": PaginationConfig(
        request_token="NextToken",
        response_token="NextToken",
    ),

    "Marker": PaginationConfig(
        request_token="Marker",
        response_token="Marker",
    ),
}