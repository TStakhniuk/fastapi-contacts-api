import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from functools import wraps
from faker import Faker

patch("fastapi_cache.decorator.cache", lambda *a, **k: (lambda f: f)).start()

# Mock FastAPICache
class MockCoder:
    def encode(self, v): return v
    def decode(self, v): return v

mock_backend = MagicMock()
patch.multiple(
    "fastapi_cache.FastAPICache",
    get_prefix=lambda: "test",
    get_coder=lambda: MockCoder(),
    get_backend=lambda: mock_backend,
    get_cache_status_header=lambda: "test",
    _prefix="test",
    _coder=MockCoder(),
    _backend=mock_backend,
    _cache_status_header="test"
).start()

from src.contacts.repository import ContactRepository
from src.contacts.schemas import ContactCreate, ContactUpdate
from src.tests.models_imports import Contact


fake = Faker()


class TestContactRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = AsyncMock()
        self.session.add = MagicMock()

        self.repo = ContactRepository(self.session)

    async def test_get_contacts(self):
        contact = Contact(
            id=fake.random_int(1, 1000),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone_number=fake.phone_number(),
            birthday=fake.date_of_birth(),
            additional_info=fake.sentence(),
            user_id=fake.random_int(1, 10)
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [contact]
        self.session.execute = AsyncMock(return_value=mock_result)

        contacts = await self.repo.get_contacts(user_id=contact.user_id)

        self.assertEqual(contacts, [contact])
        self.session.execute.assert_awaited_once()

    async def test_get_contact(self):
        contact = Contact(
            id=fake.random_int(1, 1000),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone_number=fake.phone_number(),
            birthday=fake.date_of_birth(),
            additional_info=fake.sentence(),
            user_id=fake.random_int(1, 10)
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = contact
        self.session.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_contact(contact_id=contact.id, user_id=contact.user_id)

        self.assertEqual(result, contact)
        self.session.execute.assert_awaited_once()

    @patch("src.contacts.repository.invalidate_get_contacts_repo_cache", new_callable=AsyncMock)
    async def test_create_contact(self, mock_invalidate):
        user_id = fake.random_int(1, 10)
        data = ContactCreate(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone_number=fake.phone_number(),
            birthday=fake.date_of_birth(),
            additional_info=fake.sentence()
        )

        new_contact = await self.repo.create_contact(data, user_id=user_id)

        self.assertIsInstance(new_contact, Contact)
        self.session.add.assert_called_once_with(new_contact)
        self.session.commit.assert_awaited_once()
        self.session.refresh.assert_awaited_once_with(new_contact)
        mock_invalidate.assert_awaited_once_with(user_id)

    @patch("src.contacts.repository.invalidate_get_contacts_repo_cache", new_callable=AsyncMock)
    async def test_update_contact(self, mock_invalidate):
        contact = Contact(
            id=fake.random_int(1, 1000),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone_number=fake.phone_number(),
            birthday=fake.date_of_birth(),
            additional_info=fake.sentence(),
            user_id=fake.random_int(1, 10)
        )
        update_data = ContactUpdate(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone_number=fake.phone_number(),
            birthday=fake.date_of_birth(),
            additional_info=fake.sentence()
        )
        self.repo.get_contact = AsyncMock(return_value=contact)

        updated = await self.repo.update_contact(contact.id, update_data, user_id=contact.user_id)

        self.assertEqual(updated.first_name, update_data.first_name)
        self.assertEqual(updated.last_name, update_data.last_name)
        self.assertEqual(updated.email, update_data.email)
        self.assertEqual(updated.phone_number, update_data.phone_number)
        self.assertEqual(updated.birthday, update_data.birthday)
        self.session.commit.assert_awaited_once()
        self.session.refresh.assert_awaited_once_with(contact)
        mock_invalidate.assert_awaited_once_with(contact.user_id)

    @patch("src.contacts.repository.invalidate_get_contacts_repo_cache", new_callable=AsyncMock)
    async def test_delete_contact(self, mock_invalidate):
        contact = Contact(
            id=fake.random_int(1, 1000),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone_number=fake.phone_number(),
            birthday=fake.date_of_birth(),
            additional_info=fake.sentence(),
            user_id=fake.random_int(1, 10)
        )
        self.repo.get_contact = AsyncMock(return_value=contact)

        deleted = await self.repo.delete_contact(contact.id, user_id=contact.user_id)

        self.assertEqual(deleted, contact)
        self.session.delete.assert_awaited_once_with(contact)
        self.session.commit.assert_awaited_once()
        mock_invalidate.assert_awaited_once_with(contact.user_id)

    async def test_search_contacts(self):
        contact = Contact(
            id=fake.random_int(1, 1000),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone_number=fake.phone_number(),
            birthday=fake.date_of_birth(),
            additional_info=fake.sentence(),
            user_id=fake.random_int(1, 10)
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [contact]
        self.session.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.search_contacts("query", user_id=contact.user_id)

        self.assertEqual(result, [contact])
        self.session.execute.assert_awaited_once()

    async def test_upcoming_birthdays(self):
        today = datetime.today().date()
        contact = Contact(
            id=fake.random_int(1, 1000),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone_number=fake.phone_number(),
            birthday=today,
            additional_info=fake.sentence(),
            user_id=fake.random_int(1, 10)
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [contact]
        self.session.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.upcoming_birthdays(user_id=contact.user_id)

        self.assertEqual(result, [contact])
        self.session.execute.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
