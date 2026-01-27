import asyncio
import logging
from typing import Optional, Dict, Any, List

import vk_api
from vk_api.exceptions import ApiError

logger = logging.getLogger(__name__)


class VKService:
    def __init__(self, access_token: str):
        self.session = vk_api.VkApi(token=access_token)
        self.api = self.session.get_api()

    @staticmethod
    def validate_token(access_token: str) -> bool:
        try:
            session = vk_api.VkApi(token=access_token)
            api = session.get_api()
            api.users.get()
            return True
        except Exception:
            return False

    async def get_group_info(self, group_id_or_screen: str) -> Optional[Dict[str, Any]]:
        """
        Принимает: '123', '-123', 'club123', 'public123', 'mygroup'
        Возвращает объект groups.getById[0] или None.
        """
        try:
            clean = (
                group_id_or_screen
                .replace("https://vk.com/", "")
                .replace("vk.com/", "")
                .replace("club", "")
                .replace("public", "")
                .replace("event", "")
                .strip()
            )
            if clean.startswith("-"):
                clean = clean[1:]

            loop = asyncio.get_event_loop()

            if not clean.isdigit():
                resolved = await loop.run_in_executor(
                    None, lambda: self.api.utils.resolveScreenName(screen_name=clean)
                )
                if not resolved or resolved.get("type") != "group":
                    return None
                clean = str(resolved["object_id"])

            groups = await loop.run_in_executor(None, lambda: self.api.groups.getById(group_id=clean))
            return groups[0] if groups else None

        except ApiError as e:
            logger.error(f"VK API error get_group_info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error get_group_info: {e}")
            return None

    async def post_to_wall(
    self,
    group_id: str,
    message: Optional[str],
    photo_paths: Optional[List[str]] = None
) -> Optional[int]:
        try:
            clean_group_id = str(group_id).replace("-", "")
            owner_id = f"-{clean_group_id}"

            loop = asyncio.get_event_loop()
            attachments: List[str] = []

            if photo_paths:
                upload = vk_api.VkUpload(self.session)
                for p in photo_paths:
                    try:
                        photo = await loop.run_in_executor(
                            None, lambda path=p: upload.photo_wall(path, group_id=clean_group_id)
                        )
                        if photo:
                            attachments.append(f"photo{photo[0]['owner_id']}_{photo[0]['id']}")
                    except ApiError as e:
                        if e.code == 27:
                            logger.error("VK: upload фото недоступен для group token (error 27).")
                            attachments = []
                            break
                        logger.error(f"VK upload photo ApiError: {e}")
                    except Exception as e:
                        logger.error(f"VK upload photo error: {e}")

            params = {
                "owner_id": owner_id,
                "from_group": 1,
                "attachments": ",".join(attachments) if attachments else None,
            }
            msg = (message or "").strip()
            if msg:
                params["message"] = msg

            result = await loop.run_in_executor(None, lambda: self.api.wall.post(**params))
            return result.get("post_id")

        except ApiError as e:
            logger.error(f"VK API error post_to_wall: {e}")
            return None
        except Exception as e:
            logger.error(f"Error post_to_wall: {e}")
            return None
