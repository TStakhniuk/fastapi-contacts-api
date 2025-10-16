import pickle
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis

from src.config.db import get_db
from src.config.settings import settings
from src.auth.models import User
from src.auth.repository import UserRepository
from src.auth.schemas import TokenData, RoleEnum

ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
VERIFICATION_TOKEN_EXPIRE_HOURS = 24
RESET_PASSWORD_TOKEN_EXPIRE_HOURS = 1

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
redis = aioredis.from_url(
    f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/0",
    encoding="utf-8",
    decode_responses=False
)

def create_access_token(data: dict) -> str:
    """
    Create a JWT access token with a short expiration.

    :param data: Data to encode in the token (e.g., {"sub": email}).
    :type data: dict
    :return: JWT access token string.
    :rtype: str
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token with a longer expiration.

    :param data: Data to encode in the token (e.g., {"sub": email}).
    :type data: dict
    :return: JWT refresh token string.
    :rtype: str
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData | None:
    """
    Decode a JWT access token and extract the username.

    :param token: JWT access token string.
    :type token: str
    :return: TokenData containing username if valid, else None.
    :rtype: TokenData | None
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except JWTError:
        return None


def create_verification_token(email: str) -> str:
    """
    Create a JWT token for email verification.

    :param email: User email to include in the token.
    :type email: str
    :return: JWT verification token string.
    :rtype: str
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    to_encode = {"exp": expire, "sub": email}
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_verification_token(token: str) -> str | None:
    """
    Decode a verification JWT token and extract the email.

    :param token: JWT verification token string.
    :type token: str
    :return: Email if token is valid, else None.
    :rtype: str | None
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        return email
    except JWTError:
        return None


async def create_reset_password_token(email: str) -> str:
    """
    Create a disposable JWT token for password reset and store it in Redis.

    :param email: User email for which the reset token is generated.
    :type email: str
    :return: JWT reset password token string.
    :rtype: str
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=RESET_PASSWORD_TOKEN_EXPIRE_HOURS)
    token_data = {"exp": expire, "sub": email}
    token = jwt.encode(token_data, settings.secret_key, algorithm=ALGORITHM)

    redis_key = f"reset_password:{token}"
    await redis.set(redis_key, email, ex=RESET_PASSWORD_TOKEN_EXPIRE_HOURS * 3600)

    return token


async def decode_reset_password_token(token: str) -> str | None:
    """
    Decode a reset password token, verify it, and delete it from Redis (one-time use).

    :param token: JWT reset password token string.
    :type token: str
    :return: Email if token is valid and exists in Redis, else None.
    :rtype: str | None
    """
    redis_key = f"reset_password:{token}"
    email_bytes = await redis.get(redis_key)
    if not email_bytes:
        return None
    try:
        jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        await redis.delete(redis_key) # make the token disposable
        email = email_bytes.decode("utf-8")
        return email
    except JWTError:
        return None



async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    """
    Retrieve the currently authenticated user based on the access token.

    :param token: JWT access token provided in the Authorization header.
    :type token: str
    :param db: AsyncSession database session.
    :type db: AsyncSession
    :return: User object corresponding to the token.
    :rtype: User
    :raises HTTPException: If token is invalid or user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_access_token(token)
    if token_data is None:
        raise credentials_exception

    email = token_data.username
    cache_key = f"user:{email}"

    # Check Redis
    cached_user = await redis.get(cache_key)
    if cached_user:
        user = pickle.loads(cached_user)
        return user

    repo = UserRepository(db)
    user = await repo.get_user_by_email(email)
    if not user:
        raise credentials_exception

    await redis.set(cache_key, pickle.dumps(user), ex=900)
    return user


class RoleChecker:
    """
    Dependency class for checking if the current user has one of the allowed roles.
    """
    def __init__(self, allowed_roles: list[RoleEnum]):
        """
        Initialize RoleChecker with allowed roles.

        :param allowed_roles: List of RoleEnum values permitted to access the resource.
        :type allowed_roles: list[RoleEnum]
        """
        self.allowed_roles = allowed_roles

    async def __call__(self, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
        """
        Verify current user's role against allowed roles.

        :param token: JWT access token from Authorization header.
        :type token: str
        :param db: AsyncSession database session.
        :type db: AsyncSession
        :return: User object if role is allowed.
        :rtype: User
        :raises HTTPException: If user role is not allowed.
        """
        user = await get_current_user(token, db)

        if user.role.name not in [role.value for role in self.allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user
