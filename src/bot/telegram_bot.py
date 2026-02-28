import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import datetime
import schedule
import threading
import time

TOKEN = "TU_TELEGRAM_TOKEN_AQUI"
bot = telebot.TeleBot(TOKEN)
API_URL = "http://127.0.0.1:8000"

user_state = {}

# --- UTILIDADES ---
def save_to_history(home, away, p_l, p_e, p_v, value):
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("historial_apuestas.txt", "a", encoding="utf-8") as f:
        linea = f"[{fecha}] {home} vs {away} | L:{p_l}% E:{p_e}% V:{p_v}% | Valor:{value}\n"
        f.write(linea)

# --- OPCIÃ“N A: ALERTAS MATUTINAS (9:00 AM) ---
def morning_alerts():
    try:
        opps = requests.get(f"{API_URL}/scanner").json()
        if opps:
            msg = "í³¢ *OPORTUNIDADES DE HOY*\n\n"
            for o in opps:
                msg += f"{o['type']}: {o['match']}\ní¾¯ Prob: {o['prob']}% | í²° Sugerida: {o['sug']}\n\n"
            print("Alertas enviadas.")
    except:
        print("Error en el escÃ¡ner matutino.")

def run_scheduler():
    schedule.every().day.at("09:00").do(morning_alerts)
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=run_scheduler, daemon=True).start()

# --- COMANDOS ---
@bot.message_handler(commands=['start', 'help', 'menu'])
def send_welcome(message):
    guia = (
        "í´– *GUÃA DE USO - SOCCER AI PRO*\n\n"
        "Este bot utiliza IA y estadÃ­stica de xG para encontrar valor en apuestas.\n\n"
        "í³Œ *COMANDOS PRINCIPALES:*\n"
        "1ï¸âƒ£ `/buscar [nombre]` : Encuentra un equipo rÃ¡pido (Ej: `/buscar Madrid`).\n"
        "2ï¸âƒ£ `/equipos` : Lista completa de la liga paginada de 10 en 10.\n"
        "3ï¸âƒ£ `/historial` : Muestra tus Ãºltimas 5 predicciones guardadas.\n"
        "4ï¸âƒ£ `/live` : Activa alertas para partidos en curso (Remontadas).\n\n"
        "í»  *FUNCIONES ESPECIALES:*\n"
        "â€¢ *Factor de Bajas:* Al analizar, podrÃ¡s indicar si el equipo tiene bajas para ajustar la precisiÃ³n.\n"
        "â€¢ *Alertas de Valor:* Cada maÃ±ana a las 9:00 AM, escaneo la jornada en busca de cuotas mal puestas.\n"
        "â€¢ *Auto-Guardado:* Todas tus consultas se guardan en el historial."
    )
    bot.send_message(message.chat.id, guia, parse_mode="Markdown")

@bot.message_handler(commands=['historial'])
def show_history(message):
    try:
        with open("historial_apuestas.txt", "r", encoding="utf-8") as f:
            lineas = f.readlines()
            ultimas = lineas[-5:] if len(lineas) > 5 else lineas
            
            if not ultimas:
                bot.send_message(message.chat.id, "í³­ El historial estÃ¡ vacÃ­o.")
                return
                
            msg = "í³‚ *ÃšLTIMAS 5 PREDICCIONES:*\n\n" + "".join(ultimas)
            bot.send_message(message.chat.id, msg)
    except FileNotFoundError:
        bot.send_message(message.chat.id, "í³­ AÃºn no hay historial registrado.")

@bot.message_handler(commands=['buscar'])
def search_handler(message):
    query = message.text.replace('/buscar', '').strip()
    if not query:
        bot.reply_to(message, "í´ Escribe el nombre. Ej: `/buscar Barcelona`")
        return
    try:
        res = requests.get(f"{API_URL}/search?query={query}").json()
        if not res:
            bot.send_message(message.chat.id, "âŒ Sin resultados.")
            return
        markup = InlineKeyboardMarkup()
        for t in res:
            markup.add(InlineKeyboardButton(f"âœ… {t['name']}", callback_data=f"sel_{t['name']}"))
        bot.send_message(message.chat.id, f"í´ Resultados para '{query}':", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "âš ï¸ API offline.")

@bot.message_handler(commands=['equipos'])
def list_teams(message, page=1):
    try:
        teams = requests.get(f"{API_URL}/teams").json()
        items_per_page = 10
        start, end = (page-1)*items_per_page, page*items_per_page
        current = teams[start:end]
        markup = InlineKeyboardMarkup(row_width=2)
        for t in current:
            markup.add(InlineKeyboardButton(t['name'], callback_data=f"sel_{t['name']}"))
        nav = []
        if page > 1: nav.append(InlineKeyboardButton("â¬…ï¸", callback_data=f"page_{page-1}"))
        if end < len(teams): nav.append(InlineKeyboardButton("â¡ï¸", callback_data=f"page_{page+1}"))
        markup.add(*nav)
        bot.send_message(message.chat.id, f"í³‹ *Equipos (PÃ¡g {page})*", reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "âš ï¸ API offline.")

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id = call.message.chat.id
    if call.data.startswith("page_"):
        bot.delete_message(chat_id, call.message.message_id)
        list_teams(call.message, int(call.data.split("_")[1]))
    elif call.data.startswith("sel_"):
        name = call.data.split("_")[1]
        if chat_id not in user_state or user_state[chat_id]['step'] == 'done':
            user_state[chat_id] = {'home': name, 'step': 'away'}
            bot.send_message(chat_id, f"í¿  *LOCAL:* {name}\nSelecciona el visitante:")
        else:
            home = user_state[chat_id]['home']
            user_state[chat_id] = {'home': home, 'away': name, 'step': 'bajas'}
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("âœ… Full Equipo", callback_data="abs_0"))
            markup.add(InlineKeyboardButton("âš ï¸ 1-2 Bajas", callback_data="abs_1"))
            markup.add(InlineKeyboardButton("íº¨ Crisis", callback_data="abs_2"))
            bot.send_message(chat_id, f"í¶š {home} vs {name}\nÂ¿Estado de bajas del Local?", reply_markup=markup)
    elif call.data.startswith("abs_"):
        user_state[chat_id]['abs_level'] = int(call.data.split("_")[1])
        user_state[chat_id]['step'] = 'done'
        bot.send_message(chat_id, "í²° Cuotas (Local Empate Visita):")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id, {}).get('step') == 'done')
def calculate(message):
    try:
        odds, state = message.text.split(), user_state[message.chat.id]
        all_teams = requests.get(f"{API_URL}/teams").json()
        teams_map = {t['name']: t for t in all_teams}
        h_data, a_data = teams_map[state['home']], teams_map[state['away']]
        atk_mod = h_data['atk'] * {0:1.0, 1:0.85, 2:0.70}[state['abs_level']]
        payload = {
            "home_name": state['home'], "away_name": state['away'],
            "home_attack_power": atk_mod, "away_defense_weakness": a_data['def'],
            "odds": {"L": float(odds[0]), "E": float(odds[1]), "V": float(odds[2])}
        }
        res = requests.post(f"{API_URL}/predict", json=payload).json()
        p = res['probabilities']
        save_to_history(state['home'], state['away'], p['L'], p['E'], p['V'], res['value_found'])
        msg = f"í¾¯ *IA:* L:{p['L']}% | E:{p['E']}% | V:{p['V']}%\n"
        msg += f"í²° *VALOR:* {', '.join(res['value_found'].keys())}" if res['value_found'] else "âš–ï¸ Ajustado."
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        user_state[message.chat.id]['step'] = None
    except:
        bot.send_message(message.chat.id, "âŒ Error. Formato: 1.80 3.20 4.00")

print("Bot Pro iniciado...")
bot.polling()
