import os
from typing import List, Optional
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import select

from models import Post, Community, PlatformType, PostToCommunity, PostStatus
from services.vk_service import VKService


class PostService:
    def __init__(self, session):
        self.session = session

    async def publish_from_state(
        self,
        bot: Bot,
        user_id: int,
        from_chat_id: int,
        message_id: int,
        text: str,
        photo_file_id: Optional[str],
        document_file_id: Optional[str],
        community_ids: List[int],
    ) -> int:
        
        post = Post(user_id=user_id, message_id=message_id, from_chat_id=from_chat_id)
        self.session.add(post)
        await self.session.flush()

        result = await self.session.execute(select(Community).where(Community.id.in_(community_ids)))
        communities = result.scalars().all()

        ptc_list: List[PostToCommunity] = []
        for c in communities:
            ptc = PostToCommunity(post_id=post.id, community_id=c.id, status=PostStatus.PENDING)
            self.session.add(ptc)
            ptc_list.append(ptc)

        await self.session.commit()

        file_id = photo_file_id or document_file_id
        photo_paths = await self._download_photo_by_file_id(bot, file_id)

        sent_ok = 0
        for ptc in ptc_list:
            c = await self.session.get(Community, ptc.community_id)

            ok = False
            if c.platform == PlatformType.TELEGRAM:
                ok = await self._send_to_telegram(bot, c.community_id, from_chat_id, message_id)

            elif c.platform == PlatformType.VK:
                ok = await self._send_to_vk(c, text, photo_paths)

            ptc.status = PostStatus.SENT if ok else PostStatus.FAILED
            ptc.sent_at = datetime.now(timezone.utc) if ok else None
            await self.session.commit()

            if ok:
                sent_ok += 1

        for p in photo_paths:
            try:
                os.remove(p)
            except OSError:
                pass

        return sent_ok

    async def _send_to_telegram(self, bot: Bot, target_chat_id: str, from_chat_id: int, message_id: int) -> bool:
        try:
            await bot.copy_message(chat_id=target_chat_id, from_chat_id=from_chat_id, message_id=message_id)
            return True
        except Exception:
            return False

    async def _send_to_vk(self, community: Community, text: str, photo_paths: List[str]) -> bool:
        try:
            if not community.access_token:
                return False

            vk = VKService(community.access_token)

            msg = (text or "").strip()
            message_param = msg if msg else None

            post_id = await vk.post_to_wall(
                group_id=community.community_id,
                message=message_param,        
                photo_paths=photo_paths or None
            )
            return bool(post_id)
        except Exception:
            return False

    async def _download_photo_by_file_id(self, bot: Bot, file_id: Optional[str]) -> List[str]:
        """
        bot.download_file(...) без destination возвращает BytesIO.
        Чтобы не получать пустые файлы: делаем seek(0) и пишем getvalue().
        """
        if not file_id:
            return []

        try:
            file = await bot.get_file(file_id)
            data = await bot.download_file(file.file_path)

            try:
                data.seek(0)
            except Exception:
                pass

            os.makedirs("tmp_photos", exist_ok=True)
            path = os.path.join("tmp_photos", f"{file_id}.jpg")

            with open(path, "wb") as f:
                if hasattr(data, "getvalue"):
                    f.write(data.getvalue())
                else:
                    f.write(data.read())


            # print("Saved:", path, "size:", os.path.getsize(path))

            return [path]
        except Exception as e:
            # print("TG download error:", e)
            return []
