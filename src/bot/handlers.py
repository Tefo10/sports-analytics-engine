from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
import requests
import datetime

router = Router()
API_URL = "http://127.0.0.1:8000"
user_data = {}

def save_to_history(home, away, p_l, p_e, p_v, value):
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with open("historial_apuestas.txt", "a", encoding="utf-8") as f:
            f.write(f"[{fecha}] {home} vs {away} | L:{p_l}% E:{p_e}% V:{p_v}% | Valor:{value}\n")
    except:
        pass

@router.message(Command("start"))
async def cmd_start(message: Message):
    guia = (
        "*** SOCCER AI PRO - GUIA DE USO ***\n\n"
        "1. /buscar [nombre] - Encontrar un equipo.\n"
        "2. /equipos - Lista completa de la liga.\n"
        "3. /historial - Ultimas consultas.\n\n"
        "Al elegir equipos, podras indicar si hay BAJAS para ajustar el calculo."
    )
    await message.answer(guia)

@router.message(Command("historial"))
async def cmd_historial(message: Message):
    try:
        with open("historial_apuestas.txt", "r", encoding="utf-8") as f:
            lineas = f.readlines()
            ultimas = "".join(lineas[-5:]) if lineas else "Vacio."
            await message.answer(f"HISTORIAL:\n{ultimas}")
    except:
        await message.answer("Historial no encontrado.")

@router.message(Command("buscar"))
async def cmd_buscar(message: Message):
    query = message.text.replace("/buscar", "").strip()
    if not query:
        await message.answer("Uso: /buscar Madrid")
        return
    try:
        res = requests.get(f"{API_URL}/search?query={query}").json()
        if not res:
            await message.answer("Sin resultados.")
            return
        kb = [[InlineKeyboardButton(text=t['name'], callback_data=f"sel_{t['name']}")] for t in res]
        await message.answer("Resultados:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except:
        await message.answer("API Offline.")

@router.callback_query(F.data.startswith("sel_"))
async def process_sel(call: CallbackQuery):
    name = call.data.split("_")[1]
    uid = call.message.chat.id
    if uid not in user_data or user_data[uid].get('step') == 'done':
        user_data[uid] = {'home': name, 'step': 'away'}
        await call.message.answer(f"LOCAL: {name}\nSelecciona el VISITANTE:")
    else:
        user_data[uid].update({'away': name, 'step': 'bajas'})
        btns = [
            [InlineKeyboardButton(text="Full Equipo", callback_data="abs_0")],
            [InlineKeyboardButton(text="1-2 Bajas", callback_data="abs_1")],
            [InlineKeyboardButton(text="Crisis", callback_data="abs_2")]
        ]
        await call.message.answer(f"{user_data[uid]['home']} vs {name}\nBajas del Local?", 
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@router.callback_query(F.data.startswith("abs_"))
async def process_abs(call: CallbackQuery):
    level = int(call.data.split("_")[1])
    user_data[call.message.chat.id].update({'abs': level, 'step': 'odds'})
    await call.message.answer("Cuotas (Local Empate Visita):")
    await call.answer()

@router.message()
async def process_odds(message: Message):
    uid = message.chat.id
    if uid in user_data and user_data[uid].get('step') == 'odds':
        try:
            odds = message.text.split()
            st = user_data[uid]
            teams = {t['name']: t for t in requests.get(f"{API_URL}/teams").json()}
            
            h_atk = teams[st['home']]['atk'] * {0:1.0, 1:0.85, 2:0.70}[st['abs']]
            
            payload = {
                "home_name": st['home'], "away_name": st['away'],
                "home_attack_power": h_atk, "away_defense_weakness": teams[st['away']]['def'],
                "odds": {"L": float(odds[0]), "E": float(odds[1]), "V": float(odds[2])}
            }
            res = requests.post(f"{API_URL}/predict", json=payload).json()
            p = res['probabilities']
            save_to_history(st['home'], st['away'], p['L'], p['E'], p['V'], res['value_found'])
            
            txt = f"RESULTADO: L:{p['L']}% E:{p['E']}% V:{p['V']}%\n"
            if res['value_found']: txt += f"VALOR: {', '.join(res['value_found'].keys())}"
            await message.answer(txt)
            user_data[uid]['step'] = 'done'
        except:
            await message.answer("Error. Formato: 1.85 3.50 4.10")
