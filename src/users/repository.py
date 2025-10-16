from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User


class UserProfileRepository:
    """
    Repository class for managing user profile data in the database.

    :param session: Async SQLAlchemy session used for database operations.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_avatar(self, user: User, url: str) -> User:
        """
        Update the avatar URL of a given user.

        :param user: The User instance whose avatar will be updated.
        :param url: The new avatar URL to set.
        :return: The updated User instance with refreshed database state.
        """
        user.avatar = url
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user