import datetime

import requests
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.models.brain import BettingBrain
from src.utils.database import DBManager

router = Router()
API_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 10
user_data = {}
brain = BettingBrain()
db = DBManager()


def pct(probability):
    return f"{probability * 100:.2f}"


def save_to_history(home, away, p_l, p_e, p_v, value):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with open("historial_apuestas.txt", "a", encoding="utf-8") as file:
            file.write(
                f"[{timestamp}] {home} vs {away} | "
                f"L:{pct(p_l)}% E:{pct(p_e)}% V:{pct(p_v)}% | Valor:{value}\n"
            )
    except OSError:
        pass


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user:
        db.register_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )
        db.log_event(message.from_user.id, "START")

    guide = (
        "SOCCER AI PRO - GUIA DE USO\n\n"
        "1. /buscar [nombre] - Encontrar un equipo.\n"
        "2. /equipos - Lista completa de la liga.\n"
        "3. /historial - Ultimas consultas.\n\n"
        "Al elegir equipos, puedes indicar bajas para ajustar el calculo."
    )
    await message.answer(guide)


@router.message(Command("equipos"))
async def cmd_equipos(message: Message):
    try:
        teams = requests.get(f"{API_URL}/teams", timeout=REQUEST_TIMEOUT).json()
        if message.from_user:
            db.log_event(message.from_user.id, "LIST_TEAMS")
        names = [team["name"] for team in teams]
        await message.answer("Equipos disponibles:\n" + "\n".join(names))
    except Exception:
        await message.answer("No pude consultar la lista de equipos.")


@router.message(Command("historial"))
async def cmd_historial(message: Message):
    try:
        with open("historial_apuestas.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()
            last_lines = "".join(lines[-5:]) if lines else "Vacio."
            await message.answer(f"HISTORIAL:\n{last_lines}")
    except OSError:
        await message.answer("Historial no encontrado.")


@router.message(Command("buscar"))
async def cmd_buscar(message: Message):
    query = message.text.replace("/buscar", "").strip()
    if not query:
        await message.answer("Uso: /buscar Madrid")
        return

    try:
        if message.from_user:
            db.log_event(message.from_user.id, "SEARCH", query)
        response = requests.get(
            f"{API_URL}/search", params={"query": query}, timeout=REQUEST_TIMEOUT
        ).json()
        if not response:
            await message.answer("Sin resultados.")
            return
        keyboard = [
            [InlineKeyboardButton(text=team["name"], callback_data=f"sel_{team['name']}")]
            for team in response
        ]
        await message.answer(
            "Resultados:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    except Exception:
        await message.answer("API offline.")


@router.callback_query(F.data.startswith("sel_"))
async def process_sel(call: CallbackQuery):
    name = call.data.split("_", 1)[1]
    user_id = call.message.chat.id

    if user_id not in user_data or user_data[user_id].get("step") == "done":
        user_data[user_id] = {"home": name, "step": "away"}
        await call.message.answer(f"LOCAL: {name}\nSelecciona el VISITANTE:")
    else:
        user_data[user_id].update({"away": name, "step": "bajas"})
        buttons = [
            [InlineKeyboardButton(text="Full Equipo", callback_data="abs_0")],
            [InlineKeyboardButton(text="1-2 Bajas", callback_data="abs_1")],
            [InlineKeyboardButton(text="Crisis", callback_data="abs_2")],
        ]
        await call.message.answer(
            f"{user_data[user_id]['home']} vs {name}\nBajas del Local?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
    await call.answer()


@router.callback_query(F.data.startswith("abs_"))
async def process_abs(call: CallbackQuery):
    level = int(call.data.split("_", 1)[1])
    user_data[call.message.chat.id].update({"abs": level, "step": "odds"})
    await call.message.answer("Cuotas (Local Empate Visita):")
    await call.answer()


@router.message()
async def process_odds(message: Message):
    user_id = message.chat.id
    if user_id not in user_data or user_data[user_id].get("step") != "odds":
        return

    try:
        odds = message.text.split()
        state = user_data[user_id]
        teams = {
            team["name"]: team
            for team in requests.get(f"{API_URL}/teams", timeout=REQUEST_TIMEOUT).json()
        }

        home_attack = brain.apply_absences(teams[state["home"]]["atk"], state["abs"])
        payload = {
            "home_name": state["home"],
            "away_name": state["away"],
            "home_attack_power": home_attack,
            "away_defense_weakness": teams[state["away"]]["def"],
            "odds": {"L": float(odds[0]), "E": float(odds[1]), "V": float(odds[2])},
        }
        result = requests.post(
            f"{API_URL}/predict", json=payload, timeout=REQUEST_TIMEOUT
        ).json()
        probabilities = result["probabilities"]
        save_to_history(
            state["home"],
            state["away"],
            probabilities["L"],
            probabilities["E"],
            probabilities["V"],
            result["value_found"],
        )

        text = (
            f"RESULTADO: L:{pct(probabilities['L'])}% "
            f"E:{pct(probabilities['E'])}% "
            f"V:{pct(probabilities['V'])}%\n"
        )
        if result["value_found"]:
            text += f"VALOR: {', '.join(result['value_found'].keys())}"
        await message.answer(text)
        user_data[user_id]["step"] = "done"
        if message.from_user:
            db.log_event(message.from_user.id, "PREDICT", f"{state['home']} vs {state['away']}")
    except Exception:
        await message.answer("Error. Formato: 1.85 3.50 4.10")
