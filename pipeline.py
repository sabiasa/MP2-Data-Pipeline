from scraper import scrape_all
from cleaner import clean_articles
from db import init_db, save_articles, count_articles
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)

def run_pipeline():
    print("\n" + "=" * 60)
    print("  END-TO-END DATA PIPELINE — Session 10")
    print("=" * 60)

    # Step 0: Pastikan tabel ada dan database connect
    print("\nStep 0: Inisialisasi database...")
    init_db()

    # Step 1: Scraping
    print("\nStep 1: Scraping data dari web...")
    raw = scrape_all(
        rss=True,
        book_pages=10,
        quote_pages=10,
        fetch_book_descriptions=False,
    )
    print(f"  → Scraped: {len(raw)} record") # Data mentah 
    
    # Step 2: Cleaning
    print("\nStep 2: Cleaning data dengan Pandas...")
    df = clean_articles(raw)

    print(f"  → Cleaned: {len(df)} record")
    print(f"  → Sources: {df['source'].value_counts().to_dict()}")

    # Step 3: Simpan ke PostgreSQL
    print("\nStep 3: Menyimpan ke PostgreSQL...")
    inserted = save_articles(df)
    total = count_articles()

    print(f"  → Inserted: {inserted} baru")
    print(f"  → Total di database: {total}")

    print("\n" + "=" * 60)
    print("  PIPELINE SELESAI")
    print(f"  Jalankan API: uvicorn main_solution:app --reload")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    run_pipeline()