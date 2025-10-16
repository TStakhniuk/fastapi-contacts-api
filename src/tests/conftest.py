import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from main import app
from src.auth import services
from src.config.db import Base, get_db
from src.config.settings import settings
from src.auth.models import Role, User
from src.auth.pass_utils import get_password_hash
from src.auth.schemas import RoleEnum
from src.auth.services import create_access_token, create_refresh_token
from src.contacts.models import Contact
from faker import Faker


faker = Faker()


@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(settings.database_test_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def setup_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(engine, setup_database):
    AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
def override_get_db(db_session):
    async def _get_db():
        async with db_session as session:
            yield session
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    monkeypatch.setattr(services.redis, "set", AsyncMock())
    monkeypatch.setattr(services.redis, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(services.redis, "delete", AsyncMock())

    FastAPICache.init(InMemoryBackend(), prefix="test-cache")


@pytest.fixture(autouse=True)
def mock_rate_limiter(monkeypatch):
    monkeypatch.setattr(RateLimiter, "__call__", AsyncMock(return_value=None))

@pytest_asyncio.fixture(scope="function")
async def user_role(db_session) -> Role:
    role = Role(id=2, name=RoleEnum.USER.value)
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture(scope="function")
async def user_password():
    return faker.password()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session, user_role, user_password):
    hashed_password = get_password_hash(user_password)
    user = User(
        email=faker.email(),
        username=faker.user_name(),
        hashed_password=hashed_password,
        role_id=user_role.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def auth_header(test_user: User):
    access_token = create_access_token({"sub": test_user.email})
    refresh_token = create_refresh_token({"sub": test_user.email})
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Refresh-Token": refresh_token
    }


@pytest_asyncio.fixture(scope="function")
async def test_user_contact(db_session, test_user: User) -> Contact:
    contact = Contact(
        first_name=faker.first_name(),
        last_name=faker.last_name(),
        email=faker.email(),
        phone_number=faker.phone_number(),
        user_id=test_user.id,
        birthday=faker.date_of_birth(),
        additional_info=faker.text()
    )
    db_session.add(contact)
    await db_session.commit()
    await db_session.refresh(contact)
    return contact
