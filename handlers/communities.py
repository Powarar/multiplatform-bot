from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import async_session_maker
from services.community_service import CommunityService
from services.vk_service import VKService
from config import settings
import logging

logger = logging.getLogger(__name__)
router = Router()


class AddCommunityState(StatesGroup):
    waiting_for_platform = State()
    waiting_for_telegram_id = State()
    waiting_for_vk_token = State()
    waiting_for_vk_group_id = State()


@router.message(Command("add_community"))
async def add_community_start(message: Message, state: FSMContext):
    """Начало добавления сообщества"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Telegram", callback_data="platform_telegram")],
        [InlineKeyboardButton(text="🔵 VK", callback_data="platform_vk")],
        [InlineKeyboardButton(text="🐘 MAX", callback_data="platform_max")]
    ])
    await message.answer("Выберите платформу:", reply_markup=keyboard)
    await state.set_state(AddCommunityState.waiting_for_platform)


#--------------------------------------------------------------
@router.callback_query(AddCommunityState.waiting_for_platform, F.data.startswith("platform_"))
async def platform_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора платформы"""
    platform = callback.data.split("_")[1]
    await state.update_data(platform=platform)

    if platform == "telegram":
        await callback.message.edit_text(
            "📱 <b>Telegram</b>\n\n"
            "Отправьте ID канала (например: @channel или -1001234567890)\n"
            "⚠️ Бот должен быть администратором канала!",
            parse_mode="HTML"
        )
        await state.set_state(AddCommunityState.waiting_for_telegram_id)
        
    elif platform == "vk":

        auth_url = VKService.get_auth_url(settings.VK_APP_ID, settings.VK_REDIRECT_URI)
        
        await callback.message.edit_text(
            "🔵 <b>VK (ВКонтакте)</b>\n\n"
            "Для добавления сообщества VK необходим токен доступа.\n\n"
            "1️⃣ Перейдите по ссылке для авторизации:\n"
            f"<a href='{auth_url}'>Получить токен доступа</a>\n\n"
            "2️⃣ Разрешите доступ к группам\n"
            "3️⃣ Скопируйте access_token из адресной строки\n"
            "4️⃣ Отправьте токен сюда\n\n"
            "ℹ️ Токен начинается с vk1.a... и должен быть полным",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        await state.set_state(AddCommunityState.waiting_for_vk_token)
        
    else:
        await callback.message.edit_text("❌ Эта платформа пока не поддерживается")
        await state.clear()


@router.message(AddCommunityState.waiting_for_telegram_id)
async def telegram_id_received(message: Message, state: FSMContext):
    """Обработка ID Telegram канала"""
    data = await state.get_data()
    platform = data.get("platform")
    community_id = message.text.strip()

    try:
        # Проверяем доступ к каналу
        chat = await message.bot.get_chat(community_id)
        community_name = chat.title or chat.username or community_id

        async with async_session_maker() as session:
            service = CommunityService(session)
            await service.add_community(
                user_id=message.from_user.id,
                platform=platform,
                community_id=str(chat.id),
                community_name=community_name
            )

        await message.answer(
            f"✅ Канал <b>'{community_name}'</b> успешно добавлен!",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error adding Telegram channel: {e}")
        await message.answer(
            f"❌ Ошибка при добавлении канала:\n{str(e)}\n\n"
            "Убедитесь, что:\n"
            "• ID канала указан верно\n"
            "• Бот является администратором канала"
        )

    await state.clear()


@router.message(AddCommunityState.waiting_for_vk_token)
async def vk_token_received(message: Message, state: FSMContext):
    """Обработка VK токена"""
    token = message.text.strip()
    
    # Удаляем сообщение с токеном для безопасности
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем токен
    if not VKService.validate_token(token):
        await message.answer(
            "❌ Неверный токен доступа!\n\n"
            "Убедитесь, что:\n"
            "• Токен скопирован полностью\n"
            "• Вы разрешили необходимые права\n"
            "• Токен не истек"
        )
        await state.clear()
        return
    
    await state.update_data(access_token=token)
    
    await message.answer(
        "✅ Токен принят!\n\n"
        "Теперь отправьте ID или короткое имя группы VK\n\n"
        "<b>Примеры:</b>\n"
        "• club123456789\n"
        "• public123456789\n"
        "• -123456789\n"
        "• mygroup (короткое имя)\n\n"
        "ℹ️ Вы должны быть администратором группы",
        parse_mode="HTML"
    )
    await state.set_state(AddCommunityState.waiting_for_vk_group_id)


@router.message(AddCommunityState.waiting_for_vk_group_id)
async def vk_group_id_received(message: Message, state: FSMContext):
    """Обработка ID VK группы"""
    data = await state.get_data()
    platform = data.get("platform")
    access_token = data.get("access_token")
    group_id = message.text.strip()
    
    try:

        vk_service = VKService(access_token)
        

        group_info = await vk_service.get_group_info(group_id)
        
        if not group_info:
            await message.answer(
                "❌ Не удалось найти группу!\n\n"
                "Проверьте:\n"
                "• Правильность ID/имени группы\n"
                "• Является ли группа публичной\n"
                "• Есть ли у вас права администратора"
            )
            await state.clear()
            return
        
        community_name = group_info['name']
        community_id = str(group_info['id'])
        
        # Сохраняем в БД
        async with async_session_maker() as session:
            service = CommunityService(session)
            await service.add_community(
                user_id=message.from_user.id,
                platform=platform,
                community_id=community_id,
                community_name=community_name,
                access_token=access_token
            )
        
        await message.answer(
            f"✅ Группа VK <b>'{community_name}'</b> успешно добавлена!\n\n"
            f"🔗 <a href='https://vk.com/club{community_id}'>Открыть группу</a>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error adding VK community: {e}")
        await message.answer(
            f"❌ Ошибка при добавлении группы:\n{str(e)}"
        )
    
    await state.clear()


@router.message(Command("my_communities"))
async def my_communities(message: Message):
    """Показать список добавленных сообществ"""
    async with async_session_maker() as session:
        service = CommunityService(session)
        communities = await service.get_user_communities(message.from_user.id)

    if not communities:
        await message.answer("📭 У вас нет добавленных сообществ")
        return

    text = "📋 <b>Ваши сообщества:</b>\n\n"
    for comm in communities:
        if comm.platform.value == "telegram":
            emoji = "📱"
            link = f"tg://resolve?domain={comm.community_id.replace('@', '')}"
        elif comm.platform.value == "vk":
            emoji = "🔵"
            link = f"https://vk.com/club{comm.community_id}"
        else:
            emoji = "🔗"
            link = "#"
        
        text += f"{emoji} <a href='{link}'>{comm.community_name}</a> ({comm.platform.value})\n"

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
