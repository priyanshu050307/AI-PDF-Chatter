from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Register a new user account."""
    auth_service = AuthService(db)
    return await auth_service.register_user(user_in)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_async_db)):
    """Authenticate user credentials and return JWT bearer token."""
    auth_service = AuthService(db)
    return await auth_service.authenticate_user(credentials)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Fetch profile of currently authenticated user."""
    return UserResponse.model_validate(current_user)
