from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_limiter.depends import RateLimiter
from typing import List

from src.config.db import get_db
from src.contacts.schemas import ContactCreate, ContactUpdate, ContactResponse
from src.contacts.repository import ContactRepository
from src.auth.models import User
from src.auth.schemas import RoleEnum
from src.auth.services import RoleChecker

router = APIRouter()


@router.get(
    "/",
    response_model=List[ContactResponse],
    description="Get all contacts (max 20 requests per minute per user)",
    dependencies=[Depends(RateLimiter(times=20, seconds=60))]
)
async def get_contacts(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Retrieve a list of contacts for the current user.

    :param skip: Number of contacts to skip for pagination.
    :param limit: Maximum number of contacts to return.
    :param db: Database session dependency.
    :param current_user: Authenticated user.
    :return: List of ContactResponse objects.
    """
    repo = ContactRepository(db)
    return await repo.get_contacts(user_id=current_user.id, skip=skip, limit=limit)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    description="Get contact by ID (max 20 requests per minute per user)",
    dependencies=[Depends(RateLimiter(times=20, seconds=60))]
)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Retrieve a single contact by its ID for the current user.

    :param contact_id: ID of the contact to retrieve.
    :param db: Database session dependency.
    :param current_user: Authenticated user.
    :return: ContactResponse object if found.
    :raises HTTPException: 404 if contact is not found.
    """
    repo = ContactRepository(db)
    contact = await repo.get_contact(contact_id, user_id=current_user.id)
    if not contact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.post(
    "/",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    description="Create a new contact (max 5 requests per minute per user)",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))]
)
async def create_contact(
    contact: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Create a new contact for the current user.

    :param contact: Contact creation data.
    :param db: Database session dependency.
    :param current_user: Authenticated user.
    :return: Created ContactResponse object.
    """
    repo = ContactRepository(db)
    return await repo.create_contact(contact, user_id=current_user.id)


@router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    description="Update contact (max 10 requests per minute per user)",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]
)
async def update_contact(
    contact_id: int,
    contact: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Update an existing contact for the current user.

    :param contact_id: ID of the contact to update.
    :param contact: Updated contact data.
    :param db: Database session dependency.
    :param current_user: Authenticated user.
    :return: Updated ContactResponse object.
    :raises HTTPException: 404 if contact is not found.
    """
    repo = ContactRepository(db)
    updated = await repo.update_contact(contact_id, contact, user_id=current_user.id)
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return updated


@router.delete(
    "/{contact_id}",
    response_model=ContactResponse,
    description="Delete contact (max 10 requests per minute per user)",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]
)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Delete a contact for the current user.

    :param contact_id: ID of the contact to delete.
    :param db: Database session dependency.
    :param current_user: Authenticated user.
    :return: Deleted ContactResponse object.
    :raises HTTPException: 404 if contact is not found.
    """
    repo = ContactRepository(db)
    deleted = await repo.delete_contact(contact_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return deleted


@router.get(
    "/search/",
    response_model=List[ContactResponse],
    description="Search contacts (max 15 requests per minute per user)",
    dependencies=[Depends(RateLimiter(times=15, seconds=60))]
)
async def search_contacts(
    query: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Search contacts by a query string for the current user.

    :param query: Search string (name, email, phone, etc.).
    :param skip: Number of results to skip for pagination.
    :param limit: Maximum number of results to return.
    :param db: Database session dependency.
    :param current_user: Authenticated user.
    :return: List of ContactResponse objects matching the query.
    """
    repo = ContactRepository(db)
    return await repo.search_contacts(query=query, user_id=current_user.id, skip=skip, limit=limit)


@router.get(
    "/birthdays/",
    response_model=List[ContactResponse],
    description="Get upcoming birthdays (max 10 requests per minute per user)",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]
)
async def upcoming_birthdays(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER]))
):
    """
    Retrieve contacts with upcoming birthdays for the current user.

    :param db: Database session dependency.
    :param current_user: Authenticated user.
    :return: List of ContactResponse objects with upcoming birthdays.
    """
    repo = ContactRepository(db)
    return await repo.upcoming_birthdays(user_id=current_user.id)
