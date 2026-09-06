import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse
from app.repositories.user_repository import UserRepository
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.errors import ConflictError, AuthenticationError, NotFoundError


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register_user(self, user_in: UserCreate) -> Token:
        """Register a new user, returning user data and JWT token."""
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise ConflictError(message="A user with this email address already exists.")

        hashed_password = get_password_hash(user_in.password)
        new_user = User(
            email=user_in.email.lower(),
            password_hash=hashed_password,
            full_name=user_in.full_name
        )
        created_user = await self.user_repo.create(new_user)
        await self.db.commit()
        
        access_token = create_access_token(subject=str(created_user.id))
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(created_user)
        )

    async def authenticate_user(self, credentials: UserLogin) -> Token:
        """Authenticate user credentials and return JWT token."""
        user = await self.user_repo.get_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user.password_hash):
            raise AuthenticationError(message="Invalid email or password.")

        access_token = create_access_token(subject=str(user.id))
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(message="User not found.")
        return user
