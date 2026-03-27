#!/usr/bin/env python3
"""
Download all static assets (images, CSS, JS, PDFs) referenced in scraped pages.
Run this after scrape.py has finished downloading pages.
"""

import hashlib
import json
import os
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

BASE_URL = "https://mfkfm.cz"
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
PAGES_DIR = os.path.join(WEB_DIR, "pages")
ASSETS_DIR = os.path.join(WEB_DIR, "assets")
PAGE_MAP_FILE = os.path.join(WEB_DIR, "page_map.json")

REQUEST_DELAY = 0.2
CONCURRENT = 6
TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def extract_all_asset_paths(html):
    """Extract all local asset paths from HTML content."""
    paths = set()

    # Match src="..." and href="..." attributes
    for match in re.findall(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', html, re.IGNORECASE):
        paths.add(match)

    # Match url(...) in CSS
    for match in re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', html):
        paths.add(match)

    # Match paths in JS strings
    for prefix in ['/foto/', '/img/', '/znaky/', '/ads/', '/soubory/', '/inc/']:
        for match in re.findall(rf'["\']({re.escape(prefix)}[^"\'<>\s]+)["\']', html):
            paths.add(match)

    return paths


def extract_esports_urls(html):
    """Extract php.esports.cz URLs from HTML."""
    return set(re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', html))


def normalize_asset_path(raw_path):
    """Convert a raw path/URL to a local asset path, or None if not a local asset."""
    path = raw_path.strip()
    if not path:
        return None

    # Skip non-asset stuff
    if path.startswith(('javascript:', 'mailto:', '#', 'data:')):
        return None

    # Handle absolute URLs pointing to mfkfm.cz
    if path.startswith(('http://', 'https://')):
        if 'mfkfm.cz' not in path:
            return None
        parsed = urlparse(path)
        path = parsed.path

    # Already rewritten esports path
    if path.startswith('/assets/esports/'):
        return None  # These come from esports proxy, handled separately

    # Strip leading slash, query params, fragments
    path = path.lstrip('/').split('?')[0].split('#')[0]
    if not path:
        return None

    # Only known asset directories
    PREFIXES = ('img/', 'foto/', 'znaky/', 'ads/', 'soubory/', 'inc/', 'css/')
    if not any(path.startswith(p) for p in PREFIXES):
        return None

    return path


def download_file(url, dest_path, retries=3):
    """Download a single file. Returns True on success."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return "skip"

    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY)
            resp = session.get(url, timeout=TIMEOUT, stream=True)
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                return "ok"
            elif resp.status_code == 404:
                return "404"
            else:
                return "error"
        except requests.RequestException:
            if attempt == retries - 1:
                return "error"
            time.sleep(2 ** attempt)
    return "error"


def main():
    # Load page map
    with open(PAGE_MAP_FILE, "r") as f:
        page_map = json.load(f)

    print(f"Scanning {len(page_map)} pages for asset references...")

    # Phase 1: Collect all asset paths and esports URLs from stored HTML files
    all_asset_paths = set()
    all_esports_urls = set()
    scanned = 0

    for key, entry in page_map.items():
        if not entry or not entry.get("file"):
            continue
        filepath = os.path.join(WEB_DIR, entry["file"])
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()

            # Extract local asset paths
            raw_paths = extract_all_asset_paths(html)
            for raw in raw_paths:
                norm = normalize_asset_path(raw)
                if norm:
                    all_asset_paths.add(norm)

            scanned += 1
        except Exception as e:
            print(f"  Error reading {filepath}: {e}")

    print(f"  Scanned {scanned} pages")
    print(f"  Found {len(all_asset_paths)} unique local asset paths")

    # Phase 2: Also fetch original pages from the server to get esports URLs
    # (since they were rewritten in stored HTML)
    # Instead, let's check a sample of original pages
    print(f"\nFetching esports URLs from a sample of original pages...")
    sample_keys = [k for k in page_map if k.startswith(('hrac.asp', 'soupiska.asp', 'index.asp', 'zapas.asp'))]
    esports_checked = 0
    for key in sample_keys[:500]:
        try:
            url = f"{BASE_URL}/{key}"
            time.sleep(REQUEST_DELAY)
            resp = session.get(url, timeout=TIMEOUT)
            if resp.status_code == 200:
                esports = extract_esports_urls(resp.text)
                all_esports_urls.update(esports)
                esports_checked += 1
                if esports_checked % 50 == 0:
                    print(f"  Checked {esports_checked} pages, found {len(all_esports_urls)} esports URLs")
        except Exception:
            pass

    print(f"  Total esports URLs found: {len(all_esports_urls)}")

    # Phase 3: Download local assets
    print(f"\n{'='*60}")
    print(f"Downloading {len(all_asset_paths)} local assets")
    print(f"{'='*60}")

    stats = {"ok": 0, "skip": 0, "404": 0, "error": 0}

    items = [(path, f"{BASE_URL}/{path}", os.path.join(ASSETS_DIR, path)) for path in sorted(all_asset_paths)]

    for i, (path, url, dest) in enumerate(items):
        result = download_file(url, dest)
        stats[result] += 1
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(items)}] ok={stats['ok']} skip={stats['skip']} 404={stats['404']} err={stats['error']}")

    print(f"\n  Final: ok={stats['ok']} skip={stats['skip']} 404={stats['404']} err={stats['error']}")

    # Phase 4: Download esports proxy images
    if all_esports_urls:
        print(f"\n{'='*60}")
        print(f"Downloading {len(all_esports_urls)} esports proxy images")
        print(f"{'='*60}")

        es_stats = {"ok": 0, "skip": 0, "404": 0, "error": 0}

        for i, esports_url in enumerate(sorted(all_esports_urls)):
            h = hashlib.sha256(esports_url.encode()).hexdigest()[:16]
            ext = ".jpg"
            file_match = re.search(r'file=[^&]*\.(\w{2,4})(?:[&\s"\']|$)', esports_url)
            if file_match:
                ext = f".{file_match.group(1).lower()}"
            dest = os.path.join(ASSETS_DIR, "esports", f"{h}{ext}")
            result = download_file(esports_url, dest)
            es_stats[result] += 1
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(all_esports_urls)}] ok={es_stats['ok']} skip={es_stats['skip']}")

        print(f"\n  Final: ok={es_stats['ok']} skip={es_stats['skip']} 404={es_stats['404']} err={es_stats['error']}")

    # Summary
    total_assets = 0
    for root, dirs, files in os.walk(ASSETS_DIR):
        total_assets += len(files)
    total_size = sum(
        os.path.getsize(os.path.join(root, f))
        for root, dirs, files in os.walk(ASSETS_DIR)
        for f in files
    )
    print(f"\n{'='*60}")
    print(f"DONE! Total asset files: {total_assets}, Size: {total_size / (1024*1024):.1f} MB")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
