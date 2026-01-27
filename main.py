from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

from config import BOT_TOKEN
from database import init_db
from handlers import start, communities, posts, forwarding

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(communities.router)
    dp.include_router(posts.router)
    dp.include_router(forwarding.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
