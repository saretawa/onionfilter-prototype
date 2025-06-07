"""
urlfetch.py - .onion link tracker

Features:
- Scrapes and monitors .onion URLs from darknetlive and ahmia using regex
- Uses Tor (via SOCKS5 proxy) to access hidden services
- Maintains SQLite database of seen/working/dead links
- Detects new/removed/changed links weekly
- Optional: clean up dead links not seen for X days
"""

import requests
import sqlite3
import datetime
import logging
import argparse
import re
import threading
import queue
from typing import List
import urllib3
import json

# ---- CONFIGURATION ----
TOR_PROXY = 'socks5h://127.0.0.1:9050'
DATABASE = 'onion_links.db'
TIMEOUT = 30
USER_AGENT = 'Mozilla/5.0 (urlfetch/1.0)'
HEADERS = {'User-Agent': USER_AGENT}
PROXIES = {'http': TOR_PROXY, 'https': TOR_PROXY}
THREAD_COUNT = 100

# ---- DISABLE WARNINGS ----
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- LOAD SOURCES ----
def load_sources_from_config(config_file='config.json'):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config.get("sources", [])

SCRAPE_SOURCES = load_sources_from_config()

# ---- LOGGING ----
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# ---- DB SETUP ----
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS onion_links (
                url TEXT PRIMARY KEY,
                status TEXT,
                last_seen TEXT
            )
        ''')
        conn.commit()

# ---- SCRAPER ----
def get_onion_links_from_url(url: str) -> List[str]:
    try:
        logging.info(f"Scraping {url}...")
        response = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=TIMEOUT, verify=False)
        raw_links = re.findall(r"https?://[a-zA-Z0-9\-\.]{10,60}\.onion(?:/[^\s\"'<]*)?", response.text)
        cleaned_links = [re.sub(r'[\/\s<]+$', '', link.strip()) for link in raw_links]
        unique_links = sorted(set(cleaned_links))
        logging.info(f"→ Found {len(unique_links)} .onion links from {url}")
        return unique_links
    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return []

def collect_onion_links() -> List[str]:
    all_links = []
    for src in SCRAPE_SOURCES:
        all_links.extend(get_onion_links_from_url(src))
    deduped = list(set(all_links))
    logging.info(f"Total unique .onion links collected: {len(deduped)}")
    return deduped

# ---- CHECK FUNCTION ----
def check_url(url: str) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=TIMEOUT)
        return r.status_code < 500
    except Exception:
        return False

# ---- THREAD WORKER ----
def worker(q: queue.Queue, now: str, stats: dict, lock: threading.Lock, batch_results: dict):
    conn = sqlite3.connect(DATABASE)
    while True:
        url = q.get()
        if url is None:
            break
        try:
            alive = check_url(url)
            cur = conn.execute("SELECT * FROM onion_links WHERE url = ?", (url,))
            row = cur.fetchone()

            if row:
                if alive:
                    conn.execute("UPDATE onion_links SET status = ?, last_seen = ? WHERE url = ?",
                                 ('alive', now, url))
                else:
                    conn.execute("UPDATE onion_links SET status = ? WHERE url = ?",
                                 ('dead', url))
            else:
                status = 'alive' if alive else 'dead'
                conn.execute("INSERT INTO onion_links (url, status, last_seen) VALUES (?, ?, ?)",
                             (url, status, now if alive else None))
            conn.commit()

            with lock:
                stats['alive' if alive else 'dead'] += 1
                batch_results['count'] += 1
                if alive:
                    batch_results['alive'] += 1
                else:
                    batch_results['dead'] += 1

                if batch_results['count'] >= 100:
                    batch_results['batch'] += 1
                    logging.info(f"Batch {batch_results['batch']}: 100 checked → {batch_results['alive']} alive, {batch_results['dead']} dead")
                    batch_results['count'] = 0
                    batch_results['alive'] = 0
                    batch_results['dead'] = 0
        except Exception as e:
            logging.error(f"DB error for {url}: {e}")
        q.task_done()
    conn.close()

# ---- UPDATE ----
def update_links(urls: List[str]):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    q = queue.Queue()
    lock = threading.Lock()
    stats = {'alive': 0, 'dead': 0}
    batch_results = {'count': 0, 'alive': 0, 'dead': 0, 'batch': 0}

    logging.info(f"Spawning {THREAD_COUNT} threads to verify {len(urls)} URLs...")

    threads = []
    for _ in range(THREAD_COUNT):
        t = threading.Thread(target=worker, args=(q, now, stats, lock, batch_results), daemon=True)
        t.start()
        threads.append(t)

    for idx, url in enumerate(urls, 1):
        q.put(url)

    q.join()

    for _ in range(THREAD_COUNT):
        q.put(None)
    for t in threads:
        t.join()

    if batch_results['count'] > 0:
        batch_results['batch'] += 1
        logging.info(f"Batch {batch_results['batch']}: {batch_results['count']} checked → {batch_results['alive']} alive, {batch_results['dead']} dead")

    logging.info(f"Finished checking. Alive: {stats['alive']}, Dead: {stats['dead']}")

# ---- CLEAN OLD DEAD LINKS ----
def clean_old_links(days: int):
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.execute("SELECT COUNT(*) FROM onion_links WHERE status = 'dead' AND (last_seen IS NULL OR last_seen < ?)", (cutoff,))
        count = cur.fetchone()[0]
        conn.execute("DELETE FROM onion_links WHERE status = 'dead' AND (last_seen IS NULL OR last_seen < ?)", (cutoff,))
        conn.commit()
    logging.info(f"Cleaned {count} dead links older than {days} days.")

# ---- MAIN ----
def main():
    parser = argparse.ArgumentParser(description="urlfetch - .onion tracker")
    parser.add_argument('--clean-old', type=int, help='Remove dead links older than N days')
    args = parser.parse_args()

    logging.info("Starting urlfetch job...")
    init_db()
    urls = collect_onion_links()
    if urls:
        update_links(urls)
    if args.clean_old:
        clean_old_links(args.clean_old)
    logging.info("urlfetch completed.")

if __name__ == '__main__':
    main()

