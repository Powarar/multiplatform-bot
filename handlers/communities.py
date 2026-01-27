from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select

from database import async_session_maker
from models import User, Community, PlatformType
from services.vk_service import VKService

router = Router()


class AddCommunityState(StatesGroup):
    waiting_for_platform = State()

    waiting_for_tg_id = State()
    waiting_for_tg_name = State()

    waiting_for_vk_token = State()
    waiting_for_vk_group = State()


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
            "Бот должен быть админом канала."
        )
        await state.set_state(AddCommunityState.waiting_for_tg_id)

    if callback.data == "add_vk":
        await state.update_data(platform=PlatformType.VK)
        await callback.message.edit_text(
            "Отправь **токен сообщества VK**.\n\n"
            "Настройки группы → Управление → API → Ключи доступа.\n"
            "Права: wall, photos.",
            parse_mode="Markdown"
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

    try:
        await message.delete()
    except Exception:
        pass

    if not VKService.validate_token(token):
        await message.answer(
            "❌ Токен невалидный.\n"
            "Проверь что он полный и имеет права wall/photos.\n\n"
            "Отправь токен ещё раз."
        )
        return

    await state.update_data(vk_token=token)
    await message.answer(
        "✅ Токен принят.\n"
        "Теперь отправь ID / screen_name / ссылку группы.\n\n"
        "Примеры:\n"
        "mygroup\n"
        "123456789\n"
        "vk.com/mygroup"
    )
    await state.set_state(AddCommunityState.waiting_for_vk_group)


@router.message(AddCommunityState.waiting_for_vk_group)
async def vk_group_received(message: Message, state: FSMContext):
    group_input = message.text.strip()
    data = await state.get_data()
    token = data["vk_token"]

    vk = VKService(token)
    group = await vk.get_group_info(group_input)
    if not group:
        await message.answer("❌ Не смог найти группу. Проверь ID/screen_name и права токена.")
        return

    group_id = str(group["id"])
    group_name = group.get("name", f"VK {group_id}")

    async with async_session_maker() as session:
        u = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = u.scalar_one_or_none()
        if not user:
            await message.answer("Сначала /start")
            await state.clear()
            return

        exists = await session.execute(
            select(Community).where(
                Community.user_id == user.id,
                Community.platform == PlatformType.VK,
                Community.community_id == group_id
            )
        )
        if exists.scalar_one_or_none():
            await message.answer("ℹ️ Эта VK группа уже добавлена.")
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

    await message.answer(f"✅ VK группа добавлена: {group_name} (id={group_id})")
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

    lines = ["Ваши сообщества:\n"]
    for c in comms:
        prefix = "📱 TG" if c.platform == PlatformType.TELEGRAM else "🔵 VK"
        token_ok = "" if c.platform == PlatformType.TELEGRAM else ("✅token" if c.access_token else "❌token")
        lines.append(f"{prefix} — {c.community_name} ({c.community_id}) {token_ok}")

    await message.answer("\n".join(lines))
