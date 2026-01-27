from sqlalchemy import select
from models import Community


class CommunityService:
    def __init__(self, session):
        self.session = session

    async def get_user_communities(self, user_id: int):
        result = await self.session.execute(select(Community).where(Community.user_id == user_id))
        return result.scalars().all()
