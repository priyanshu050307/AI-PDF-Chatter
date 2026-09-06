import uuid
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.core.security import decode_access_token
from app.core.errors import AuthenticationError
from app.repositories.user_repository import UserRepository
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """Dependency that decodes JWT token and returns current authenticated User model."""
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AuthenticationError(message="Invalid or expired access token.")

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise AuthenticationError(message="Invalid token subject payload.")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise AuthenticationError(message="User associated with token no longer exists.")

    return user
