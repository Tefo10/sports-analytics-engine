from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import pandas as pd
import io

class FBRefScraper:
    def get_table(self, url):
        with sync_playwright() as p:
            # Lanzamos un navegador real (Chromium)
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            stealth_sync(page) # Oculta las huellas de automatizaci√≥n
            
            print(f"Ì≥° Accediendo a FBRef: {url}")
            page.goto(url, wait_until="networkidle")
            
            # Si hay un captcha, aqu√≠ podr√≠as pausar o usar un solver
            # Por ahora, extraemos el contenido tras la carga
            html = page.content()
            browser.close()
            
            # Convertimos las tablas HTML a DataFrames de Pandas
            tables = pd.read_html(io.StringIO(html))
            return tables[0] # Retornamos la tabla principal
