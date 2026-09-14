import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CurrentUserOut, LoginRequest, RefreshRequest, TokenResponse
from app.services.audit import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    log_action(
        db,
        user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.name),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    data = decode_token(payload.refresh_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    user = db.get(User, uuid.UUID(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.name),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    log_action(
        db,
        user_id=user.id,
        action="auth.logout",
        entity_type="user",
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=CurrentUserOut)
def me(user: User = Depends(get_current_user)) -> CurrentUserOut:
    out = CurrentUserOut.model_validate(user)
    out.permissions = sorted(p.code for p in user.role.permissions)
    return out
