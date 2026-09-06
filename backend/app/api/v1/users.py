from fastapi import APIRouter, Depends
from app.schemas.user import UserResponse
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(get_current_user)):
    """Retrieve details for current user profile."""
    return UserResponse.model_validate(current_user)
