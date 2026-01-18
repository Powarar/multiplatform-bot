from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import async_session_maker
from services.community_service import CommunityService

router = Router()

class AddCommunityState(StatesGroup):
    waiting_for_platform = State()
    waiting_for_telegram_id = State()

@router.message(Command("add_community"))
async def add_community_start(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Telegram", callback_data="platform_telegram")],
        [InlineKeyboardButton(text="🔵 VK", callback_data="platform_vk")],
        [InlineKeyboardButton(text="🐘 MAX", callback_data="platform_MAX")]
    ])
    await message.answer("Выберите платформу:", reply_markup=keyboard)
    await state.set_state(AddCommunityState.waiting_for_platform)

@router.callback_query(AddCommunityState.waiting_for_platform, F.data.startswith("platform_"))
async def platform_selected(callback: CallbackQuery, state: FSMContext):
    platform = callback.data.split("_")[1]
    await state.update_data(platform=platform)

    if platform == "telegram":
        await callback.message.edit_text(
            "📱 Telegram\n\n"
            "Отправьте ID канала (например: @channel или -1001234567890)\n"
            "Бот должен быть администратором канала!"
        )
        await state.set_state(AddCommunityState.waiting_for_telegram_id)
    else:
        await callback.message.edit_text("❌ Эта платформа пока не поддерживается")
        await state.clear()

@router.message(AddCommunityState.waiting_for_telegram_id)
async def community_type_selected(message: Message, state: FSMContext):
    data = await state.get_data()
    platform = data.get("platform")
    community_id = message.text.strip()

    try:
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

        await message.answer(f"✅ Канал '{community_name}' добавлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

    await state.clear()

@router.message(Command("my_communities"))
async def my_communities(message: Message):
    async with async_session_maker() as session:
        service = CommunityService(session)
        communities = await service.get_user_communities(message.from_user.id)

    if not communities:
        await message.answer("📭 У вас нет добавленных сообществ")
        return

    text = "📋 Ваши сообщества:\n\n"
    for comm in communities:
        emoji = "📱" if comm.platform == "telegram" else "🔗"
        text += f"{emoji} {comm.community_name} ({comm.platform})\n"

    await message.answer(text)
