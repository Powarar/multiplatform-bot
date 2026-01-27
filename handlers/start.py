from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import async_session_maker
from models import User
from sqlalchemy import select

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
            session.add(user)
            await session.commit()

    await message.answer(
        "Привет! Я бот для публикации постов в Telegram и VK.\n\n"
        "Команды:\n"
        "/add_community — добавить канал/группу\n"
        "/my_communities — список сообществ\n"
        "/new_post — создать пост и опубликовать\n"
        "/forward_to_vk — переслать реплаем в VK\n"
        "/help — справка"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/add_community — добавить канал/группу\n"
        "/my_communities — список сообществ\n"
        "/new_post — создать пост и опубликовать\n"
        "/forward_to_vk — ответь на сообщение и отправь в VK\n"
    )
