import requests
import json
import sqlite3
import argparse
from bs4 import BeautifulSoup

TOR_PROXY = "socks5h://127.0.0.1:9050"
PROXIES = {"http": TOR_PROXY, "https": TOR_PROXY}
TIMEOUT = 60
CONFIG_FILE = "config.json"
DATABASE = "onion_links.db"

def get_exit_node_ip():
    try:
        r = requests.get("http://httpbin.org/ip", proxies=PROXIES, timeout=10)
        return r.json().get("origin", "Unknown")
    except:
        return "Unavailable"

def load_sources(config_file=CONFIG_FILE):
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            return config.get('sources', [])
    except Exception as e:
        print(f"Failed to load sources from config: {e}")
        return []

def load_alive_from_db(db=DATABASE):
    try:
        with sqlite3.connect(db) as conn:
            rows = conn.execute("SELECT url FROM onion_links WHERE status = 'alive'")
            return [row[0] for row in rows]
    except Exception as e:
        print(f"Failed to load URLs from DB: {e}")
        return []

def check_onion(url):
    try:
        r = requests.get(url, proxies=PROXIES, timeout=TIMEOUT)
        status = r.status_code
        try:
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.title.string.strip() if soup.title and soup.title.string else ''
        except:
            title = ''
        return True, status, title
    except Exception as e:
        return False, None, str(e)

def main():
    parser = argparse.ArgumentParser(description="Check .onion sites")
    parser.add_argument('--from-db', action='store_true', help='Test URLs from alive status in onion_links.db')
    args = parser.parse_args()

    print("[*] Detecting Tor exit IP...")
    exit_ip = get_exit_node_ip()
    print(f"→ Tor Exit IP: {exit_ip}\n")

    if args.from_db:
        links = load_alive_from_db()
        if not links:
            print("No alive URLs found in the database.")
            return
    else:
        links = load_sources()
        if not links:
            print("No sources found in config.json.")
            return

    for link in links:
        print(f"[+] Checking: {link}")
        alive, status, info = check_onion(link)
        if alive:
            print(f"   → Alive (HTTP {status}) | Title: {info}")
        else:
            print(f"   → Dead or blocked | Error: {info}")
        print()

if __name__ == '__main__':
    main()

