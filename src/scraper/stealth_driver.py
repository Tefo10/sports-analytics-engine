import io
import re
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync


class FBRefScraper:
    DEFAULT_LA_LIGA_URL = "https://fbref.com/en/comps/12/stats/La-Liga-Stats"
    DEFAULT_LA_LIGA_FIXTURES_URL = "https://fbref.com/en/comps/12/schedule/La-Liga-Scores-and-Fixtures"

    def _get_page_html(self, url):
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
        return html

    def get_tables(self, url):
        html = self._get_page_html(url)
        tables = pd.read_html(io.StringIO(html))
        if not tables:
            # FBRef often ships tables inside HTML comments to deter simple scrapers.
            uncommented_html = re.sub(r"<!--|-->", "", html)
            tables = pd.read_html(io.StringIO(uncommented_html))
        return [self._flatten_columns(table) for table in tables]

    def get_table(self, url, table_index=0):
        tables = self.get_tables(url)
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
    def _find_column(columns, candidates):
        normalized = {str(col).strip().lower(): col for col in columns}
        for candidate in candidates:
            candidate_lower = candidate.lower()
            for lower_name, original in normalized.items():
                if candidate_lower == lower_name or candidate_lower in lower_name:
                    return original
        return None

    def _extract_matches_from_schedule(self, schedule_df):
        home_col = self._find_column(schedule_df.columns, ["home", "home team", "home_team"])
        away_col = self._find_column(schedule_df.columns, ["away", "away team", "away_team"])
        score_col = self._find_column(schedule_df.columns, ["score", "result"])

        if not (home_col and away_col and score_col):
            raise ValueError("Could not identify Home/Away/Score columns in FBRef schedule table.")

        matches = []
        for _, row in schedule_df.iterrows():
            home_team = str(row.get(home_col, "")).strip()
            away_team = str(row.get(away_col, "")).strip()
            raw_score = str(row.get(score_col, "")).strip()

            if not home_team or not away_team or home_team.lower() == "nan" or away_team.lower() == "nan":
                continue

            parsed_score = re.search(r"(\d+)\D+(\d+)", raw_score)
            if not parsed_score:
                continue

            home_goals = int(parsed_score.group(1))
            away_goals = int(parsed_score.group(2))
            matches.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                }
            )
        return matches

    def _aggregate_home_away_stats(self, matches):
        base_fields = {
            "played_home": 0,
            "goals_for_home": 0,
            "goals_against_home": 0,
            "points_home": 0,
            "draws_home": 0,
            "played_away": 0,
            "goals_for_away": 0,
            "goals_against_away": 0,
            "points_away": 0,
            "draws_away": 0,
        }
        stats = defaultdict(lambda: dict(base_fields))

        for match in matches:
            home_team = match["home_team"]
            away_team = match["away_team"]
            home_goals = match["home_goals"]
            away_goals = match["away_goals"]

            home = stats[home_team]
            away = stats[away_team]

            home["played_home"] += 1
            home["goals_for_home"] += home_goals
            home["goals_against_home"] += away_goals

            away["played_away"] += 1
            away["goals_for_away"] += away_goals
            away["goals_against_away"] += home_goals

            if home_goals > away_goals:
                home["points_home"] += 3
            elif away_goals > home_goals:
                away["points_away"] += 3
            else:
                home["points_home"] += 1
                away["points_away"] += 1
                home["draws_home"] += 1
                away["draws_away"] += 1

        output = []
        for team_name, team_stats in stats.items():
            played_home = max(team_stats["played_home"], 1)
            played_away = max(team_stats["played_away"], 1)

            atk = team_stats["goals_for_home"] / played_home
            defense_weakness = team_stats["goals_against_away"] / played_away
            ppg = (team_stats["points_home"] + team_stats["points_away"]) / (
                team_stats["played_home"] + team_stats["played_away"] or 1
            )
            ga_per_match = (team_stats["goals_against_home"] + team_stats["goals_against_away"]) / (
                team_stats["played_home"] + team_stats["played_away"] or 1
            )

            strength_base = atk + defense_weakness + 1
            sug_l = round(1 / max(atk / strength_base, 0.05), 2)
            sug_v = round(1 / max(defense_weakness / strength_base, 0.05), 2)

            if ppg >= 1.9:
                status = "DOMINANTE"
            elif ga_per_match >= 1.6:
                status = "DEFENSA DEBIL"
            else:
                status = "ESTABLE"

            output.append(
                {
                    "name": team_name,
                    "atk": round(atk, 3),
                    "def": round(defense_weakness, 3),
                    "sug_l": sug_l,
                    "sug_v": sug_v,
                    "status": status,
                    "played_home": team_stats["played_home"],
                    "goals_for_home": team_stats["goals_for_home"],
                    "goals_against_home": team_stats["goals_against_home"],
                    "points_home": team_stats["points_home"],
                    "draws_home": team_stats["draws_home"],
                    "played_away": team_stats["played_away"],
                    "goals_for_away": team_stats["goals_for_away"],
                    "goals_against_away": team_stats["goals_against_away"],
                    "points_away": team_stats["points_away"],
                    "draws_away": team_stats["draws_away"],
                    "partidos_jugados_local": team_stats["played_home"],
                    "goles_a_favor_local": team_stats["goals_for_home"],
                    "goles_en_contra_local": team_stats["goals_against_home"],
                    "puntos_local": team_stats["points_home"],
                    "empates_local": team_stats["draws_home"],
                    "partidos_jugados_visitante": team_stats["played_away"],
                    "goles_a_favor_visitante": team_stats["goals_for_away"],
                    "goles_en_contra_visitante": team_stats["goals_against_away"],
                    "puntos_visitante": team_stats["points_away"],
                    "empates_visitante": team_stats["draws_away"],
                }
            )

        return sorted(output, key=lambda item: item["name"])

    def get_la_liga_stats(self):
        tables = self.get_tables(self.DEFAULT_LA_LIGA_FIXTURES_URL)
        schedule = None
        for table in tables:
            if self._find_column(table.columns, ["home"]) and self._find_column(table.columns, ["away"]) and self._find_column(table.columns, ["score", "result"]):
                schedule = table
                break

        if schedule is None:
            raise ValueError("No schedule table found in FBRef fixtures page.")

        matches = self._extract_matches_from_schedule(schedule)
        if not matches:
            raise ValueError("No completed matches found to build team stats.")
        return self._aggregate_home_away_stats(matches)

    def get_team_input_stats(self, home_team, away_team):
        teams = self.get_la_liga_stats()
        by_name = {team["name"].lower(): team for team in teams}
        home = by_name.get(home_team.lower())
        away = by_name.get(away_team.lower())
        if not home or not away:
            raise ValueError("Team not found in current scraped dataset.")

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

    def save_la_liga_csv(self, output_path="data/la_liga_stats.csv"):
        stats = self.get_la_liga_stats()
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(stats).to_csv(output_file, index=False, encoding="utf-8")
        return str(output_file)
