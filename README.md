# ⚽ Sports Analytics Engine (Soccer AI Pro)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-green.svg)
![Aiogram](https://img.shields.io/badge/Aiogram-TelegramBot-blue.svg)

Este es un sistema avanzado de análisis estadístico de fútbol que utiliza modelos de **Goles Esperados (xG)** y la **Distribución de Poisson** para identificar valor en las cuotas de apuestas deportivas.

---

## 🚀 Características Principales

- **🔍 Motor de Scraping:** Extracción de métricas avanzadas (xG, xGA) desde FBRef.
- **🧠 Analizador de Probabilidades:** Cálculo de probabilidades (1X2) basado en rendimiento ofensivo y defensivo.
- **🤖 Bot de Telegram Interactivo:**
    - Búsqueda instantánea de equipos.
    - Factor de **Bajas/Ausencias** (ajusta el potencial de ataque dinámicamente).
    - Historial de consultas automático.
- **💡 Escáner de Oportunidades:** Alertas matutinas automáticas sobre partidos con valor estadístico.

---

## 🛠️ Estructura del Proyecto

```text
predictor_pro/
├── main.py              # Punto de entrada del Bot (Aiogram)
├── api.py               # Servidor Backend (FastAPI)
├── src/
│   ├── bot/
│   │   └── handlers.py  # Lógica de comandos de Telegram
│   └── models/
│       └── brain.py     # El "cerebro" matemático (Poisson)
├── .env                 # Variables de entorno (Token)
└── historial_apuestas.txt # Registro local de predicciones
