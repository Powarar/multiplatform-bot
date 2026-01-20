import vk_api
from vk_api.exceptions import ApiError
from typing import Optional, Dict, Any
import logging
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

def async_wrap(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return wrapper

class VKService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        try:
            self.session = vk_api.VkApi(token=access_token)
            self.api = self.session.get_api()
        except Exception as e:
            logger.error(f"Failed to initialize VK API: {e}")
            raise

    async def get_group_info(self, group_id: str) -> Optional[Dict[str, Any]]:
        try:
            clean_id = group_id.replace('club', '').replace('public', '').replace('event', '')
            
            if not clean_id.isdigit() and not clean_id.startswith('-'):
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.api.utils.resolveScreenName(screen_name=clean_id)
                )
                if result and result.get('type') == 'group':
                    clean_id = str(result['object_id'])
                else:
                    return None
            
            clean_id = clean_id.replace('-', '')
            
            loop = asyncio.get_event_loop()
            groups = await loop.run_in_executor(
                None,
                lambda: self.api.groups.getById(group_id=clean_id)
            )
            
            if groups:
                return groups[0]
            return None
            
        except ApiError as e:
            logger.error(f"VK API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting VK group info: {e}")
            return None

    async def post_to_wall(
        self,
        group_id: str,
        message: str,
        attachments: Optional[list] = None,
        photo_paths: Optional[list] = None
    ) -> Optional[int]:
        try:
            clean_group_id = group_id.replace('-', '')
            owner_id = f"-{clean_group_id}"
            
            uploaded_attachments = []
            
            if photo_paths:
                loop = asyncio.get_event_loop()
                for photo_path in photo_paths:
                    try:
                        upload = vk_api.VkUpload(self.session)
                        photo = await loop.run_in_executor(
                            None,
                            lambda p=photo_path: upload.photo_wall(p, group_id=clean_group_id)
                        )
                        if photo:
                            uploaded_attachments.append(
                                f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
                            )
                    except Exception as e:
                        logger.error(f"Error uploading photo: {e}")
                        continue
            
            if attachments:
                uploaded_attachments.extend(attachments)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.api.wall.post(
                    owner_id=owner_id,
                    message=message,
                    attachments=','.join(uploaded_attachments) if uploaded_attachments else None,
                    from_group=1
                )
            )
            
            return result.get('post_id')
            
        except ApiError as e:
            logger.error(f"VK API error while posting: {e}")
            return None
        except Exception as e:
            logger.error(f"Error posting to VK wall: {e}")
            return None

    @staticmethod
    def get_auth_url(app_id: int, redirect_uri: str) -> str:
        scope = "wall,photos,groups,offline"
        return (
            f"https://oauth.vk.com/authorize?"
            f"client_id={app_id}&"
            f"redirect_uri={redirect_uri}&"
            f"display=page&"
            f"scope={scope}&"
            f"response_type=token&"
            f"v=5.131"
        )
    
    @staticmethod
    def validate_token(access_token: str) -> bool:
        try:
            session = vk_api.VkApi(token=access_token)
            api = session.get_api()
            api.users.get()
            return True
        except:
            return False
