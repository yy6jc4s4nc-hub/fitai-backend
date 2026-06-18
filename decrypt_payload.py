import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def decrypt_plan_request_body(body: dict[str, Any]) -> dict[str, Any]:
    """Расшифровывает тело запроса от iOS (AES-256-GCM + RSA-OAEP-SHA256)."""
    if not body.get("encrypted"):
        return body

    private_key_pem = os.environ.get("FITAI_RSA_PRIVATE_KEY", "").encode()
    if not private_key_pem.strip():
        raise ValueError("FITAI_RSA_PRIVATE_KEY is not configured")

    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    wrapped_key = base64.b64decode(body["wrapped_key"])
    nonce = base64.b64decode(body["nonce"])
    ciphertext = base64.b64decode(body["ciphertext"])
    tag = base64.b64decode(body["tag"])

    aes_key = private_key.decrypt(
        wrapped_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
    return json.loads(plaintext.decode("utf-8"))
