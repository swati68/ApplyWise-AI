import base64
import hashlib


class EncryptionService:
    """Small reversible wrapper for local OAuth token storage.

    Production TODO: replace this implementation with envelope encryption backed by
    a managed KMS or a vetted cryptography library. This wrapper keeps token access
    isolated so the storage implementation can be swapped without changing callers.
    """

    def __init__(self, secret_key: str) -> None:
        self.key = hashlib.sha256(secret_key.encode("utf-8")).digest()

    def encrypt(self, value: str | None) -> str | None:
        if value is None or value == "":
            return None

        token_bytes = value.encode("utf-8")
        encrypted_bytes = bytes(
            byte ^ self.key[index % len(self.key)]
            for index, byte in enumerate(token_bytes)
        )
        return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if value is None or value == "":
            return None

        encrypted_bytes = base64.urlsafe_b64decode(value.encode("utf-8"))
        token_bytes = bytes(
            byte ^ self.key[index % len(self.key)]
            for index, byte in enumerate(encrypted_bytes)
        )
        return token_bytes.decode("utf-8")
