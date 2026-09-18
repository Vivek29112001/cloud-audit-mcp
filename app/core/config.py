from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name : str = "INAT AWS AUditor"
    app_env: str = "development"
    
    aws_mcp_endpoint: str = "https://aws-mcp.us-east-1.api.aws/mcp"
    aws_mcp_endpoint_region: str = "us-east-1"
    
    mcp_read_only : bool = True
    mcp_timeout : int = 180
    mcp_tool_timeout : int = 300
    
    groq_api_key : str | None = None
    
    groq_intent_model : str = (
        "openai/gpt-oss-20b"
    )
    
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra="ignore",
    )
    

@lru_cache
def get_settings()-> Settings:
    return Settings()

settings = get_settings()