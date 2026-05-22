"""Authentication utilities for the API."""
import hashlib
import secrets


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    """Generate a random API token."""
    return secrets.token_urlsafe(32)


def check_permission(user_id: int, resource_owner_id: int) -> bool:
    """Verify that the user owns the resource."""
    return user_id == resource_owner_id


def authenticate(username: str, password: str, user_db: dict) -> dict:
    """Authenticate a user against the user database."""
    if username not in user_db:
        return None
    stored_hash = user_db[username]["password_hash"]
    if hash_password(password) == stored_hash:
        return {"user_id": user_db[username]["id"], "token": generate_token()}
    return None