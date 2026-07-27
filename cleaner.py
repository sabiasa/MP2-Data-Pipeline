from typing import List, Dict
import pandas as pd
import logging

log = logging.getLogger(__name__)

def clean_articles(raw_records: List[Dict]) -> pd.DataFrame:
    # Init
    if not raw_records:
        return pd.DataFrame(columns=["title", "url", "source", "content", "published_at"])
    
    df = pd.DataFrame(raw_records)
    initial_count = len(df)
    log.info("Cleaning data: awal %d record", initial_count)


    # 1. Drop duplikat berdasarkan URL
    df = df.drop_duplicates(subset=["url"])
    log.info("  → Drop duplikat: %d record", initial_count - len(df))
   
    # 2. Buang baris tanpa title atau URL
    before = len(df)
    df = df.dropna(subset=["title", "url"])

    if len(df) < before:
        log.info("  → Buang baris tanpa title/url: %d record", before - len(df))
    
    # 3. Normalisasi teks
    df["title"] = df["title"].str.strip()
    df["url"] = df["url"].str.strip()
    df["source"] = df["source"].str.strip().str.lower()
    df["content"] = df["content"].fillna("").str.strip()

    # 4. Tipe data konsisten
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    df["published_at"] = df["published_at"].dt.tz_localize(None)  

    # 5. Buang konten terlalu pendek (< 20 karakter = kemungkinan gagal scrape)
    before2 = len(df)
    df = df[df["content"].str.len() >= 20]
    if len(df) < before2:
        log.info("  → Buang konten terlalu pendek: %d record", before2 - len(df))

    # 6. Kolom di database
    db_columns = ["title", "url", "source", "content", "published_at"]
    df = df[db_columns]
    df = df.reset_index(drop=True)
    log.info(" Cleaning Selesai -> Final: %d record", len(df))

    return df 
