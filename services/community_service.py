from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Community, PlatformType, User
from typing import List

class CommunityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_community(self, user_id: int, platform: str, community_id: str, community_name: str, access_token: str = None):
        user = await self.session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user.scalar_one_or_none()

        if not user:
            user = User(telegram_id=user_id)
            self.session.add(user)
            await self.session.flush()

        community = Community(
            user_id=user.id,
            platform = PlatformType[platform.upper()],
            community_id=community_id,
            community_name=community_name,
            access_token=access_token
        )
        self.session.add(community)
        await self.session.commit()
        return community

    async def get_user_communities(self, telegram_id: int) -> List[Community]:
        user = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user.scalar_one_or_none()

        if not user:
            return []

        result = await self.session.execute(
            select(Community).where(Community.user_id == user.id)
        )
        return result.scalars().all()
