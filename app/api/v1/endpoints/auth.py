from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import LoginRequest, Token, UserResponse, UserCreate
from app.services.auth_service import AuthService, get_current_user, require_admin
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=Token)
def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with username or email and return signed JWT."""
    user = AuthService.authenticate_user(db, login_req.username_or_email, login_req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    return AuthService.create_user_tokens(user)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve authenticated user's profile and roles."""
    return current_user


@router.post("/users", response_model=UserResponse)
def create_new_user(
    user_in: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Administrator-only user creation."""
    return AuthService.register_user(db, user_in)
