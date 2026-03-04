import sys
from datetime import datetime
from threading import Lock
from typing import Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.models.brain import BettingBrain
from src.scraper.stealth_driver import FBRefScraper

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

app = FastAPI(title="Sports Analytics Engine API")
brain = BettingBrain()
scraper = FBRefScraper()
cache_lock = Lock()
teams_cache = {"data": None, "fetched_at": None}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Odds(BaseModel):
    L: float
    E: float
    V: float


class MatchRequest(BaseModel):
    home_name: str
    away_name: str
    home_attack_power: float
    away_defense_weakness: float
    odds: Odds


def load_teams_data(force_refresh=False, max_age_seconds=180):
    with cache_lock:
        cached_data = teams_cache["data"]
        cached_at = teams_cache["fetched_at"]
        if not force_refresh and cached_data and cached_at:
            age = (datetime.utcnow() - cached_at).total_seconds()
            if age <= max_age_seconds:
                return cached_data

    try:
        teams = scraper.get_la_liga_stats()
    except Exception as exc:
        with cache_lock:
            if teams_cache["data"]:
                return teams_cache["data"]
        raise HTTPException(status_code=503, detail=f"Could not fetch live FBRef data: {exc}") from exc

    with cache_lock:
        teams_cache["data"] = teams
        teams_cache["fetched_at"] = datetime.utcnow()
    return teams


def find_team_by_name(teams, team_name):
    team_name_norm = team_name.strip().lower()

    exact_match = next((team for team in teams if team["name"].lower() == team_name_norm), None)
    if exact_match:
        return exact_match

    partial_match = next((team for team in teams if team_name_norm in team["name"].lower()), None)
    return partial_match


@app.get("/health")
def health():
    with cache_lock:
        cached_at = teams_cache["fetched_at"]
    return {"status": "ok", "teams_last_refresh_utc": cached_at.isoformat() if cached_at else None}


@app.get("/teams")
def get_teams(refresh: bool = True, max_age_seconds: int = 180):
    return load_teams_data(force_refresh=refresh, max_age_seconds=max_age_seconds)


@app.get("/front/match-inputs")
def get_front_match_inputs(home_team: str, away_team: str, refresh: bool = True):
    teams = load_teams_data(force_refresh=refresh, max_age_seconds=180)

    home = find_team_by_name(teams, home_team)
    away = find_team_by_name(teams, away_team)
    if not home:
        raise HTTPException(status_code=404, detail=f"Local team not found: {home_team}")
    if not away:
        raise HTTPException(status_code=404, detail=f"Away team not found: {away_team}")

    return {
        "equipo_local": home["name"],
        "equipo_visitante": away["name"],
        "partidos_jugados_local": home["partidos_jugados_local"],
        "goles_a_favor_local": home["goles_a_favor_local"],
        "goles_en_contra_local": home["goles_en_contra_local"],
        "puntos_local": home["puntos_local"],
        "empates_local": home["empates_local"],
        "partidos_jugados_visitante": away["partidos_jugados_visitante"],
        "goles_a_favor_visitante": away["goles_a_favor_visitante"],
        "goles_en_contra_visitante": away["goles_en_contra_visitante"],
        "puntos_visitante": away["puntos_visitante"],
        "empates_visitante": away["empates_visitante"],
    }


@app.post("/predict")
def predict(match: MatchRequest):
    probs = brain.predict_1x2(match.home_attack_power, match.away_defense_weakness)
    odds: Dict[str, float] = match.odds.model_dump()
    value = brain.find_value(probs, odds)
    return {"probabilities": probs, "value_found": value}


@app.get("/scanner")
def scan_opportunities():
    teams = load_teams_data(force_refresh=False, max_age_seconds=180)
    opportunities = []

    for i in range(0, len(teams), 2):
        home, away = teams[i], teams[i + 1]
        probs = brain.predict_1x2(home["atk"], away["def"])

        # `L` is 0..1, so 0.65 means 65% home-win probability.
        if probs["L"] > 0.65:
            opportunities.append(
                {
                    "match": f"{home['name']} vs {away['name']}",
                    "prob": round(probs["L"] * 100, 2),
                    "sug": home["sug_l"],
                    "type": "VALOR LOCAL",
                }
            )
    return opportunities


@app.get("/search")
def search_team(query: str):
    teams = load_teams_data(force_refresh=False, max_age_seconds=180)
    return [team for team in teams if query.lower() in team["name"].lower()]


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
