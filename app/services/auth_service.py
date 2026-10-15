from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.core.security import verify_password, create_access_token, decode_token, get_password_hash
from app.db.session import get_db
from app.models.user import User, Role
from app.schemas.auth import Token, UserResponse, UserCreate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


class AuthService:
    @staticmethod
    def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[User]:
        user = (
            db.query(User)
            .filter((User.email == username_or_email) | (User.username == username_or_email))
            .first()
        )
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_user_tokens(user: User) -> Token:
        access_token = create_access_token(
            subject=user.id,
            claims={
                "email": user.email,
                "username": user.username,
                "roles": [r.name for r in user.roles],
            },
        )
        return Token(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        existing = db.query(User).filter((User.email == user_in.email) | (User.username == user_in.username)).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or username already registered")

        role = db.query(Role).filter(Role.name == user_in.role).first()
        roles = [role] if role else []

        user = User(
            email=user_in.email,
            username=user_in.username,
            full_name=user_in.full_name,
            hashed_password=get_password_hash(user_in.password),
            is_active=True,
            is_superuser=False,
            roles=roles,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Dependency to retrieve the authenticated user from the Bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or non-existent user")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency ensuring user has Admin role or superuser flag."""
    is_admin = current_user.is_superuser or any(r.name == "admin" for r in current_user.roles)
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required")
    return current_user
