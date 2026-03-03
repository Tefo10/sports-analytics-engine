from src.scraper.stealth_driver import FBRefScraper


def main():
    scraper = FBRefScraper()
    csv_path = scraper.save_la_liga_csv()
    print(f"CSV generado: {csv_path}")


if __name__ == "__main__":
    main()
