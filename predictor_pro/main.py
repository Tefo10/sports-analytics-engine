import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from src.bot.handlers import router

load_dotenv()

async def main():
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    dp = Dispatcher()
    dp.include_router(router)
    print("íº€ Bot multi-usuario iniciado...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
