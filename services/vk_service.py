import vk_api
from vk_api.exceptions import ApiError
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class VKService:
    """Сервис для работы с VK API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = vk_api.VkApi(token=access_token)
        self.api = self.session.get_api()
    
    async def get_group_info(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о группе/сообществе"""
        try:
            # Убираем префиксы если есть (club, public, event)
            clean_id = group_id.replace('club', '').replace('public', '').replace('event', '')
            
            # Если это короткое имя (screen_name), получаем ID
            if not clean_id.isdigit() and not clean_id.startswith('-'):
                result = self.api.utils.resolveScreenName(screen_name=clean_id)
                if result and result['type'] == 'group':
                    clean_id = str(result['object_id'])
                else:
                    return None
            
            # Убираем минус если есть
            clean_id = clean_id.replace('-', '')
            
            # Получаем информацию о группе
            groups = self.api.groups.getById(group_id=clean_id)
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
        """
        Опубликовать пост на стене группы
        
        Args:
            group_id: ID группы (без минуса)
            message: Текст поста
            attachments: Список вложений в формате type{owner_id}_{media_id}
            photo_paths: Пути к фотографиям для загрузки
            
        Returns:
            ID опубликованного поста или None при ошибке
        """
        try:
            owner_id = f"-{group_id.replace('-', '')}"
            
            uploaded_attachments = []
            
            # Загружаем фото если есть
            if photo_paths:
                upload = vk_api.VkUpload(self.session)
                for photo_path in photo_paths:
                    photo = upload.photo_wall(
                        photo_path,
                        group_id=group_id.replace('-', '')
                    )
                    uploaded_attachments.append(
                        f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
                    )
            
            # Добавляем переданные вложения
            if attachments:
                uploaded_attachments.extend(attachments)
            
            # Публикуем пост
            result = self.api.wall.post(
                owner_id=owner_id,
                message=message,
                attachments=','.join(uploaded_attachments) if uploaded_attachments else None,
                from_group=1  # Публикация от имени группы
            )
            
            return result['post_id']
            
        except ApiError as e:
            logger.error(f"VK API error while posting: {e}")
            return None
        except Exception as e:
            logger.error(f"Error posting to VK wall: {e}")
            return None
    
    @staticmethod
    def get_auth_url(app_id: int, redirect_uri: str) -> str:
        """Получить URL для авторизации пользователя"""
        scope = "wall,photos,groups,offline"  # offline для permanent token
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
        """Проверить валидность токена"""
        try:
            session = vk_api.VkApi(token=access_token)
            api = session.get_api()
            api.users.get()
            return True
        except:
            return False
