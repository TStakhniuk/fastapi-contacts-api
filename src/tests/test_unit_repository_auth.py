import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from faker import Faker

from src.auth.repository import UserRepository, RoleRepository
from src.tests.models_imports import User, Role
from src.auth.schemas import UserCreate, RoleEnum

fake = Faker()


class TestUserRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = AsyncMock(spec=AsyncSession)
        self.repo = UserRepository(self.session)

    @patch("src.auth.repository.get_password_hash", return_value="hashed_pwd")
    async def test_create_user(self, mock_hash):
        role = Role(id=2, name=RoleEnum.USER.value)
        role_repo = AsyncMock()
        role_repo.get_role_by_name.return_value = role

        with patch("src.auth.repository.RoleRepository", return_value=role_repo):
            user_data = UserCreate(
                username=fake.user_name(),
                email=fake.email(),
                password=fake.password()
            )
            new_user = await self.repo.create_user(user_data)

        self.assertIsInstance(new_user, User)
        self.assertEqual(new_user.hashed_password, "hashed_pwd")
        self.assertEqual(new_user.role_id, role.id)
        self.session.add.assert_called_once()
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once_with(new_user)

    async def test_get_user_by_email(self):
        fake_user = User(
            id=fake.random_int(min=1, max=1000),
            username=fake.user_name(),
            email=fake.email(),
            hashed_password=fake.password(),
            role_id=2,
            is_active=fake.boolean()
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_user
        self.session.execute = AsyncMock(return_value=mock_result)

        user = await self.repo.get_user_by_email(fake_user.email)

        self.assertEqual(user, fake_user)
        self.session.execute.assert_awaited_once()

    async def test_get_user_by_username(self):
        fake_user = User(
            id=fake.random_int(min=1, max=1000),
            username=fake.user_name(),
            email=fake.email()
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_user
        self.session.execute = AsyncMock(return_value=mock_result)

        user = await self.repo.get_user_by_username(fake_user.username)

        self.assertEqual(user, fake_user)
        self.session.execute.assert_awaited_once()

    async def test_activate_user(self):
        user = User(
            id=fake.random_int(min=1, max=1000),
            username=fake.user_name(),
            email=fake.email(),
            is_active=False
        )
        await self.repo.activate_user(user)

        self.assertTrue(user.is_active)
        self.session.add.assert_called_once_with(user)
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once_with(user)

    async def test_update_password(self):
        user = User(
            id=fake.random_int(min=1, max=1000),
            username=fake.user_name(),
            email=fake.email(),
            hashed_password=fake.password()
        )
        new_hash = fake.password()
        await self.repo.update_password(user, new_hash)

        self.assertEqual(user.hashed_password, new_hash)
        self.session.add.assert_called_once_with(user)
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once_with(user)


class TestRoleRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = AsyncMock(spec=AsyncSession)
        self.repo = RoleRepository(self.session)

    async def test_get_role_by_name(self):
        role = Role(id=2, name=RoleEnum.USER.value)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = role
        self.session.execute = AsyncMock(return_value=mock_result)

        result = await self.repo.get_role_by_name(RoleEnum.USER)

        self.assertEqual(result, role)
        self.session.execute.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
