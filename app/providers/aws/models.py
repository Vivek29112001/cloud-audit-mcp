from pydantic import BaseModel

class AWSIdentity(BaseModel):
    account_id: str
    arn: str
    user_id: str
    
    provider: str = "AWS"
    connection_status: str = "VERIFIED"
    
    