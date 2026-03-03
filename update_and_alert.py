import asyncio
import os

from aiogram import Bot
from dotenv import load_dotenv

from src.models.brain import BettingBrain
from src.scraper.stealth_driver import FBRefScraper
from src.utils.database import DBManager

load_dotenv()

db = DBManager()
brain = BettingBrain()
scraper = FBRefScraper()


async def run_pipeline():
    token = os.getenv("TELEGRAM_TOKEN")
    users = db.get_all_users()

    try:
        csv_path = scraper.save_la_liga_csv()
        print(f"OK: CSV generado en {csv_path}")
    except Exception as exc:
        print(f"ERROR: no se pudo ejecutar el scraping ({exc})")
        return

    match = {
        "home": "Arsenal",
        "away": "Chelsea",
        "h_xg": 2.1,
        "a_xg": 1.1,
        "odds": {"L": 2.2, "E": 3.5, "V": 4.0},
    }
    probs = brain.predict_1x2(match["h_xg"], match["a_xg"])
    values = brain.find_value(probs, match["odds"])

    if not (values and users and token):
        return

    bot = Bot(token=token)
    for user_id in users:
        try:
            await bot.send_message(
                user_id,
                (
                    "Valor detectado\n"
                    f"{match['home']} vs {match['away']}\n"
                    f"Prob L: {probs['L']:.1%}"
                ),
            )
        except Exception:
            continue


if __name__ == "__main__":
    asyncio.run(run_pipeline())
