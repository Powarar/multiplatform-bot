from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from config import settings

router = Router()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("❌ У вас нет прав администратора")
        return

    await message.answer(
        "👑 Админ панель\n\n"
        "Доступные команды:\n"
        "/stats - Статистика бота"
    )

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return

    from database import async_session_maker
    from sqlalchemy import select, func
    from models import User, Post, Community

    async with async_session_maker() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        posts_count = await session.scalar(select(func.count(Post.id)))
        communities_count = await session.scalar(select(func.count(Community.id)))

    await message.answer(
        f"📊 Статистика:\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📝 Постов: {posts_count}\n"
        f"🏘 Сообществ: {communities_count}"
    )
