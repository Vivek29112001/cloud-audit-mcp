from pydantic import SecretStr
from app.providers.aws.credential_crypto import AWSCredentialCipher
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.assume_role import AWSAssumeRoleService

def main():
    raw=AWSCredentials(access_key_id="A"*20,secret_access_key=SecretStr("secret-value"),session_token=SecretStr("token-value"),default_region="ap-south-1")
    cipher=AWSCredentialCipher(); encrypted=cipher.encrypt(raw); restored=cipher.decrypt(encrypted)
    assert "secret-value" not in encrypted
    assert restored.access_key_id==raw.access_key_id
    assert restored.secret_access_key.get_secret_value()=="secret-value"
    assert restored.session_token.get_secret_value()=="token-value"
    nested={"response":{"Credentials":{"AccessKeyId":"B"*20,"SecretAccessKey":"s","SessionToken":"t","Expiration":"2026-09-23T12:00:00Z"}}}
    assert AWSAssumeRoleService._find_credentials(nested)["SessionToken"]=="t"
    assert AWSAssumeRoleService._parse_expiration("2026-09-23T12:00:00Z") is not None
    print("automatic authentication tests passed")
if __name__=="__main__":main()
