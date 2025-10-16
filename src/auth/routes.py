import pickle

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader

from src.auth.mail_utils import send_verification, send_reset_password
from src.config.db import get_db
from src.auth.repository import UserRepository
from src.auth.schemas import UserCreate, UserResponse, Token, PasswordResetRequest, PasswordResetConfirm
from src.auth.pass_utils import verify_password, get_password_hash
from src.auth.services import (
    redis,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    create_verification_token,
    decode_verification_token,
    create_reset_password_token,
    decode_reset_password_token
)


router = APIRouter()
env = Environment(loader=FileSystemLoader("src/templates"))


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, background_tasks: BackgroundTasks, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Register a new user and send a verification email.

    :param user_data: Data required to create a new user.
    :type user_data: UserCreate
    :param background_tasks: Background tasks handler to send emails asynchronously.
    :type background_tasks: BackgroundTasks
    :param request: The HTTP request object to determine base URL.
    :type request: Request
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: Information about the created user.
    :rtype: UserResponse
    :raises HTTPException: If the user with the given email already exists.
    """
    repo = UserRepository(db)

    existing_email = await repo.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="User with this email already exists")

    existing_username = await repo.get_user_by_username(user_data.username)
    if existing_username:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="User with this username already exists")

    new_user = await repo.create_user(user_data)

    verification_token = create_verification_token(new_user.email)
    base_url = str(request.base_url).rstrip("/")  # read host and port
    verification_link = f"{base_url}/auth/verify-email?token={verification_token}"
    template = env.get_template("verification_email.html")
    email_body = template.render(verification_link=verification_link, username=new_user.username)
    background_tasks.add_task(send_verification, new_user.email, email_body)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        created_at=new_user.created_at,
        role=new_user.role.name
    )


@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Verify a user's email using a token sent via email.

    :param token: Email verification token.
    :type token: str
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: Success message if email is verified or already confirmed.
    :rtype: dict
    :raises HTTPException: If token is invalid, expired, or user not found.
    """
    email: str = decode_verification_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    repo = UserRepository(db)
    user = await repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_active:
        return {"message": "Your email is already confirmed"}

    await repo.activate_user(user)
    return {"msg": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(email: str, background_tasks: BackgroundTasks, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Resend the email verification link to the user.

    :param email: Email of the user to resend the verification.
    :type email: str
    :param background_tasks: Background tasks handler to send emails asynchronously.
    :type background_tasks: BackgroundTasks
    :param request: The HTTP request object to determine base URL.
    :type request: Request
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: Success message confirming that verification email was resent.
    :rtype: dict
    :raises HTTPException: If user not found.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        return {"msg": "Email already verified"}

    verification_token = create_verification_token(user.email)
    base_url = str(request.base_url).rstrip("/")
    verification_link = f"{base_url}/auth/verify-email?token={verification_token}"
    template = env.get_template("verification_email.html")
    email_body = template.render(verification_link=verification_link, username=user.username)
    background_tasks.add_task(send_verification, user.email, email_body)

    return {"msg": "Verification email resent"}



@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user and return access and refresh tokens.

    :param form_data: OAuth2 form data containing username and password.
    :type form_data: OAuth2PasswordRequestForm
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: Access and refresh JWT tokens.
    :rtype: Token
    :raises HTTPException: If credentials are invalid or email not confirmed.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Email not confirmed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    cache_key = f"user:{user.email}"
    await redis.set(cache_key, pickle.dumps(user), ex=900)

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
async def refresh_tokens(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """
   Refresh access and refresh tokens using an existing refresh token.

   :param refresh_token: Existing refresh token to generate new tokens.
   :type refresh_token: str
   :param db: Database session dependency.
   :type db: AsyncSession
   :return: New access and refresh JWT tokens.
   :rtype: Token
   :raises HTTPException: If refresh token is invalid or user not found.
   """
    token_data = decode_access_token(refresh_token)
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_email(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/reset-password")
async def request_password_reset(data: PasswordResetRequest, background_tasks: BackgroundTasks, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Request a password reset email for a user.

    :param data: Password reset request containing the user's email.
    :type data: PasswordResetRequest
    :param background_tasks: Background tasks handler to send emails asynchronously.
    :type background_tasks: BackgroundTasks
    :param request: The HTTP request object to determine base URL.
    :type request: Request
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: Success message indicating that reset email was sent.
    :rtype: dict
    :raises HTTPException: If user with given email is not found.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_email(data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reset_token = await create_reset_password_token(user.email)
    base_url = str(request.base_url).rstrip("/")
    reset_link = f"{base_url}/auth/reset-password/confirm?token={reset_token}"
    template = env.get_template("reset_password_email.html")
    email_body = template.render(reset_link=reset_link, username=user.username)
    background_tasks.add_task(send_reset_password, user.email, email_body)

    return {"msg": "Password reset email sent"}


@router.post("/reset-password/confirm")
async def reset_password(data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """
    Confirm password reset using a token and set a new password.

    :param data: Password reset confirmation data containing token and new password.
    :type data: PasswordResetConfirm
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: Success message indicating password was updated.
    :rtype: dict
    :raises HTTPException: If token is invalid/expired or user not found.
    """
    email = await decode_reset_password_token(data.token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    repo = UserRepository(db)
    user = await repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    hashed_password = get_password_hash(data.new_password)
    await repo.update_password(user, hashed_password)

    return {"msg": "Password updated successfully"}
