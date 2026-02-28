# api.py
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.models.brain import BettingBrain
import uvicorn

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

app = FastAPI()
brain = BettingBrain()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class MatchRequest(BaseModel):
    home_name: str
    away_name: str
    home_attack_power: float
    away_defense_weakness: float
    odds: dict

@app.get("/teams")
def get_teams():
    # Simulamos 20 equipos (puedes conectar esto a tu DB de SQLite después)
    full_data = [
        {"name": "Real Madrid", "atk": 2.15, "def": 0.88},
        {"name": "Barcelona", "atk": 1.95, "def": 1.05},
        {"name": "Girona", "atk": 1.85, "def": 1.20},
        {"name": "Atletico Madrid", "atk": 1.70, "def": 0.95},
        {"name": "Athletic Club", "atk": 1.60, "def": 1.10},
        {"name": "Real Sociedad", "atk": 1.45, "def": 1.02},
        {"name": "Betis", "atk": 1.30, "def": 1.15},
        {"name": "Valencia", "atk": 1.25, "def": 1.10},
        {"name": "Villarreal", "atk": 1.55, "def": 1.40},
        {"name": "Getafe", "atk": 1.10, "def": 1.05},
        {"name": "Osasuna", "atk": 1.15, "def": 1.20},
        {"name": "Las Palmas", "atk": 1.05, "def": 1.18},
        {"name": "Alaves", "atk": 1.08, "def": 1.25},
        {"name": "Sevilla", "atk": 1.40, "def": 1.35},
        {"name": "Mallorca", "atk": 0.95, "def": 1.10},
        {"name": "Rayo Vallecano", "atk": 1.02, "def": 1.30},
        {"name": "Celta de Vigo", "atk": 1.28, "def": 1.45},
        {"name": "Cadiz", "atk": 0.85, "def": 1.40},
        {"name": "Granada", "atk": 1.10, "def": 1.60},
        {"name": "Almeria", "atk": 1.15, "def": 1.75}
    ]
    
    for t in full_data:
        # Calculamos cuotas sugeridas basadas en sus propios xG vs promedio (simulado)
        # Esto sirve para que tengas una referencia de qué cuota esperar
        t["sug_l"] = round(1 / (t["atk"] / (t["atk"] + t["def"] + 1)), 2)
        t["sug_v"] = round(1 / (t["def"] / (t["atk"] + t["def"] + 1)), 2)
        
        if t["atk"] > 1.8: t["status"] = "🔥 DOMINANTE"
        elif t["def"] > 1.4: t["status"] = "⚠️ DEFENSA DEBIL"
        else: t["status"] = "⚖️ ESTABLE"
        
    return full_data

@app.post("/predict")
def predict(match: MatchRequest):
    probs = brain.predict_1x2(match.home_attack_power, match.away_defense_weakness)
    value = brain.find_value(probs, match.odds)
    return {"probabilities": probs, "value_found": value}
# Añadir a api.py
@app.get("/scanner")
def scan_opportunities():
    teams = get_teams() # Obtiene todos los equipos
    opportunities = []
    
    # Simulación de cruces de jornada
    for i in range(0, len(teams), 2):
        home, away = teams[i], teams[i+1]
        probs = brain.predict_1x2(home['atk'], away['def'])
        
        # Si la probabilidad de victoria local es > 65% y la cuota sugerida es atractiva
        if probs['L'] > 65:
            opportunities.append({
                "match": f"{home['name']} vs {away['name']}",
                "prob": probs['L'],
                "sug": home['sug_l'],
                "type": "🔥 VALOR LOCAL"
            })
    return opportunities
@app.get("/search")
def search_team(query: str):
    teams = get_teams() # Obtiene la lista completa de 20
    # Busca coincidencias parciales (ej: "Mad" encontrará "Real Madrid")
    results = [t for t in teams if query.lower() in t['name'].lower()]
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)