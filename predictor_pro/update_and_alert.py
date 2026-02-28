import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot
from src.utils.database import DBManager
from src.models.brain import BettingBrain
from src.scraper.stealth_driver import FBRefScraper

load_dotenv()
db = DBManager()
brain = BettingBrain()
scraper = FBRefScraper()

async def run_pipeline():
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    users = db.get_all_users()
    
    # Intentar scraping sigiloso (Ejemplo Premier League Standings)
    try:
        data = scraper.get_table("https://fbref.com/en/comps/9/stats/Premier-League-Stats")
        print("‚úÖ Datos obtenidos exitosamente.")
    except Exception as e:
        print(f"‚ùå Error al saltar protecci√≥n: {e}")
        return

    # L√≥gica de ejemplo para alerta
    match = {'home': 'Arsenal', 'away': 'Chelsea', 'h_xg': 2.1, 'a_xg': 1.1, 'odds': {'L': 2.2, 'E': 3.5, 'V': 4.0}}
    probs = brain.predict_1x2(match['h_xg'], match['a_xg'])
    values = brain.find_value(probs, match['odds'])
    
    if values and users:
        for u_id in users:
            try:
                await bot.send_message(u_id, f"Ì∫® **Valor Detectado**\n{match['home']} vs {match['away']}\nProb L: {probs['L']:.1%}")
            except: pass

if __name__ == "__main__":
    asyncio.run(run_pipeline())
