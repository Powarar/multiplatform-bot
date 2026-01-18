from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Post, User, PostToCommunity
from datetime import datetime, timezone
from typing import List, Optional

class PostService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_post(self, user_id: int, message_id: int, from_chat_id: int, community_ids: list):
        user = await self.session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user.scalar_one_or_none()

        if not user:
            user = User(telegram_id=user_id)
            self.session.add(user)
            await self.session.flush()

        post = Post(
            user_id=user_id,
            message_id=message_id,
            from_chat_id=from_chat_id
        )
        self.session.add(post)
        await self.session.flush()

        if community_ids:
            for community_id in community_ids:
                p2c = PostToCommunity(
                    post_id=post.id,
                    community_id=community_id,
                    status="pending"
                )
                self.session.add(p2c)

        await self.session.commit()
        return post

    async def get_user_posts(self, telegram_id: int) -> List[Post]:
        user = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user.scalar_one_or_none()

        if not user:
            return []

        result = await self.session.execute(
            select(Post).where(Post.user_id == user.id).order_by(Post.created_at.desc())
        )
        return result.scalars().all()
