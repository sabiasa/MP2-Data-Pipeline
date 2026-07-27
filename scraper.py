"""
Sumber:
  1. RSS Feeds (News)
  2. books.toscrape.com 
  3. quotes.toscrape.com
"""

from typing import Optional, List, Dict
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "DigitalSkola-Learner/1.0"}
REQUEST_TIMEOUT = 15
DELAY_BETWEEN_REQUESTS = 1.0

def _get(url):
    # type: (str) -> BeautifulSoup
    time.sleep(DELAY_BETWEEN_REQUESTS)
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

RSS_FEEDS = [
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",       "source": "nytimes"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",  "source": "nytimes"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",                 "source": "bbc"},
    {"url": "https://feeds.bbci.co.uk/news/technology/rss.xml",            "source": "bbc"},
    {"url": "http://rss.cnn.com/rss/edition_world.rss",                    "source": "cnn"},
    {"url": "http://rss.cnn.com/rss/edition_technology.rss",               "source": "cnn"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml",                   "source": "aljazeera"},
    {"url": "https://feeds.skynews.com/feeds/rss/world.xml",               "source": "skynews"},
    {"url": "https://techcrunch.com/feed/",                                "source": "techcrunch"},
]

def _parse_rss_xml(xml_text, source_name):
    # type: (str, str) -> List[Dict]
    soup = BeautifulSoup(xml_text, "xml")
    items = soup.find_all("item")
    results = []

    for item in items:
        title_tag = item.find("title")
        link_tag = item.find("link")
        desc_tag = item.find("description")
        pubdate_tag = item.find("pubDate")

        if not title_tag or not link_tag:
            continue

        title = title_tag.get_text(strip=True)
        url = link_tag.get_text(strip=True)

        # Description bisa mengandung HTML, bersihkan
        content = ""
        if desc_tag:
            raw_desc = desc_tag.get_text(strip=True)
            # Strip HTML tags dari description
            content = BeautifulSoup(raw_desc, "html.parser").get_text(strip=True)

        # Parse published date
        published_at = None
        if pubdate_tag:
            raw_date = pubdate_tag.get_text(strip=True)
            for fmt in [
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z",
            ]:
                try:
                    published_at = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue

        results.append({
            "title": title[:200],
            "url": url,
            "source": source_name,
            "content": content if content else title,
            "published_at": published_at,
        })

    return results


def scrape_rss(feeds=None):
    if feeds is None:
        feeds = RSS_FEEDS

    all_articles = []

    for feed in feeds:
        url = feed["url"]
        source = feed["source"]
        log.info("[rss] Scraping %s: %s", source, url)

        try:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            articles = _parse_rss_xml(resp.text, source)
            all_articles.extend(articles)
            log.info("[rss] %s: dapat %d artikel (total: %d)", source, len(articles), len(all_articles))
        except Exception as e:
            log.warning("[rss] %s gagal: %s", source, e)
            continue

    return all_articles

BOOKS_BASE = "https://books.toscrape.com/"

STAR_MAP = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5,
}

def _parse_book_listing(article_tag, page_url):
    # type: (object, str) -> dict
    h3 = article_tag.select_one("h3 > a")
    title = h3["title"]
    relative_url = h3["href"]
    book_url = urljoin(page_url, relative_url)

    price = article_tag.select_one("p.price_color").get_text(strip=True)

    star_tag = article_tag.select_one("p.star-rating")
    star_class = [c for c in star_tag.get("class", []) if c != "star-rating"]
    rating = STAR_MAP.get(star_class[0], 0) if star_class else 0

    avail_tag = article_tag.select_one("p.instock.availability")
    availability = avail_tag.get_text(strip=True) if avail_tag else "Unknown"

    return {
        "title": title,
        "url": book_url,
        "source": "books.toscrape",
        "content": "%s. Price: %s. Rating: %d/5 stars. %s." % (title, price, rating, availability),
        "published_at": None,
        "meta": {"detail_url": book_url},
    }


def _fetch_book_description(detail_url):
    # type: (str) -> Optional[str]
    try:
        soup = _get(detail_url)
        desc_header = soup.select_one("#product_description")
        if desc_header:
            p = desc_header.find_next_sibling("p")
            if p:
                return p.get_text(strip=True)
    except Exception as e:
        log.warning("Gagal ambil deskripsi %s: %s", detail_url, e)
    return None

# Mencari data judul dan url dari Network lalu fetch description dari halaman selanjunya
def scrape_books(max_pages=10, fetch_descriptions=False):
    # type: (int, bool) -> List[Dict]
    results = []

    for page_num in range(1, max_pages + 1):
        url = "%scatalogue/page-%d.html" % (BOOKS_BASE, page_num)
        log.info("[books] Scraping halaman %d: %s", page_num, url)

        try:
            soup = _get(url)
        except requests.HTTPError as e:
            log.warning("[books] Halaman %d gagal (%s), berhenti.", page_num, e)
            break

        pods = soup.select("article.product_pod")
        if not pods:
            log.info("[books] Tidak ada buku di halaman %d, berhenti.", page_num)
            break

        for pod in pods:
            book = _parse_book_listing(pod, url)
            results.append(book)

        log.info("[books] Halaman %d: dapat %d buku (total: %d)", page_num, len(pods), len(results))

    if fetch_descriptions:
        log.info("[books] Mengambil deskripsi untuk %d buku...", len(results))
        for i, book in enumerate(results):
            desc = _fetch_book_description(book["meta"]["detail_url"])
            if desc:
                book["content"] = desc
            if (i + 1) % 20 == 0:
                log.info("[books] Deskripsi: %d/%d selesai", i + 1, len(results))

    for book in results:
        book.pop("meta", None)

    return results

QUOTES_BASE = "https://quotes.toscrape.com/"

def scrape_quotes(max_pages=10):
    # type: (int) -> List[Dict]
    results = []

    for page_num in range(1, max_pages + 1):
        url = "%spage/%d/" % (QUOTES_BASE, page_num)
        log.info("[quotes] Scraping halaman %d: %s", page_num, url)

        try:
            soup = _get(url)
        except requests.HTTPError as e:
            log.warning("[quotes] Halaman %d gagal (%s), berhenti.", page_num, e)
            break

        quotes = soup.select("div.quote")
        if not quotes:
            log.info("[quotes] Tidak ada kutipan di halaman %d, berhenti.", page_num)
            break

        for q in quotes:
            text = q.select_one("span.text").get_text(strip=True)
            author = q.select_one("small.author").get_text(strip=True)
            tags = [t.get_text(strip=True) for t in q.select("div.tags > a.tag")]

            tag_str = ", ".join(tags) if tags else "none"
            results.append({
                "title": text[:100],
                "url": "%s#quote-%d-%s" % (QUOTES_BASE, len(results) + 1, author.replace(" ", "-")),
                "source": "quotes.toscrape",
                "content": "%s -- %s. Tags: %s." % (text, author, tag_str),
                "published_at": datetime.now(timezone.utc),
            })

        log.info("[quotes] Halaman %d: dapat %d kutipan (total: %d)", page_num, len(quotes), len(results))

    return results

def scrape_all(
    rss=True,
    book_pages=10,
    quote_pages=10,
    fetch_book_descriptions=False,
):
    # type: (...) -> List[Dict]
    all_records = []

    log.info("=" * 60)
    log.info("MULAI SCRAPING")
    log.info("=" * 60)

    # Jika ADA data yang ditemukan berasal dari RSS News feed
    if rss: 
        rss_articles = scrape_rss()
        all_records.extend(rss_articles)
        log.info("Total RSS: %d", len(rss_articles))

    # Scrapping dari data books
    books = scrape_books(max_pages=book_pages, fetch_descriptions=fetch_book_descriptions)
    all_records.extend(books)
    log.info("Total buku: %d", len(books))

    # Scrapping dari data quotes
    quotes = scrape_quotes(max_pages=quote_pages)
    all_records.extend(quotes)
    log.info("Total kutipan: %d", len(quotes))

    log.info("=" * 60)
    log.info("SELESAI. Total record: %d", len(all_records))
    log.info("=" * 60)

    return all_records


if __name__ == "__main__":
    records = scrape_all()
    print("\nHasil: %d record" % len(records))
    rss_count = sum(1 for r in records if r["source"] not in ("books.toscrape", "quotes.toscrape"))
    book_count = sum(1 for r in records if r["source"] == "books.toscrape")
    quote_count = sum(1 for r in records if r["source"] == "quotes.toscrape")
    print("  RSS:     %d" % rss_count)
    print("  Buku:    %d" % book_count)
    print("  Kutipan: %d" % quote_count)
    for r in records[:3]:
        print("\n  [%s] %s" % (r["source"], r["title"][:60]))
        print("    URL: %s" % r["url"][:80])