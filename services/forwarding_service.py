import os
from typing import List
from sqlalchemy import select

from aiogram.types import Message

from models import Community, PlatformType
from services.vk_service import VKService


class ForwardingService:
    def __init__(self, session):
        self.session = session

    async def forward_reply_to_all_vk(self, message: Message, user_id: int) -> int:
        result = await self.session.execute(
            select(Community).where(
                Community.user_id == user_id,
                Community.platform == PlatformType.VK
            )
        )
        vk_groups = result.scalars().all()
        if not vk_groups:
            return 0

        text = message.text or message.caption or ""
        photo_paths = await self._download_single_photo(message)

        sent = 0
        for g in vk_groups:
            if not g.access_token:
                continue
            vk = VKService(g.access_token)
            post_id = await vk.post_to_wall(g.community_id, text, photo_paths or None)
            if post_id:
                sent += 1

        for p in photo_paths:
            try:
                os.remove(p)
            except OSError:
                pass

        return sent

    async def _download_single_photo(self, message: Message) -> List[str]:
        try:
            if not message.photo:
                return []
            best = message.photo[-1]
            file = await message.bot.get_file(best.file_id)
            data = await message.bot.download_file(file.file_path)

            os.makedirs("tmp_photos", exist_ok=True)
            path = os.path.join("tmp_photos", f"{best.file_id}.jpg")
            with open(path, "wb") as f:
                f.write(data.read())

            return [path]
        except Exception:
            return []
