import requests
import sqlite3
import re
import logging
import json
from bs4 import BeautifulSoup, Tag
from typing import Tuple
from time import sleep

class OnionFilter:
    def __init__(self, source_db='onion_links.db', dest_db='filtered_onions.db', config_file='config.json'):
        self.source_db = source_db
        self.dest_db = dest_db
        self.config_file = config_file
        self.timeout = 60
        self.retry_delay = 3
        self.headers = {'User-Agent': 'Mozilla/5.0 (filter/2.2)'}
        self.proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        self.keywords, self.scam_patterns = self.load_config()

    def load_config(self) -> Tuple[list, list]:
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('keywords', []), config.get('scam_patterns', [])
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return [], []

    def init_db(self):
        with sqlite3.connect(self.dest_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS filtered_links (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    matched_keywords TEXT,
                    context_snippet TEXT
                )
            ''')
            conn.commit()

    def get_alive_urls(self):
        with sqlite3.connect(self.source_db) as conn:
            return [row[0] for row in conn.execute("SELECT url FROM onion_links WHERE status = 'alive'")]

    def extract_features(self, soup: BeautifulSoup) -> Tuple[str, str, str]:
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        headers = " ".join(h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3']))
        bold = " ".join(b.get_text(strip=True) for b in soup.find_all(['b', 'strong']))
        pre = " ".join(p.get_text(strip=True) for p in soup.find_all(['pre', 'code']))
        meta = " ".join(str(m.get('content', '')) for m in soup.find_all('meta') if isinstance(m, Tag) and m.get('content'))
        body = soup.get_text(separator=' ', strip=True)
        combined = f"{title} {meta} {headers} {bold} {pre}".lower()
        return title, combined, body

    def scan_url(self, url: str) -> Tuple[str, list, str]:
        for attempt in range(3):
            try:
                res = requests.get(url, headers=self.headers, proxies=self.proxies,
                                   timeout=self.timeout, allow_redirects=True)
                soup = BeautifulSoup(res.text, 'html.parser')
                title, combined, body = self.extract_features(soup)
                matches = [kw for kw in self.keywords if re.search(rf'\b{re.escape(kw)}\b', combined + ' ' + body, re.IGNORECASE)]
                snippet = ""
                if matches:
                    match_pos = body.lower().find(matches[0].lower())
                    snippet = body[max(0, match_pos - 80):match_pos + 120]
                return title, matches, snippet
            except requests.exceptions.RequestException as e:
                logging.warning(f"[RETRY {attempt+1}] {url}: {e}")
                sleep(self.retry_delay + attempt * 2)
            except Exception as e:
                logging.warning(f"[FAIL] {url}: {e}")
                break
        return "", [], ""

    def run(self):
        self.init_db()
        urls = self.get_alive_urls()
        logging.info(f"Scanning {len(urls)} alive links...")

        with sqlite3.connect(self.dest_db) as conn:
            for url in urls:
                title, matches, snippet = self.scan_url(url)
                if matches:
                    conn.execute('''INSERT OR REPLACE INTO filtered_links 
                                    (url, title, matched_keywords, context_snippet) 
                                    VALUES (?, ?, ?, ?)''',
                                 (url, title, ', '.join(matches), snippet))
                    conn.commit()
                    logging.info(f"[MATCH] {url}\n ↳ Title: {title or 'N/A'}\n ↳ Keywords: {matches}")
        logging.info("Deep filtering completed.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    OnionFilter().run()

