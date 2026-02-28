from aiogram import Router, types
from aiogram.filters import Command
from src.utils.database import DBManager

router = Router()
db = DBManager()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    db.register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    db.log_event(message.from_user.id, "START")
    await message.answer("⚽ **Predictor Pro v3.0 (Anti-Block)**\nRegistrado correctamente. Analizaré los datos sigilosamente.")
