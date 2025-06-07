# onionfilter-prototype

**onionfilter-prototype** is a lightweight yet powerful tool designed to scrape, verify, and filter `.onion` URLs from publicly available dark web sources. It serves as a foundational prototype to complement existing dark web monitoring or threat intelligence workflows. It is open for use and support.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Installation & Requirements](#installation--requirements)
4. [Configuration](#configuration)
5. [Usage](#usage)

   * [Fetching Onion URLs](#fetching-onion-urls)
   * [Filtering Alive URLs](#filtering-alive-urls)
   * [Testing URLs Manually](#testing-urls-manually)
6. [Database Structure](#database-structure)
7. [Example Commands](#example-commands)
8. [Recommended `.gitignore`](#recommended-gitignore)
9. [Use Cases](#use-cases)
10. [Future Enhancements](#future-enhancements)
11. [Disclaimer & Legal Notice](#disclaimer--legal-notice)
12. [License](#license)
13. [Credits](#credits)

---

## Introduction

`onionfilter-prototype` helps security researchers and enthusiasts quickly gather and analyze `.onion` addresses from open sources, verifying their status and scanning their content for security-sensitive keywords. It's ideal as a complementary tool for:

* Security operations (SOC) teams
* Threat intelligence analysts
* Cybersecurity researchers

---

## Features

* **Scraping:** Gathers `.onion` URLs from specified dark web sources.
* **Verification:** Checks if `.onion` links are live via the Tor network.
* **Keyword Filtering:** Identifies and stores pages containing keywords indicative of breaches or leaks.
* **Databases:** Stores results in SQLite databases for efficient analysis.
* **Customizable:** Modular and easily configurable via `config.json`.

---

## Installation & Requirements

### Requirements:

* **Python 3.9+**
* **Tor** (configured as a local SOCKS5 proxy at `127.0.0.1:9050`)

### Python Dependencies:

Install via pip:

```bash
pip install requests beautifulsoup4
```

Ensure Tor is running locally:

```bash
systemctl start tor
```

---

## Configuration

Configuration is handled via `config.json`:

```json
{
  "sources": [
    "https://ahmia.fi/onions/",
    "https://onion.live/"
  ],
  "keywords": [
    "breach", "leak", "dump", "credentials", "combo list"
  ],
  "scam_patterns": [
    "bitcoin doubler", "free bitcoin"
  ]
}
```

* **sources**: URLs where `.onion` addresses are scraped from.
* **keywords**: Words indicating potential breaches/leaks.
* **scam\_patterns**: Patterns indicating scams.

---

## Usage

### Fetching Onion URLs

Scrape URLs and update their live status:

```bash
python urlfetch.py
```

Clean up old dead links after 7 days:

```bash
python urlfetch.py --clean-old 7
```

---

### Filtering Alive URLs

Filter alive URLs based on keywords:

```bash
python filter.py
```

Filtered results are stored in `filtered_onions.db`.

---

### Testing URLs Manually

Check URLs from database or sources manually and view Tor exit IP:

* Test alive links from database:

```bash
python test.py --from-db
```

* Check URLs directly from sources:

```bash
python test.py
```

---

## Database Structure

### `onion_links.db`

* `url`: URL of `.onion` link
* `status`: `alive` or `dead`
* `last_seen`: Timestamp when last seen alive

### `filtered_onions.db`

* `url`: Filtered `.onion` URL
* `title`: Webpage title
* `matched_keywords`: Keywords matched from content
* `context_snippet`: Snippet from content where keyword was matched

---

## Example Commands

1. **Run full workflow (fetch + filter):**

```bash
python urlfetch.py && python filter.py
```

2. **Routine maintenance (weekly):**

```bash
python urlfetch.py --clean-old 7 && python filter.py
```

3. **Check current Tor exit node IP:**

```bash
python test.py
```

---

## Recommended `.gitignore`

```gitignore
onion_links.db
filtered_onions.db
.env/
__pycache__/
```

---

## Use Cases

* Complement larger dark web monitoring platforms
* Educational purposes for cybersecurity training
* Prototype for threat intelligence workflows
* Enrich cybersecurity investigations

---

## Disclaimer & Legal Notice

* This tool is provided for educational and research purposes only.
* Users are fully responsible for the ethical and lawful usage of the tool.
* Do not store or interact with illegal content.
* Comply with local laws and regulations at all times.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Credits

* Developed by [saretawa](https://github.com/saretawa)
* Inspired by various cybersecurity threat intelligence techniques and open-source projects

---
