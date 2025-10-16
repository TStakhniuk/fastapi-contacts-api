from fastapi_cache import default_key_builder
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_cache.decorator import cache
from datetime import datetime, timedelta
from sqlalchemy import select, extract
from typing import List

from src.contacts.models import Contact
from src.contacts.schemas import ContactCreate, ContactUpdate
from src.config.cache import custom_repo_key_builder, invalidate_get_contacts_repo_cache


class ContactRepository:
    """
    Repository class for managing Contact records in the database.

    :param session: Async SQLAlchemy session for database operations.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    @cache(expire=600, namespace="get_contacts_repo", key_builder=custom_repo_key_builder)
    async def get_contacts(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Contact]:
        """
        Retrieve a list of contacts for a user with optional pagination.

        :param user_id: ID of the user whose contacts to fetch.
        :param skip: Number of contacts to skip (for pagination).
        :param limit: Maximum number of contacts to return.
        :return: List of Contact objects.
        """
        query = select(Contact).where(Contact.user_id == user_id).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_contact(self, contact_id: int, user_id: int) -> Contact | None:
        """
        Retrieve a single contact by ID for a specific user.

        :param contact_id: ID of the contact.
        :param user_id: ID of the user who owns the contact.
        :return: Contact object if found, else None.
        """
        query = select(Contact).where(Contact.id == contact_id, Contact.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_contact(self, contact: ContactCreate, user_id: int) -> Contact:
        """
        Create a new contact for a user.

        :param contact: Contact creation data.
        :param user_id: ID of the user creating the contact.
        :return: The newly created Contact object.
        """
        new_contact = Contact(**contact.model_dump(), user_id=user_id)
        self.session.add(new_contact)
        await self.session.commit()
        await self.session.refresh(new_contact)  # Get ID from database
        await invalidate_get_contacts_repo_cache(user_id)
        return new_contact

    async def update_contact(self, contact_id: int, contact: ContactUpdate, user_id: int) -> Contact | None:
        """
        Update an existing contact for a user.

        :param contact_id: ID of the contact to update.
        :param contact: Contact update data.
        :param user_id: ID of the user who owns the contact.
        :return: Updated Contact object if successful, else None.
        """
        existing_contact = await self.get_contact(contact_id, user_id)
        if not existing_contact:
            return None
        for key, value in contact.model_dump().items():
            setattr(existing_contact, key, value)
        await self.session.commit()
        await self.session.refresh(existing_contact)
        await invalidate_get_contacts_repo_cache(user_id)
        return existing_contact

    async def delete_contact(self, contact_id: int, user_id: int) -> Contact | None:
        """
        Delete a contact for a user.

        :param contact_id: ID of the contact to delete.
        :param user_id: ID of the user who owns the contact.
        :return: Deleted Contact object if successful, else None.
        """
        existing_contact = await self.get_contact(contact_id, user_id)
        if not existing_contact:
            return None
        await self.session.delete(existing_contact)
        await self.session.commit()
        await invalidate_get_contacts_repo_cache(user_id)
        return existing_contact

    async def search_contacts(self, query: str, user_id: int, skip: int = 0, limit: int = 100) -> List[Contact]:
        """
        Search contacts by name or email for a specific user.

        :param query: Search string (matches first name, last name, or email).
        :param user_id: ID of the user whose contacts to search.
        :param skip: Number of results to skip (for pagination).
        :param limit: Maximum number of results to return.
        :return: List of Contact objects matching the search query.
        """
        q = (
            select(Contact)
            .where(
                Contact.user_id == user_id,
                (Contact.first_name.ilike(f"%{query}%")) |
                (Contact.last_name.ilike(f"%{query}%")) |
                (Contact.email.ilike(f"%{query}%"))
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(q)
        return result.scalars().all()

    async def upcoming_birthdays(self, user_id: int) -> List[Contact]:
        """
        Retrieve contacts with birthdays in the upcoming week for a user.

        Handles week ranges that span across months or years.

        :param user_id: ID of the user whose contacts to check.
        :return: List of Contact objects with upcoming birthdays.
        """
        today = datetime.today().date()
        week_later = today + timedelta(days=6)

        today_month, today_day = today.month, today.day
        week_later_month, week_later_day = week_later.month, week_later.day

        if today_month == week_later_month:
            # week within one month
            query = select(Contact).where(
                Contact.user_id == user_id,
                (extract("month", Contact.birthday) == today_month) &
                (extract("day", Contact.birthday).between(today_day, week_later_day))
            )
        else:
            # week moves to next month/year
            query = select(Contact).where(
                Contact.user_id == user_id,
                ((extract("month", Contact.birthday) == today_month) & (extract("day", Contact.birthday) >= today_day)) |
                ((extract("month", Contact.birthday) == week_later_month) & (extract("day", Contact.birthday) <= week_later_day))
            )

        result = await self.session.execute(query)
        return result.scalars().all()