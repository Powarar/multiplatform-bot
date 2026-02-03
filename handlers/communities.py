from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import logging

from sqlalchemy import select

from database import async_session_maker
from models import User, Community, PlatformType
from services.vk_service import VKService

router = Router()
logger = logging.getLogger(__name__)


class AddCommunityState(StatesGroup):
    waiting_for_platform = State()
    waiting_for_tg_id = State()
    waiting_for_tg_name = State()
    waiting_for_vk_token = State()


@router.message(Command("add_community"))
async def add_community(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Telegram", callback_data="add_tg")],
        [InlineKeyboardButton(text="🔵 VK", callback_data="add_vk")],
    ])
    await message.answer("Выбери платформу:", reply_markup=kb)
    await state.set_state(AddCommunityState.waiting_for_platform)


@router.callback_query(AddCommunityState.waiting_for_platform, F.data.in_(["add_tg", "add_vk"]))
async def platform_selected(callback: CallbackQuery, state: FSMContext):
    if callback.data == "add_tg":
        await state.update_data(platform=PlatformType.TELEGRAM)
        await callback.message.edit_text(
            "Отправь ID/username канала.\n\n"
            "Примеры:\n"
            "@mychannel\n"
            "-1001234567890\n\n"
            "⚠️ Бот должен быть админом канала."
        )
        await state.set_state(AddCommunityState.waiting_for_tg_id)

    if callback.data == "add_vk":
        await state.update_data(platform=PlatformType.VK)
        await callback.message.edit_text(
            "Как получить токен VK группы:\n\n"
            "1. Открой группу VK\n"
            "2. Управление → перейди по URL:\n"
            "   vk.com/club{ID}?act=tokens\n\n"
            "3. Создай ключ с правами:\n"
            "   • управление сообществом\n"
            "   • фото\n"
            "   • стены (wall)\n\n"
            "4. Отправь мне токен (начинается с vk1.a.)\n\n"
            "Токен автоматически определит твою группу."
        )
        await state.set_state(AddCommunityState.waiting_for_vk_token)

    await callback.answer()


@router.message(AddCommunityState.waiting_for_tg_id)
async def tg_id_received(message: Message, state: FSMContext):
    tg_id = message.text.strip()
    await state.update_data(community_id=tg_id)
    await message.answer("Теперь отправь название (как будет отображаться).")
    await state.set_state(AddCommunityState.waiting_for_tg_name)


@router.message(AddCommunityState.waiting_for_tg_name)
async def tg_name_received(message: Message, state: FSMContext):
    name = message.text.strip()
    data = await state.get_data()
    community_id = data["community_id"]

    async with async_session_maker() as session:
        u = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = u.scalar_one_or_none()
        if not user:
            await message.answer("Сначала /start")
            await state.clear()
            return

        session.add(Community(
            user_id=user.id,
            platform=PlatformType.TELEGRAM,
            community_id=community_id,
            community_name=name,
            access_token=None
        ))
        await session.commit()

    await message.answer(f"✅ Telegram-канал добавлен: {name}")
    await state.clear()


@router.message(AddCommunityState.waiting_for_vk_token)
async def vk_token_received(message: Message, state: FSMContext):
    token = message.text.strip()

    # Удаляем сообщение с токеном для безопасности
    try:
        await message.delete()
    except Exception:
        pass

    # Валидация токена
    if not VKService.validate_token(token):
        await message.answer(
            "❌ Токен невалидный.\n\n"
            "Проверь что токен:\n"
            "• Скопирован полностью\n"
            "• Начинается с vk1.a.\n"
            "• Имеет права на группу\n\n"
            "Попробуй ещё раз или /add_community"
        )
        return

    await state.update_data(vk_token=token)
    
    # Автоматически определяем группу по токену
    vk = VKService(token)
    try:
        loop = asyncio.get_event_loop()
        groups = await loop.run_in_executor(None, lambda: vk.api.groups.getById())
        
        if not groups:
            await message.answer("❌ Не удалось определить группу по токену.")
            await state.clear()
            return
            
        group = groups[0]
        group_id = str(group["id"])
        group_name = group.get("name", f"VK {group_id}")
        
        async with async_session_maker() as session:
            u = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
            user = u.scalar_one_or_none()
            if not user:
                await message.answer("Сначала /start")
                await state.clear()
                return

            # Проверяем дубликаты
            exists = await session.execute(
                select(Community).where(
                    Community.user_id == user.id,
                    Community.platform == PlatformType.VK,
                    Community.community_id == group_id
                )
            )
            if exists.scalar_one_or_none():
                await message.answer("ℹ️ Эта группа уже добавлена.")
                await state.clear()
                return

            session.add(Community(
                user_id=user.id,
                platform=PlatformType.VK,
                community_id=group_id,
                community_name=group_name,
                access_token=token
            ))
            await session.commit()

        await message.answer(
            f"✅ VK группа добавлена!\n\n"
            f"📝 {group_name}\n"
            f"🆔 {group_id}\n\n"
            f"Теперь /new_post для постинга с фото! 📸"
        )
        await state.clear()
            
    except Exception as e:
        logger.error(f"Ошибка добавления VK группы: {e}")
        await message.answer(
            f"❌ Ошибка: {str(e)}\n\n"
            "Попробуй ещё раз или /add_community"
        )
        await state.clear()


@router.message(Command("my_communities"))
async def my_communities(message: Message):
    async with async_session_maker() as session:
        u = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = u.scalar_one_or_none()
        if not user:
            await message.answer("Сначала /start")
            return

        result = await session.execute(select(Community).where(Community.user_id == user.id))
        comms = result.scalars().all()

    if not comms:
        await message.answer("Пока нет сообществ. Добавь через /add_community")
        return

    lines = ["Твои сообщества:\n"]
    for c in comms:
        prefix = "📱 TG" if c.platform == PlatformType.TELEGRAM else "🔵 VK"
        token_status = " ✅" if c.access_token else " ❌"
        lines.append(f"{prefix} — {c.community_name} ({c.community_id}){token_status}")

    await message.answer("\n".join(lines))
