"""
DDL:
  CREATE TABLE IF NOT EXISTS articles_name (
      id           SERIAL PRIMARY KEY,
      title        TEXT NOT NULL,
      url          TEXT UNIQUE NOT NULL,
      source       TEXT NOT NULL,
      content      TEXT,
      published_at TIMESTAMP,
      scraped_at   TIMESTAMP DEFAULT NOW()
  );
  CREATE INDEX IF NOT EXISTS idx_articles_source ON articles_name(source);
  CREATE INDEX IF NOT EXISTS idx_articles_published ON articles_name(published_at DESC);
"""

from typing import Optional, List, Dict
from sqlalchemy import create_engine, text
from pydantic_settings import BaseSettings, SettingsConfigDict
import pandas as pd
import logging

log = logging.getLogger(__name__)


class DBSettings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )


settings = DBSettings()
engine = create_engine(settings.database_url)

TABLE_NAME = '"ai_engineer".articles_shabhi'

def init_db():
    """Buat tabel dan index kalau belum ada."""
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id           SERIAL PRIMARY KEY,
        title        TEXT NOT NULL,
        url          TEXT UNIQUE NOT NULL,
        source       TEXT NOT NULL,
        content      TEXT,
        published_at TIMESTAMP,
        scraped_at   TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_articles_source
        ON {TABLE_NAME}(source);
    CREATE INDEX IF NOT EXISTS idx_articles_published
        ON {TABLE_NAME}(published_at DESC);
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    log.info("Tabel '%s' siap.", TABLE_NAME)


def save_articles(df: pd.DataFrame) -> int:
    if df.empty:
        log.warning("DataFrame kosong, tidak ada yang di-insert.")
        return 0

    inserted = 0
    with engine.begin() as conn:
        for _, row in df.iterrows():
            result = conn.execute(
                text(f"""
                    INSERT INTO {TABLE_NAME}
                        (title, url, source, content, published_at)
                    VALUES
                        (:title, :url, :source, :content, :published_at)
                    ON CONFLICT (url) DO NOTHING
                """),
                {
                    "title": row["title"],
                    "url": row["url"],
                    "source": row["source"],
                    "content": row["content"],
                    "published_at": row["published_at"]
                    if pd.notna(row["published_at"])
                    else None,
                },
            )
            inserted += result.rowcount

    log.info("Insert selesai: %d baru dari %d record.", inserted, len(df))
    return inserted


def get_articles(
    source: Optional[str] = None,
    limit: int = 20,
) -> List[Dict]:
    query = f"SELECT * FROM {TABLE_NAME}"
    params: dict = {}

    if source:
        query += " WHERE source = :source"
        params["source"] = source.lower()

    query += " ORDER BY published_at DESC NULLS LAST LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()

    return [dict(r) for r in rows]


def get_article_by_id(article_id: int) -> Optional[Dict]:
    """Get single article by ID."""
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT * FROM {TABLE_NAME} WHERE id = :id"),
            {"id": article_id},
        ).mappings().first()

    return dict(row) if row else None


def count_articles() -> int:
    """Hitung total articles di database."""
    with engine.connect() as conn:
        row = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).fetchone()
    return row[0] if row else 0

     # Moni project = Tambahkan query unuk panggilan API
     # GET julah total artikel
