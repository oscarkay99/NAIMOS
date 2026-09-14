import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    return user


def require_permission(permission_code: str) -> Callable[..., User]:
    """FastAPI dependency factory enforcing server-side RBAC (section 39: never
    rely only on frontend checks). Every protected route declares exactly the
    permission it needs; the check runs against the DB-backed role assignment."""

    def _check(
        request: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        role_codes = {p.code for p in user.role.permissions}
        if permission_code not in role_codes:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role '{user.role.name}' lacks permission '{permission_code}'",
            )
        request.state.current_user = user
        return user

    return _check
