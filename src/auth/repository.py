from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.auth.models import User, Role
from src.auth.schemas import UserCreate, RoleEnum
from src.auth.pass_utils import get_password_hash


class UserRepository:
    """
    Repository class for User-related database operations.
    """
    def __init__(self, session: AsyncSession):
        """
        Initialize UserRepository with an async database session.

        :param session: SQLAlchemy asynchronous database session.
        :type session: AsyncSession
        """
        self.session = session

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user with hashed password and default role.

        :param user_data: Data required to create a new user.
        :type user_data: UserCreate
        :return: Newly created User object.
        :rtype: User
        """
        hashed_password = get_password_hash(user_data.password)
        user_role = await RoleRepository(self.session).get_role_by_name(RoleEnum.USER)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role_id=user_role.id,
            is_active=False
        )
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Retrieve a user by their email.

        :param email: User's email to search for.
        :type email: str
        :return: User object if found, else None.
        :rtype: User | None
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """
        Retrieve a user by their username.

        :param username: Username to search for.
        :type username: str
        :return: User object if found, else None.
        :rtype: User | None
        """
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def activate_user(self, user: User):
        """
        Activate a user's account by setting is_active to True.

        :param user: User object to activate.
        :type user: User
        """
        user.is_active = True
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

    async def update_password(self, user: User, new_hashed_password: str):
        """
        Update the hashed password of a user.

        :param user: User object whose password will be updated.
        :type user: User
        :param new_hashed_password: New hashed password string.
        :type new_hashed_password: str
        """
        user.hashed_password = new_hashed_password
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)


class RoleRepository:
    """
    Repository class for Role-related database operations.
    """
    def __init__(self, session: AsyncSession):
        """
        Initialize RoleRepository with an async database session.

        :param session: SQLAlchemy asynchronous database session.
        :type session: AsyncSession
        """
        self.session = session

    async def get_role_by_name(self, name: RoleEnum) -> Role | None:
        """
        Retrieve a role by its name.

        :param name: Name of the role to search for.
        :type name: RoleEnum
        :return: Role object if found, else None.
        :rtype: Role | None
        """
        result = await self.session.execute(select(Role).where(Role.name == name.value))
        return result.scalar_one_or_none()

