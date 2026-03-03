import io
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync


class FBRefScraper:
    DEFAULT_LA_LIGA_URL = "https://fbref.com/en/comps/12/stats/La-Liga-Stats"

    def get_table(self, url, table_index=0):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/119.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            stealth_sync(page)

            print(f"INFO: Requesting table from {url}")
            page.goto(url, wait_until="networkidle")
            time.sleep(2)

            html = page.content()
            browser.close()

        tables = pd.read_html(io.StringIO(html))
        if table_index >= len(tables):
            raise ValueError(
                f"Requested table index {table_index}, but only {len(tables)} tables were found."
            )
        return tables[table_index]

    @staticmethod
    def _flatten_columns(dataframe):
        if not isinstance(dataframe.columns, pd.MultiIndex):
            return dataframe

        dataframe = dataframe.copy()
        dataframe.columns = [
            "_".join(str(col).strip() for col in cols if str(col).strip())
            for cols in dataframe.columns
        ]
        return dataframe

    @staticmethod
    def _as_float(value, default_value=1.0):
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.isna(parsed):
            return float(default_value)
        return float(parsed)

    def get_la_liga_stats(self):
        raw_table = self.get_table(self.DEFAULT_LA_LIGA_URL, table_index=0)
        table = self._flatten_columns(raw_table)

        output = []
        for _, row in table.iterrows():
            name = str(row.get("Unnamed: 1_level_0_Squad", row.get("Squad", "Unknown"))).strip()
            if not name or name.lower() == "nan":
                continue

            output.append(
                {
                    "name": name,
                    "xg": self._as_float(row.get("Expected_xG", row.get("xG", 1.0))),
                    "xga": self._as_float(row.get("Expected_xGA", row.get("xGA", 1.0))),
                }
            )
        return output

    def save_la_liga_csv(self, output_path="data/la_liga_stats.csv"):
        stats = self.get_la_liga_stats()
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(stats).to_csv(output_file, index=False, encoding="utf-8")
        return str(output_file)
