from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import async_session_maker
from services.community_service import CommunityService
from services.post_service import PostService
from sqlalchemy import select
from models import Community, PlatformType


router = Router()


class CreatePostState(StatesGroup):
    waiting_for_post_message = State()
    waiting_for_communities = State()


@router.message(Command("new_post"))
async def new_post_start(message: Message, state: FSMContext):
    await message.answer(
        "📝 Отправьте сообщение для публикации (с текстом, фото):\n\n"
    )
    await state.set_state(CreatePostState.waiting_for_post_message)


@router.message(CreatePostState.waiting_for_post_message)
async def post_message_received(message: Message, state: FSMContext):
    await state.update_data(
        message_id=message.message_id,
        from_chat_id=message.chat.id
    )

    async with async_session_maker() as session:
        service = CommunityService(session)
        communities = await service.get_user_communities(message.from_user.id)

    if not communities:
        await message.answer("❌ У вас нет добавленных сообществ. Используйте /add_community")
        await state.clear()
        return

    buttons = []
    for comm in communities:
        emoji = "📱" if comm.platform == PlatformType.TELEGRAM else "🔗"
        buttons.append([
            InlineKeyboardButton(
                text=f"☐ {emoji} {comm.community_name}",
                callback_data=f"select_comm_{comm.id}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_post")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")])

    await state.update_data(communities=communities, selected_communities=[])
    await message.answer(
        "🎯 Выберите сообщества для отправки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(CreatePostState.waiting_for_communities)


@router.callback_query(CreatePostState.waiting_for_communities)
async def community_toggled(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if callback.data == "cancel_post":
        await callback.message.edit_text("❌ Создание поста отменено")
        await state.clear()
        return

    if callback.data.startswith("select_comm_"):
        comm_id = int(callback.data.split("_")[-1])
        selected = data.get("selected_communities", [])

        if comm_id in selected:
            selected.remove(comm_id)
        else:
            selected.append(comm_id)

        await state.update_data(selected_communities=selected)

        buttons = []
        for comm in data.get("communities", []):
            emoji = "📱" if comm.platform == PlatformType.TELEGRAM else "🔗"
            check = "☑" if comm.id in selected else "☐"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{check} {emoji} {comm.community_name}",
                    callback_data=f"select_comm_{comm.id}"
                )
            ])

        buttons.append([InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_post")])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")])

        await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.answer()

    elif callback.data == "confirm_post":
        data = await state.get_data()
        selected = data.get("selected_communities", [])

        if not selected:
            await callback.answer("Выберите хотя бы одно сообщество!", show_alert=True)
            return

        message_id = data.get("message_id")
        from_chat_id = data.get("from_chat_id")

        async with async_session_maker() as session:
            post_service = PostService(session)
            await post_service.create_post(
                user_id=callback.from_user.id,
                message_id=message_id,
                from_chat_id=from_chat_id,
                community_ids=selected
            )

            result = await session.execute(
                select(Community).where(Community.id.in_(selected))
            )
            communities = result.scalars().all()

        bot = callback.bot
        sent_count = 0

        for comm in communities:
            if comm.platform == PlatformType.TELEGRAM:
                try:
                    await bot.copy_message(
                        chat_id=comm.community_id,
                        from_chat_id=from_chat_id,
                        message_id=message_id
                    )
                    sent_count += 1
                except Exception as e:
                    print(f"Error sending to {comm.community_name}: {e}")

        await callback.message.edit_text(
            f"✅ Пост отправлен в {sent_count} сообщество(в)!\n\n"
            f"📊 Всего: {len(selected)}\n"
            f"Успешно: {sent_count}"
        )
        await state.clear()


@router.message(Command("my_posts"))
async def my_posts(message: Message):
    async with async_session_maker() as session:
        service = PostService(session)
        posts = await service.get_user_posts(message.from_user.id)

    if not posts:
        await message.answer("📭 У вас пока нет постов")
        return

    text = "📝 Ваши посты:\n\n"
    for post in posts:
        text += f"🆔 {post.id}: message_id={post.message_id}\n"
        text += f"📅 {post.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    await message.answer(text)
