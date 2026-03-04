from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
import requests
import datetime
import asyncio

router = Router()
API_URL = "http://127.0.0.1:8000"
user_data = {}

# --- UTILIDADES DE INTERFAZ ---

def main_menu_kb():
    """Genera el menú principal con botones para evitar escribir."""
    kb = [
        [InlineKeyboardButton(text="🏟️ Listado de Equipos", callback_data="menu_equipos")],
        [InlineKeyboardButton(text="🔍 Buscador Rápido", callback_data="menu_buscar")],
        [InlineKeyboardButton(text="📜 Ver mi Historial", callback_data="menu_historial")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def save_to_history(home, away, p_l, p_e, p_v, value):
    """Guarda el análisis en un archivo de texto local."""
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with open("historial_apuestas.txt", "a", encoding="utf-8") as f:
            f.write(f"[{fecha}] {home} vs {away} | L:{p_l}% E:{p_e}% V:{p_v}% | Valor:{value}\n")
    except:
        pass

# --- COMANDOS Y MENÚS ---

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Punto de entrada con menú de botones."""
    user_data[message.from_user.id] = {} 
    await message.answer(
        "⚽ **SOCCER AI PRO - SISTEMA DE PREDICCIÓN**\n\n"
        "Bienvenido. Utiliza los botones de abajo para navegar sin escribir:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_equipos")
async def btn_equipos(call: CallbackQuery):
    """Muestra la lista de equipos directamente desde la API."""
    try:
        res = requests.get(f"{API_URL}/teams").json()
        teams = res if isinstance(res, list) else res.get('teams', [])
        
        # Generar botones usando el campo 'name' del JSON
        kb = [[InlineKeyboardButton(text=f"🏟️ {t['name']}", callback_data=f"sel_{t['name']}")] for t in teams[:15]]
        
        await call.message.edit_text(
            "📋 **SELECCIÓN DE EQUIPO**\nSelecciona el equipo que juega como **LOCAL**:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode="Markdown"
        )
    except Exception as e:
        await call.message.answer(f"❌ Error al conectar con la API: {e}")
    await call.answer()

@router.callback_query(F.data == "menu_buscar")
async def btn_buscar(call: CallbackQuery):
    await call.message.answer("🔍 Escribe el nombre del equipo. Ejemplo: `/buscar Madrid`", parse_mode="Markdown")
    await call.answer()

@router.message(Command("buscar"))
async def cmd_buscar(message: Message):
    query = message.text.replace("/buscar", "").strip()
    if not query:
        await message.answer("⚠️ Por favor escribe un nombre. Ej: `/buscar Barcelona`")
        return
    try:
        res = requests.get(f"{API_URL}/search?query={query}").json()
        if not res:
            await message.answer("❌ No se encontraron coincidencias.")
            return
        kb = [[InlineKeyboardButton(text=f"✅ {t['name']}", callback_data=f"sel_{t['name']}")] for t in res]
        await message.answer(f"🔎 Resultados para '{query}':", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except:
        await message.answer("⚠️ API fuera de línea.")

# --- FLUJO DE SELECCIÓN ---

@router.callback_query(F.data.startswith("sel_"))
async def process_sel(call: CallbackQuery):
    """Maneja la selección de Local y luego Visitante."""
    name = call.data.split("_", 1)[1]
    uid = call.from_user.id
    
    if uid not in user_data or 'home' not in user_data[uid] or user_data[uid].get('step') == 'done':
        user_data[uid] = {'home': name, 'step': 'away'}
        await call.message.answer(
            f"🏠 **LOCAL SELECCIONADO:** {name}\n\n"
            f"Ahora selecciona al equipo **VISITANTE** (usa /equipos o busca):",
            parse_mode="Markdown"
        )
    else:
        user_data[uid].update({'away': name, 'step': 'bajas'})
        btns = [
            [InlineKeyboardButton(text="🟢 Equipo Completo", callback_data="abs_0")],
            [InlineKeyboardButton(text="🟡 1-2 Bajas", callback_data="abs_1")],
            [InlineKeyboardButton(text="🔴 Crisis de Bajas", callback_data="abs_2")]
        ]
        await call.message.answer(
            f"🆚 **PARTIDO:** {user_data[uid]['home']} vs {name}\n\n"
            f"¿Cuál es el estado de bajas del equipo local?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
            parse_mode="Markdown"
        )
    await call.answer()

@router.callback_query(F.data.startswith("abs_"))
async def process_abs(call: CallbackQuery):
    """Paso para decidir el origen de las cuotas."""
    uid = call.from_user.id
    level = int(call.data.split("_")[1])
    user_data[uid].update({'abs': level, 'step': 'odds_choice'})
    
    kb = [
        [InlineKeyboardButton(text="🤖 Usar Cuotas de la IA", callback_data="odds_ai")],
        [InlineKeyboardButton(text="✍️ Ingresar Cuotas Manuales", callback_data="odds_manual")]
    ]
    await call.message.answer(
        "💰 **SISTEMA DE CUOTAS**\n\n"
        "¿Deseas usar las cuotas recomendadas por la base de datos o ingresar las cuotas actuales de tu casa de apuestas?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="Markdown"
    )
    await call.answer()

@router.callback_query(F.data == "odds_ai")
async def process_ai_odds(call: CallbackQuery):
    uid = call.from_user.id
    st = user_data[uid]
    try:
        # Consultar cuotas sugeridas en la API
        res = requests.get(f"{API_URL}/teams").json()
        teams = {t['name']: t for t in (res if isinstance(res, list) else res.get('teams', []))}
        
        # Obtener valores sug_l y sug_v (o valores por defecto)
        h_data = teams[st['home']]
        odds = [h_data.get('sug_l', 1.85), 3.40, h_data.get('sug_v', 4.20)]
        
        await execute_prediction(call.message, uid, odds)
    except:
        await call.message.answer("❌ No se pudieron obtener cuotas sugeridas.")
    await call.answer()

@router.callback_query(F.data == "odds_manual")
async def process_manual_odds(call: CallbackQuery):
    user_data[call.from_user.id]['step'] = 'waiting_odds'
    await call.message.answer("✍️ **Envía las cuotas separadas por espacio.**\nEjemplo: `2.10 3.25 4.10` (Local Empate Visita)")
    await call.answer()

# --- MOTOR DE PREDICCIÓN Y RESULTADOS ---

async def execute_prediction(message, uid, odds):
    st = user_data[uid]
    try:
        # Obtener datos técnicos (atk/def) confirmados en API
        res_teams = requests.get(f"{API_URL}/teams").json()
        teams_list = res_teams if isinstance(res_teams, list) else res_teams.get('teams', [])
        teams = {t['name']: t for t in teams_list}
        
        # Modificar ataque local según el nivel de bajas
        modificador = {0: 1.0, 1: 0.85, 2: 0.70}[st['abs']]
        h_atk = float(teams[st['home']]['atk']) * modificador
        
        payload = {
            "home_name": st['home'], 
            "away_name": st['away'],
            "home_attack_power": h_atk, 
            "away_defense_weakness": float(teams[st['away']]['def']),
            "odds": {"L": float(odds[0]), "E": float(odds[1]), "V": float(odds[2])}
        }
        
        # Enviar a la Inferencia de Poisson
        res = requests.post(f"{API_URL}/predict", json=payload).json()
        p = res['probabilities']
        
        # --- DISEÑO DE RESPUESTA ENTENDIBLE ---
        txt = (
            f"🎯 **RESULTADO DEL ANÁLISIS**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏟️ **Partido:** {st['home']} vs {st['away']}\n\n"
            f"📈 **Probabilidades de éxito:**\n"
            f"🏠 **Victoria Local:** `{p['L']}%` \n"
            f"🤝 **Empate:** `{p['E']}%` \n"
            f"🚀 **Victoria Visitante:** `{p['V']}%` \n\n"
            f"💰 **Cuotas utilizadas:**\n"
            f"`{odds[0]} (L)` | `{odds[1]} (E)` | `{odds[2]} (V)`\n"
        )

        if res.get('value_found'):
            # Traducir L, E, V a palabras completas para el usuario
            dic_trad = {"L": "Victoria Local", "E": "Empate", "V": "Victoria Visitante"}
            encontrados = [dic_trad.get(k, k) for k in res['value_found'].keys()]
            
            txt += (
                f"\n🔥 **¡OPORTUNIDAD DE VALOR!**\n"
                f"La IA detectó que la cuota es rentable en:\n"
                f"👉 **{', '.join(encontrados)}**\n"
            )
        else:
            txt += "\n⚖️ **Sin Valor Significativo:** Las cuotas son justas para el riesgo."

        await message.answer(txt, parse_mode="Markdown", reply_markup=main_menu_kb())
        save_to_history(st['home'], st['away'], p['L'], p['E'], p['V'], res.get('value_found'))
        user_data[uid]['step'] = 'done'

    except Exception as e:
        await message.answer(f"❌ Error en el motor de cálculo: {e}")

@router.message()
async def capture_manual_odds(message: Message):
    uid = message.from_user.id
    if uid in user_data and user_data[uid].get('step') == 'waiting_odds':
        odds = message.text.split()
        if len(odds) == 3:
            await execute_prediction(message, uid, odds)
        else:
            await message.answer("⚠️ Formato incorrecto. Debes enviar 3 números. Ej: `1.8 3.5 4.0`")

@router.callback_query(F.data == "menu_historial")
async def btn_historial(call: CallbackQuery):
    try:
        with open("historial_apuestas.txt", "r", encoding="utf-8") as f:
            lineas = f.readlines()
            # Mostrar últimos 5 registros
            ultimas = "".join(lineas[-5:]) if lineas else "Aún no tienes registros."
            await call.message.answer(f"📜 **ÚLTIMOS ANÁLISIS:**\n\n{ultimas}", parse_mode="Markdown")
    except:
        await call.message.answer("📭 No se encontró el archivo de historial.")
    await call.answer()
