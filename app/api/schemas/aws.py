from pydantic import BaseModel, Field , SecretStr

class AWSVerifyRequest(BaseModel):
    access_key_id: str = Field(
        min_length=16,
        max_length=128,
    )
    
    secret_access_key: SecretStr
    
    session_token: SecretStr | None = None
    

class AWSVerifyResponse(BaseModel):
    provider:str
    account_id:str
    arn:str
    user_id:str
    connection_status:str