from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from database import async_session_maker
from models import User
from services.forwarding_service import ForwardingService

router = Router()


@router.message(Command("forward_to_vk"))
async def forward_to_vk(message: Message):
    if not message.reply_to_message:
        await message.answer("Ответь этой командой на сообщение, которое надо отправить в VK.")
        return

    async with async_session_maker() as session:
        u = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = u.scalar_one_or_none()
        if not user:
            await message.answer("Сначала /start")
            return

        svc = ForwardingService(session)
        sent = await svc.forward_reply_to_all_vk(message.reply_to_message, user.id)

    await message.answer(f"✅ Отправлено в VK групп: {sent}")
