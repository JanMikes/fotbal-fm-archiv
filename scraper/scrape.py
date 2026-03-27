#!/usr/bin/env python3
"""
Deep scraper for mfkfm.cz - downloads every page and asset for offline archival.

Usage:
    python scrape.py                  # Full scrape (seed + enumerate + crawl + assets)
    python scrape.py --seed-only      # Only generate seed URLs and crawl (no ID enumeration)
    python scrape.py --assets-only    # Only download assets from already-scraped pages
    python scrape.py --validate       # Validate internal links in scraped pages
"""

import hashlib
import json
import os
import re
import sys
import time
import threading
import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, quote

import requests
from bs4 import BeautifulSoup

# ─── Configuration ───────────────────────────────────────────────────────────

BASE_URL = "https://mfkfm.cz"
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
PAGES_DIR = os.path.join(WEB_DIR, "pages")
ASSETS_DIR = os.path.join(WEB_DIR, "assets")
PAGE_MAP_FILE = os.path.join(WEB_DIR, "page_map.json")

REQUEST_DELAY = 0.5          # seconds between requests
MAX_RETRIES = 3
CONCURRENT_PAGES = 4
CONCURRENT_ASSETS = 8
REQUEST_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Enumeration ranges
ARTICLE_ID_MAX = 2500
MATCH_ID_MAX = 3100
GALLERY_ID_MAX = 350

SEASONS_MEN = list(range(2017, 2027))
SEASONS_YOUTH = list(range(2009, 2027))
ARCHIVE_YEARS = list(range(2012, 2027))

ZOBRAZ_PAGES = [
    "vedeni", "kontakt", "realizacni-tymy", "zmeny-v-kadru", "realizacni-tym",
    "nabor", "treneri-mladeze", "treninky-mladeze", "informace-pro-rodice",
    "desatero", "kodex", "metodika", "rozpis-treninku", "treneri-treninku",
    "nabor-deti", "galerie-skolicka", "skolicka-partneri", "plan-hriste",
    "vstupenky", "mapa", "historie", "fanzona",
]

STANDALONE_PAGES = [
    "index.asp", "partneri.asp", "tabulka.asp", "mladez.asp",
    "fotogalerie.asp", "offline.asp", "kalendar_embed.asp",
    "archiv.asp", "mladez_novinky.asp", "soupiska.asp", "statistiky.asp",
]

# Youth category codes (base codes; actual codes discovered by crawling)
YOUTH_CATEGORIES_BASE = ["DOR", "ZAC", "PRI"]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def url_key(url):
    """Normalize a URL to a canonical key for the page map."""
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path or path == "/":
        path = "index.asp"
    params = parse_qs(parsed.query, keep_blank_values=False)
    # Sort params, take first value of each
    sorted_params = sorted((k, v[0]) for k, v in params.items() if v and v[0])
    qs = urlencode(sorted_params)
    return f"{path}?{qs}" if qs else path


def url_hash(key):
    """SHA256 hash of URL key, truncated to 16 chars."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def is_internal_link(href):
    """Check if a link is internal to mfkfm.cz."""
    if not href:
        return False
    href = href.strip()
    if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
        return False
    if href.startswith("http://") or href.startswith("https://"):
        parsed = urlparse(href)
        return parsed.hostname and "mfkfm.cz" in parsed.hostname
    # Relative link
    return True


def normalize_internal_url(href, base_url=BASE_URL):
    """Convert internal link to full URL."""
    href = href.strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"{base_url}{href}"
    return f"{base_url}/{href}"


# ─── Page Map ────────────────────────────────────────────────────────────────

class PageMap:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def has(self, key):
        with self.lock:
            return key in self.data

    def add(self, key, filename, status):
        with self.lock:
            self.data[key] = {"file": filename, "status": status}

    def get(self, key):
        with self.lock:
            return self.data.get(key)

    def save(self):
        with self.lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)

    def keys(self):
        with self.lock:
            return list(self.data.keys())

    def __len__(self):
        with self.lock:
            return len(self.data)


# ─── HTTP Session ────────────────────────────────────────────────────────────

class Downloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_request = 0
        self._rate_lock = threading.Lock()

    def _rate_limit(self):
        with self._rate_lock:
            elapsed = time.time() - self._last_request
            if elapsed < REQUEST_DELAY:
                time.sleep(REQUEST_DELAY - elapsed)
            self._last_request = time.time()

    def get(self, url, retries=MAX_RETRIES):
        for attempt in range(retries):
            self._rate_limit()
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                return resp
            except requests.RequestException as e:
                if attempt == retries - 1:
                    print(f"  FAIL {url}: {e}")
                    return None
                time.sleep(2 ** attempt)
        return None

    def download_file(self, url, dest_path, retries=MAX_RETRIES):
        """Download a binary file."""
        if os.path.exists(dest_path):
            return True
        for attempt in range(retries):
            self._rate_limit()
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
                if resp.status_code == 200:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                    return True
                elif resp.status_code == 404:
                    return False
            except requests.RequestException:
                if attempt == retries - 1:
                    return False
                time.sleep(2 ** attempt)
        return False


# ─── URL Generator ───────────────────────────────────────────────────────────

def generate_seed_urls():
    """Generate the initial set of known URLs to scrape."""
    urls = set()

    # Category A: zobraz.asp static pages
    for t in ZOBRAZ_PAGES:
        urls.add(f"{BASE_URL}/zobraz.asp?t={t}")

    # Category B: standalone pages
    for page in STANDALONE_PAGES:
        urls.add(f"{BASE_URL}/{page}")

    # Category C: season-filtered listings (men's team)
    for year in SEASONS_MEN:
        urls.add(f"{BASE_URL}/zapasy.asp?sezona={year}")
        urls.add(f"{BASE_URL}/zapasy.asp?sezona={year}POH")
        urls.add(f"{BASE_URL}/zapasy.asp?sezona={year}prip")
        urls.add(f"{BASE_URL}/soupiska.asp?sezona={year}")
        urls.add(f"{BASE_URL}/statistiky.asp?sezona={year}")
        urls.add(f"{BASE_URL}/tabulka.asp?sezona={year}")

    # Category C: youth hub per season (crawling these discovers all category links)
    for year in SEASONS_YOUTH:
        urls.add(f"{BASE_URL}/mladez.asp?sezona={year}")

    # Category G: photo gallery listings per season
    for year in range(2016, 2027):
        for start in range(0, 120, 12):  # Up to 10 pages per season
            urls.add(f"{BASE_URL}/fotogalerie.asp?file=&start={start}&season={year}&search=")

    # Category H: archive combinations
    for kde in ["clanky", "aktuality"]:
        urls.add(f"{BASE_URL}/archiv.asp?kde={kde}&zobraz=posledni&kategorie=0&mesic=0&rok=0&anotace=true&razeni=0")
        for year in ARCHIVE_YEARS:
            for month in range(0, 13):  # 0 = all months
                urls.add(f"{BASE_URL}/archiv.asp?kde={kde}&zobraz=datum&kategorie=0&mesic={month}&rok={year}&anotace=true&razeni=0")

    # Category I: youth news pagination
    for start in range(0, 60, 6):
        urls.add(f"{BASE_URL}/mladez_novinky.asp?start={start}&pocet=6")

    return urls


def generate_enumeration_urls():
    """Generate URLs by enumerating ID ranges (articles, matches, galleries)."""
    urls = set()

    # Category D: articles by numeric ID
    for i in range(1, ARTICLE_ID_MAX + 1):
        urls.add(f"{BASE_URL}/clanek.asp?id={i}")

    # Category E: matches by numeric ID
    for i in range(1, MATCH_ID_MAX + 1):
        urls.add(f"{BASE_URL}/zapas.asp?id={i}")

    # Category G: galleries by numeric ID
    for i in range(1, GALLERY_ID_MAX + 1):
        urls.add(f"{BASE_URL}/media_show.asp?type=1&media=1&id={i}&url_back=fotogalerie.asp&start=0&season=0&search=")

    return urls


# ─── Link Extraction ────────────────────────────────────────────────────────

def extract_links(html, page_url):
    """Extract all internal links from HTML."""
    links = set()
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["a", "link"], href=True):
        href = tag["href"].split("#")[0].strip()
        if is_internal_link(href):
            full_url = normalize_internal_url(href)
            # Only include .asp pages (not assets)
            parsed = urlparse(full_url)
            if parsed.path.endswith(".asp") or parsed.path == "/" or not "." in parsed.path.split("/")[-1]:
                links.add(full_url)

    return links


def extract_asset_urls(html, page_url):
    """Extract all asset URLs (images, CSS, JS, PDFs) from HTML."""
    assets = set()
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # img src
    for tag in soup.find_all("img", src=True):
        assets.add(tag["src"])

    # link href (CSS)
    for tag in soup.find_all("link", href=True):
        href = tag["href"]
        if href.endswith(".css") or "stylesheet" in str(tag.get("rel", "")):
            assets.add(href)

    # script src
    for tag in soup.find_all("script", src=True):
        src = tag["src"]
        if is_internal_link(src) or "esports" in src:
            assets.add(src)

    # a href to files (PDFs, docs, etc.)
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if re.search(r"\.(pdf|doc|docx|xls|xlsx|zip|rar)$", href, re.I):
            assets.add(href)

    # Background images in style attributes
    for tag in soup.find_all(style=True):
        urls = re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', tag["style"])
        assets.update(urls)

    # Inline CSS
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            urls = re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', style_tag.string)
            assets.update(urls)

    # esgallery data attributes and JS image arrays
    html_text = str(soup)
    # Match image paths in JavaScript
    img_patterns = re.findall(r'["\'](/foto/[^"\']+)["\']', html_text)
    assets.update(img_patterns)
    img_patterns = re.findall(r'["\'](/img/[^"\']+)["\']', html_text)
    assets.update(img_patterns)
    img_patterns = re.findall(r'["\'](/znaky/[^"\']+)["\']', html_text)
    assets.update(img_patterns)
    img_patterns = re.findall(r'["\'](/ads/[^"\']+)["\']', html_text)
    assets.update(img_patterns)
    img_patterns = re.findall(r'["\'](/soubory/[^"\']+)["\']', html_text)
    assets.update(img_patterns)
    img_patterns = re.findall(r'["\'](/inc/[^"\']+)["\']', html_text)
    assets.update(img_patterns)

    # php.esports.cz image proxy URLs
    esports_urls = re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', html_text)
    assets.update(esports_urls)

    return assets


# ─── HTML Processing ─────────────────────────────────────────────────────────

def process_html(html):
    """Post-process HTML: rewrite absolute URLs, strip tracking."""
    # Replace absolute domain references with relative
    html = re.sub(r'https?://(?:www\.)?mfkfm\.cz/', '/', html)

    # Strip Google Analytics
    html = re.sub(
        r'<script[^>]*google[_-]?analytics[^>]*>.*?</script>',
        '', html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(
        r'<script[^>]*gtag[^>]*>.*?</script>',
        '', html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(
        r"<script[^>]*>\s*\(function\s*\(\s*i\s*,\s*s\s*,\s*o\s*,\s*g\s*,\s*r\s*,\s*a\s*,\s*m\s*\).*?</script>",
        '', html, flags=re.DOTALL
    )

    # Strip TOPlist tracking
    html = re.sub(
        r'<script[^>]*toplist[^>]*>.*?</script>',
        '', html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(
        r'<a[^>]*toplist[^>]*>.*?</a>',
        '', html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(
        r'<img[^>]*toplist[^>]*/?>', '', html, flags=re.IGNORECASE
    )

    return html


def process_esports_url(url, html):
    """Replace php.esports.cz image proxy URLs with local paths."""
    esports_urls = re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', html)
    for esports_url in esports_urls:
        # Create a deterministic local filename
        h = hashlib.sha256(esports_url.encode()).hexdigest()[:16]
        # Try to extract original extension
        ext = ".jpg"
        file_match = re.search(r'file=[^&]*\.(\w{2,4})(?:[&\s"\']|$)', esports_url)
        if file_match:
            ext = f".{file_match.group(1).lower()}"
        local_path = f"/assets/esports/{h}{ext}"
        html = html.replace(esports_url, local_path)
    return html


# ─── Scraper Orchestrator ───────────────────────────────────────────────────

class Scraper:
    def __init__(self):
        self.downloader = Downloader()
        self.page_map = PageMap(PAGE_MAP_FILE)
        self.queue = deque()
        self.queued = set()  # All URLs ever added to queue
        self.queue_lock = threading.Lock()
        self.stats = {"downloaded": 0, "skipped": 0, "failed": 0, "discovered": 0}
        self.all_asset_urls = set()
        self.asset_lock = threading.Lock()

    def enqueue(self, url):
        """Add URL to queue if not already processed."""
        key = url_key(url)
        with self.queue_lock:
            if key not in self.queued and not self.page_map.has(key):
                self.queued.add(key)
                self.queue.append(url)
                return True
            return False

    def enqueue_many(self, urls):
        """Add multiple URLs to queue."""
        count = 0
        for url in urls:
            if self.enqueue(url):
                count += 1
        return count

    def download_page(self, url):
        """Download a single page, process it, extract links."""
        key = url_key(url)

        # Skip if already in map
        if self.page_map.has(key):
            self.stats["skipped"] += 1
            return

        resp = self.downloader.get(url)
        if resp is None:
            self.stats["failed"] += 1
            return

        status = resp.status_code

        # For non-200 responses on enumerated IDs, skip storage
        if status == 404:
            self.page_map.add(key, None, 404)
            self.stats["skipped"] += 1
            return

        if status != 200:
            # Still store redirects etc.
            if status in (301, 302, 303, 307, 308):
                self.page_map.add(key, None, status)
                self.stats["skipped"] += 1
                return

        # Check if we got a real page (not a soft 404 / redirect to index)
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            self.page_map.add(key, None, status)
            self.stats["skipped"] += 1
            return

        html = resp.text

        # Detect soft 404 for enumerated pages: if the page is just the homepage
        # when we requested a specific article/match, skip it
        if ("clanek.asp?id=" in url or "zapas.asp?id=" in url) and status == 200:
            # Check if page title or content suggests it's a valid page
            if "<title>" in html:
                title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
                    # If title is just the generic homepage title, it's a soft 404
                    if title in ("MFK Frýdek-Místek", "FK Frýdek-Místek") and "clanek.asp" in url:
                        # Check if article content div is empty
                        if 'class="clanek"' not in html and 'class="article"' not in html:
                            self.page_map.add(key, None, 404)
                            self.stats["skipped"] += 1
                            return

        # Process HTML
        html = process_html(html)
        html = process_esports_url(url, html)

        # Save
        h = url_hash(key)
        filename = f"pages/{h}.html"
        filepath = os.path.join(WEB_DIR, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        self.page_map.add(key, filename, status)
        self.stats["downloaded"] += 1

        # Extract and enqueue discovered links
        try:
            new_links = extract_links(html, url)
            added = self.enqueue_many(new_links)
            if added > 0:
                self.stats["discovered"] += added
        except Exception as e:
            print(f"  Link extraction error for {url}: {e}")

        # Collect asset URLs
        try:
            assets = extract_asset_urls(resp.text, url)  # Use original HTML for assets
            with self.asset_lock:
                self.all_asset_urls.update(assets)
        except Exception as e:
            print(f"  Asset extraction error for {url}: {e}")

    def run_page_scraping(self, seed_urls, enum_urls=None):
        """Main scraping loop: process seed URLs, then enumeration URLs, then crawl discovered."""
        print(f"\n{'='*60}")
        print(f"Phase 1: Seed URLs ({len(seed_urls)} URLs)")
        print(f"{'='*60}")
        self.enqueue_many(seed_urls)
        self._process_queue()

        if enum_urls:
            print(f"\n{'='*60}")
            print(f"Phase 2: Enumeration URLs ({len(enum_urls)} URLs)")
            print(f"{'='*60}")
            self.enqueue_many(enum_urls)
            self._process_queue()

        print(f"\n{'='*60}")
        print(f"Phase 3: Crawl discovered URLs")
        print(f"{'='*60}")
        # The queue may have grown from link discovery; keep processing
        self._process_queue()

        # Save map
        self.page_map.save()
        self._print_stats()

    def _process_queue(self):
        """Process all URLs in the queue with thread pool."""
        batch_size = 100
        total_processed = 0

        while True:
            # Collect a batch
            batch = []
            with self.queue_lock:
                while self.queue and len(batch) < batch_size:
                    batch.append(self.queue.popleft())

            if not batch:
                break

            with ThreadPoolExecutor(max_workers=CONCURRENT_PAGES) as executor:
                futures = {executor.submit(self.download_page, url): url for url in batch}
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"  Error: {e}")
                    total_processed += 1
                    if total_processed % 100 == 0:
                        print(f"  Progress: {total_processed} processed, "
                              f"{self.stats['downloaded']} downloaded, "
                              f"{len(self.queue)} in queue")

            # Save map periodically
            if total_processed % 500 == 0:
                self.page_map.save()

    def _print_stats(self):
        print(f"\n--- Scraping Stats ---")
        print(f"  Downloaded: {self.stats['downloaded']}")
        print(f"  Skipped (404/redirect/already done): {self.stats['skipped']}")
        print(f"  Failed: {self.stats['failed']}")
        print(f"  Discovered via crawling: {self.stats['discovered']}")
        print(f"  Total in page map: {len(self.page_map)}")

    # ─── Asset Downloading ───────────────────────────────────────────────────

    def collect_all_assets(self):
        """Parse all stored HTML files and collect asset URLs."""
        print(f"\nCollecting asset URLs from {len(self.page_map)} pages...")
        all_assets = set()

        for key in self.page_map.keys():
            entry = self.page_map.get(key)
            if not entry or not entry.get("file"):
                continue
            filepath = os.path.join(WEB_DIR, entry["file"])
            if not os.path.exists(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    html = f.read()
                assets = extract_asset_urls(html, key)
                all_assets.update(assets)
            except Exception as e:
                print(f"  Error reading {filepath}: {e}")

        # Also include assets found during scraping
        all_assets.update(self.all_asset_urls)

        print(f"  Found {len(all_assets)} unique asset URLs")
        return all_assets

    def download_assets(self, asset_urls):
        """Download all static assets."""
        print(f"\n{'='*60}")
        print(f"Downloading {len(asset_urls)} assets")
        print(f"{'='*60}")

        esports_urls = set()
        local_assets = set()

        for url in asset_urls:
            url = url.strip()
            if not url:
                continue

            # php.esports.cz proxy images
            if "php.esports.cz" in url:
                esports_urls.add(url)
                continue

            # Skip external URLs (except esports)
            if url.startswith("http://") or url.startswith("https://"):
                if "mfkfm.cz" not in url:
                    continue
                # Convert absolute to relative path
                parsed = urlparse(url)
                url = parsed.path
                if parsed.query:
                    url += f"?{parsed.query}"

            # Skip non-file URLs
            if url.startswith("javascript:") or url.startswith("mailto:") or url.startswith("#"):
                continue

            # Clean path
            path = url.lstrip("/").split("?")[0].split("#")[0]
            if not path:
                continue

            # Only download known asset directories
            asset_prefixes = ("img/", "foto/", "znaky/", "ads/", "soubory/", "inc/", "css/")
            if not any(path.startswith(p) for p in asset_prefixes):
                continue

            local_assets.add((f"{BASE_URL}/{path}", os.path.join(ASSETS_DIR, path)))

        # Download local assets
        downloaded = 0
        failed = 0
        skipped = 0

        def download_one(item):
            nonlocal downloaded, failed, skipped
            src_url, dest_path = item
            if os.path.exists(dest_path):
                skipped += 1
                return
            if self.downloader.download_file(src_url, dest_path):
                downloaded += 1
            else:
                failed += 1

        with ThreadPoolExecutor(max_workers=CONCURRENT_ASSETS) as executor:
            futures = [executor.submit(download_one, item) for item in local_assets]
            for i, future in enumerate(as_completed(futures)):
                try:
                    future.result()
                except Exception as e:
                    print(f"  Asset error: {e}")
                if (i + 1) % 200 == 0:
                    print(f"  Assets progress: {i+1}/{len(local_assets)} "
                          f"(downloaded: {downloaded}, skipped: {skipped})")

        print(f"\n  Local assets: downloaded={downloaded}, skipped={skipped}, failed={failed}")

        # Download esports proxy images
        print(f"\n  Downloading {len(esports_urls)} esports proxy images...")
        es_downloaded = 0
        es_failed = 0

        def download_esports(esports_url):
            nonlocal es_downloaded, es_failed
            h = hashlib.sha256(esports_url.encode()).hexdigest()[:16]
            ext = ".jpg"
            file_match = re.search(r'file=[^&]*\.(\w{2,4})(?:[&\s"\']|$)', esports_url)
            if file_match:
                ext = f".{file_match.group(1).lower()}"
            dest = os.path.join(ASSETS_DIR, "esports", f"{h}{ext}")
            if os.path.exists(dest):
                return
            if self.downloader.download_file(esports_url, dest):
                es_downloaded += 1
            else:
                es_failed += 1

        with ThreadPoolExecutor(max_workers=CONCURRENT_ASSETS) as executor:
            futures = [executor.submit(download_esports, url) for url in esports_urls]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        print(f"  Esports images: downloaded={es_downloaded}, failed={es_failed}")

    # ─── Post-processing ─────────────────────────────────────────────────────

    def postprocess_all_pages(self):
        """Re-process all stored pages to fix esports URLs after assets are downloaded."""
        print(f"\nPost-processing {len(self.page_map)} pages...")
        count = 0
        for key in self.page_map.keys():
            entry = self.page_map.get(key)
            if not entry or not entry.get("file"):
                continue
            filepath = os.path.join(WEB_DIR, entry["file"])
            if not os.path.exists(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    html = f.read()

                new_html = process_esports_url("", html)
                # Also ensure absolute URLs are relative
                new_html = re.sub(r'https?://(?:www\.)?mfkfm\.cz/', '/', new_html)

                if new_html != html:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_html)
                    count += 1
            except Exception as e:
                print(f"  Error processing {filepath}: {e}")

        print(f"  Updated {count} pages")

    # ─── Validation ──────────────────────────────────────────────────────────

    def validate_links(self):
        """Check all internal links in stored pages resolve to known pages or assets."""
        print(f"\n{'='*60}")
        print(f"Validating internal links")
        print(f"{'='*60}")

        broken = []
        checked = 0

        for key in self.page_map.keys():
            entry = self.page_map.get(key)
            if not entry or not entry.get("file"):
                continue
            filepath = os.path.join(WEB_DIR, entry["file"])
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    html = f.read()
                soup = BeautifulSoup(html, "lxml")

                for tag in soup.find_all(["a", "img", "link", "script"], True):
                    attr = "src" if tag.name in ("img", "script") else "href"
                    val = tag.get(attr)
                    if not val:
                        continue
                    val = val.strip().split("#")[0]
                    if not val or not is_internal_link(val):
                        continue

                    # Check if it's a page
                    full_url = normalize_internal_url(val)
                    target_key = url_key(full_url)

                    if self.page_map.has(target_key):
                        target = self.page_map.get(target_key)
                        if target and target.get("status") == 200:
                            continue

                    # Check if it's an asset
                    path = val.lstrip("/").split("?")[0]
                    asset_path = os.path.join(ASSETS_DIR, path)
                    if os.path.exists(asset_path):
                        continue

                    # Also check directly in web dir (for assets served via rewrite)
                    web_path = os.path.join(WEB_DIR, "assets", path)
                    if os.path.exists(web_path):
                        continue

                    broken.append((key, val))
                    checked += 1

            except Exception as e:
                print(f"  Error validating {filepath}: {e}")

        if broken:
            print(f"\n  Found {len(broken)} broken internal links:")
            # Group by target
            by_target = {}
            for source, target in broken:
                by_target.setdefault(target, []).append(source)
            for target, sources in sorted(by_target.items())[:50]:
                print(f"    {target} (from {len(sources)} pages)")
        else:
            print(f"  All internal links are valid!")

        return broken


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deep scraper for mfkfm.cz")
    parser.add_argument("--seed-only", action="store_true", help="Only scrape seed URLs (no ID enumeration)")
    parser.add_argument("--assets-only", action="store_true", help="Only download assets from already-scraped pages")
    parser.add_argument("--validate", action="store_true", help="Validate internal links")
    parser.add_argument("--postprocess", action="store_true", help="Re-process HTML files")
    args = parser.parse_args()

    os.makedirs(PAGES_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)

    scraper = Scraper()

    if args.validate:
        scraper.validate_links()
        return

    if args.postprocess:
        scraper.postprocess_all_pages()
        scraper.page_map.save()
        return

    if args.assets_only:
        asset_urls = scraper.collect_all_assets()
        scraper.download_assets(asset_urls)
        scraper.postprocess_all_pages()
        scraper.page_map.save()
        return

    # Full scrape
    seed_urls = generate_seed_urls()
    print(f"Generated {len(seed_urls)} seed URLs")

    enum_urls = None
    if not args.seed_only:
        enum_urls = generate_enumeration_urls()
        print(f"Generated {len(enum_urls)} enumeration URLs")

    scraper.run_page_scraping(seed_urls, enum_urls)

    # Download assets
    asset_urls = scraper.collect_all_assets()
    scraper.download_assets(asset_urls)

    # Final post-processing
    scraper.postprocess_all_pages()
    scraper.page_map.save()

    print(f"\n{'='*60}")
    print(f"DONE! Total pages in map: {len(scraper.page_map)}")
    print(f"{'='*60}")

    # Quick validation
    broken = scraper.validate_links()
    if broken:
        print(f"\nWARNING: {len(broken)} broken links found. Run with --validate for details.")


if __name__ == "__main__":
    main()
