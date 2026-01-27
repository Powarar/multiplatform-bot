from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select

from database import async_session_maker
from models import User, Community, PlatformType
from services.post_service import PostService

router = Router()


class CreatePostState(StatesGroup):
    waiting_for_post_message = State()
    waiting_for_communities = State()


@router.message(Command("new_post"))
async def new_post_start(message: Message, state: FSMContext):
    await message.answer("📝 Отправь сообщение для публикации (текст/фото).")
    await state.set_state(CreatePostState.waiting_for_post_message)


@router.message(CreatePostState.waiting_for_post_message)
async def post_message_received(message: Message, state: FSMContext):
    """
    Сохраняем в FSM:
    - from_chat_id/message_id: для TG copy_message
    - text: для VK wall.post
    - photo_file_id: если прислали как фото
    - document_file_id: если прислали как документ (часто так кидают 'без сжатия')
    """
    text = (message.text or message.caption or "").strip()

    photo_file_id = message.photo[-1].file_id if message.photo else None

    document_file_id = None
    if message.document:

        mime = (message.document.mime_type or "").lower()
        if mime.startswith("image/"):
            document_file_id = message.document.file_id

    if not text and not photo_file_id and not document_file_id:
        await message.answer(
            "❌ Я не вижу ни текста, ни картинки.\n"
            "Отправь текст и/или изображение (как фото или как файл)."
        )
        return

    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        photo_file_id=photo_file_id,
        document_file_id=document_file_id,
    )

    async with async_session_maker() as session:
        u = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = u.scalar_one_or_none()
        if not user:
            await message.answer("Сначала /start")
            await state.clear()
            return

        comms = await session.execute(select(Community).where(Community.user_id == user.id))
        communities = comms.scalars().all()

    if not communities:
        await message.answer("Нет сообществ. Добавь через /add_community")
        await state.clear()
        return

    buttons = []
    for c in communities:
        emoji = "📱" if c.platform == PlatformType.TELEGRAM else "🔵"
        buttons.append([InlineKeyboardButton(text=f"☐ {emoji} {c.community_name}", callback_data=f"sel_{c.id}")])

    buttons.append([InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])

    await state.update_data(all_ids=[c.id for c in communities], selected=[])
    await message.answer("Выбери сообщества:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(CreatePostState.waiting_for_communities)


@router.callback_query(CreatePostState.waiting_for_communities)
async def community_toggle(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if callback.data == "cancel":
        await callback.message.edit_text("Отменено.")
        await state.clear()
        await callback.answer()
        return

    if callback.data.startswith("sel_"):
        comm_id = int(callback.data.split("_")[1])
        selected = set(data.get("selected", []))

        if comm_id in selected:
            selected.remove(comm_id)
        else:
            selected.add(comm_id)

        selected = list(selected)
        await state.update_data(selected=selected)

        async with async_session_maker() as session:
            result = await session.execute(select(Community).where(Community.id.in_(data["all_ids"])))
            communities = result.scalars().all()

        buttons = []
        for c in communities:
            emoji = "📱" if c.platform == PlatformType.TELEGRAM else "🔵"
            check = "☑" if c.id in selected else "☐"
            buttons.append([InlineKeyboardButton(text=f"{check} {emoji} {c.community_name}", callback_data=f"sel_{c.id}")])

        buttons.append([InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm")])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])

        await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.answer()
        return

    if callback.data == "confirm":
        selected = data.get("selected", [])
        if not selected:
            await callback.answer("Выбери хотя бы одно сообщество.", show_alert=True)
            return

        async with async_session_maker() as session:
            u = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
            user = u.scalar_one_or_none()
            if not user:
                await callback.message.edit_text("Сначала /start")
                await state.clear()
                await callback.answer()
                return

        
            post_service = PostService(session)
            sent = await post_service.publish_from_state(
                bot=callback.bot,
                user_id=user.id,
                from_chat_id=data["from_chat_id"],
                message_id=data["message_id"],
                text=data["text"],
                photo_file_id=data.get("photo_file_id"),
                document_file_id=data.get("document_file_id"),
                community_ids=selected,
            )

        await callback.message.edit_text(
            f"✅ Готово.\n"
            f"Всего выбрано: {len(selected)}\n"
            f"Успешно: {sent}"
        )
        await state.clear()
        await callback.answer()
