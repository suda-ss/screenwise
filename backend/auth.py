from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import AuthSession, Membership, Role, User


PBKDF2_ITERATIONS = 310_000


@dataclass
class Principal:
    user: User
    organization_id: str
    role: Role


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user_id: str) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    db.add(AuthSession(id=token_hash(token), user_id=user_id, expires_at=expires))
    return token, expires


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie),
    db: Session = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.id == token_hash(session_token),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    )
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user


def get_principal(
    organization_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Principal:
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == organization_id,
        )
    )
    if not membership:
        raise HTTPException(status_code=403, detail="No access to this organization")
    return Principal(user=user, organization_id=organization_id, role=membership.role)


def require_editor(principal: Principal = Depends(get_principal)) -> Principal:
    if principal.role not in {Role.owner, Role.admin, Role.recruiter}:
        raise HTTPException(status_code=403, detail="Recruiter permission required")
    return principal


def delete_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.id == token_hash(token)))
