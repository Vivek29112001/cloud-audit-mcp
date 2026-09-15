from pydantic import BaseModel,Field,SecretStr

class AWSCredentials(BaseModel):
    access_key_id : str = Field(
        min_length = 16,
        max_length = 128,
    )
    
    secret_access_key: SecretStr
    
    session_token : SecretStr | None = None
    
    default_region : str = "us-east-1"
    
    def to_environment(self) -> dict[str,str]:
        env = {
            "AWS_ACCESS_KEY_ID": self.access_key_id,
            "AWS_SECRET_ACCESS_KEY": self.secret_access_key.get_secret_value(),
            "AWS_REGION": self.default_region,
            "AWS_DEFAULT_REGION": self.default_region,
        }
        
        if self.session_token:
            env["AWS_SESSION_TOKEN"]=(
                self.session_token.get_secret_value()
            )
            
        return env