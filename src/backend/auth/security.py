"""
MedBrief AI — Security & JWT Utilities
Step 4: Authentication + RBAC

Provides cryptographically signed JWT token generation, verification,
and audit logging helpers.
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from sqlalchemy.orm import Session
from src.backend.db.models import AuditEvent, generate_uuid, utc_now

# Environment settings
JWT_SECRET = os.getenv("JWT_SECRET", "medbrief-ai-production-grade-hmac-key-2026-secure-clinical")
JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with a unique cryptographic salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored salt$key hash."""
    if not hashed or "$" not in hashed:
        return False
    try:
        salt, key_hex = hashed.split("$", 1)
        expected_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return secrets.compare_digest(key_hex, expected_key.hex())
    except Exception:
        return False



def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT access token with standard claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })

    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Returns decoded claims dictionary or None if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def log_auth_audit_event(
    db: Session,
    user_id: Optional[str],
    action: str,
    resource_type: str = "AUTH",
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Safely append an authentication or access-control event to the audit_events table.
    Swallows errors to avoid blocking auth flows if audit write encounters a transient issue.
    """
    try:
        meta_json = json.dumps(metadata) if metadata else None
        event = AuditEvent(
            id=generate_uuid(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=meta_json,
            created_at=utc_now(),
        )
        db.add(event)
        db.commit()
    except Exception as e:
        db.rollback()
        # Audit logging failure must not crash the application, but should be noted
        print(f"[WARN] Failed to write auth audit event: {e}")
