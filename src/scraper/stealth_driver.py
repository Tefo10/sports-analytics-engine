from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import pandas as pd
import io
import time

class FBRefScraper:
    def get_la_liga_stats(self):
        url = "https://fbref.com/en/comps/12/stats/La-Liga-Stats"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            stealth_sync(page)
            
            print("INFO: Extrayendo datos reales de FBRef (La Liga)...")
            page.goto(url, wait_until="networkidle")
            time.sleep(2) # Pausa de seguridad
            
            html = page.content()
            browser.close()
            
            # Buscamos la tabla de estadisticas de escuadras
            dfs = pd.read_html(io.StringIO(html))
            df = dfs[0] # Tabla principal de posiciones/stats
            
            # Limpiar nombres de columnas (FBRef usa multi-index)
            df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
            
            # Simplificar para nuestra web
            processed = []
            for _, row in df.iterrows():
                processed.append({
                    "name": row.get('Unnamed: 1_level_0_Squad', 'Unknown'),
                    "xg": float(row.get('Expected_xG', 1.0)),
                    "xga": float(row.get('Expected_xGA', 1.0))
                })
            return processed
