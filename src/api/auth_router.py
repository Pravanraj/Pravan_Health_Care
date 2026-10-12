"""Authentication router managing user login, token issue, and user profile."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import User
from src.utils.auth import verify_password, create_access_token
from src.api.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    full_name: str


class LoginPayload(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    full_name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Optional[OAuth2PasswordRequestForm] = Depends(),
    json_payload: Optional[LoginPayload] = None,
    db: Session = Depends(get_db),
):
    """Authenticate user with username and password, returning JWT bearer token."""
    username = form_data.username if form_data else (json_payload.username if json_payload else "")
    password = form_data.password if form_data else (json_payload.password if json_payload else "")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name,
    }


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieve currently authenticated user identity and role."""
    return current_user


@router.get("/users", response_model=List[UserResponse])
def list_system_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all system users and roles (Administrator role required)."""
    return db.query(User).all()
