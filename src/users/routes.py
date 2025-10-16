import pickle

from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.db import get_db
from src.auth.models import User
from src.auth.services import RoleChecker
from src.auth.schemas import RoleEnum
from src.users.schemas import UserProfileResponse
from src.users.repository import UserProfileRepository
from src.users.cloudinary_utils import upload_avatar
from src.auth.services import redis


router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Retrieve the profile information of the currently authenticated user.

    :param current_user: The authenticated user obtained via RoleChecker dependency.
    :return: UserProfileResponse containing user details such as ID, username, email,
             creation date, role, and avatar URL.
    """
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        role=current_user.role.name,
        avatar=current_user.avatar
    )


@router.patch("/avatar", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def update_avatar_user(
    file: UploadFile = File(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Update the authenticated user's avatar.

    The uploaded file is sent to Cloudinary, the user's avatar URL is updated
    in the database, and the cached user data in Redis is refreshed.

    :param file: Uploaded avatar file.
    :param db: Async SQLAlchemy session for database operations.
    :param current_user: The authenticated user obtained via RoleChecker dependency.
    :return: UserProfileResponse with updated user profile including new avatar URL.
    """
    repo = UserProfileRepository(db)
    avatar_url = await upload_avatar(file.file, public_id=f"users/{current_user.username}")
    updated_user = await repo.update_avatar(current_user, avatar_url)

    cache_key = f"user:{current_user.email}"
    await redis.set(cache_key, pickle.dumps(updated_user), ex=900)

    return UserProfileResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        created_at=updated_user.created_at,
        role=updated_user.role.name,
        avatar=updated_user.avatar
    )
