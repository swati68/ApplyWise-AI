import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if stored_hash is None:
        return False

    try:
        algorithm, iterations, salt, expected_hash = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != PASSWORD_ALGORITHM:
        return False

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(password_hash, expected_hash)


def create_session_token(
    *,
    user_id: UUID,
    secret_key: str,
    expires_delta: timedelta,
) -> str:
    expires_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": str(user_id),
        "exp": int(expires_at.timestamp()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded_payload = _base64_url_encode(payload_bytes)
    signature = _sign(encoded_payload, secret_key)
    return f"{encoded_payload}.{signature}"


def parse_session_token(token: str, secret_key: str) -> UUID | None:
    try:
        encoded_payload, provided_signature = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign(encoded_payload, secret_key)
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    try:
        payload = json.loads(_base64_url_decode(encoded_payload))
        expires_at = int(payload["exp"])
        user_id = UUID(payload["sub"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    if expires_at <= int(datetime.now(UTC).timestamp()):
        return None

    return user_id


def _sign(encoded_payload: str, secret_key: str) -> str:
    signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _base64_url_encode(signature)


def _base64_url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _base64_url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
