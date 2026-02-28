import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from src.bot.handlers import router

# Forzar codificacion UTF-8 en Windows para evitar errores de consola
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

async def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("ERROR: Define TELEGRAM_TOKEN en el archivo .env")
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    print("LOG: Bot iniciado correctamente...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
