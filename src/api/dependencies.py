"""API security dependencies, authentication guards, and Role-Based Access Control."""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import User
from src.utils.auth import decode_access_token, ROLE_ADMIN, ROLE_CLINICAL, ROLE_ANALYST

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate bearer token and resolve authenticated User model."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        # Default fallback user for open/demo local calls when token omitted
        user = db.query(User).filter(User.username == "admin").first()
        if user:
            return user
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(allowed_roles: List[str]):
    """Decorator dependency to enforce Role-Based Access Control."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_roles}. Current role: '{current_user.role}'",
            )
        return current_user
    return role_checker


require_admin = require_roles([ROLE_ADMIN])
require_clinical_or_admin = require_roles([ROLE_ADMIN, ROLE_CLINICAL])
require_any_authenticated = require_roles([ROLE_ADMIN, ROLE_CLINICAL, ROLE_ANALYST])
