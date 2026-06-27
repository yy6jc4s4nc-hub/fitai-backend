import os

import jwt
from jwt import PyJWKClient

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
_jwks_client = PyJWKClient(APPLE_JWKS_URL)


def verify_apple_identity_token(identity_token: str) -> dict:
    client_id = os.environ.get("APPLE_CLIENT_ID", "com.aleksey.fitai.FitAI")
    signing_key = _jwks_client.get_signing_key_from_jwt(identity_token)
    return jwt.decode(
        identity_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer="https://appleid.apple.com",
    )
