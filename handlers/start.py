from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🤖 Добро пожаловать в бота для мультиплатформенных постов!\n\n"
        "Доступные команды:\n"
        "/add_community - Добавить сообщество\n"
        "/my_communities - Мои сообщества\n"
        "/new_post - Создать новый пост\n"
        "/my_posts - Мои посты"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 Помощь:\n\n"
        "1. Добавьте канал командой /add_community\n"
        "2. Создайте пост командой /new_post\n"
        "3. Выберите каналы для публикации\n"
        "4. Готово! Пост опубликован 🎉"
    )
