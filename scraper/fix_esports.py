#!/usr/bin/env python3
"""
Fix esports image references in all scraped HTML pages.

The original scraper used a broken regex that produced wrong file extensions.
This script:
1. Fetches original pages from the server to collect all esports URLs
2. Computes correct hash -> extension mapping
3. Downloads images with correct filenames
4. Fixes all HTML references
"""

import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict

import requests

BASE_URL = "https://mfkfm.cz"
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
ASSETS_DIR = os.path.join(WEB_DIR, "assets")
ESPORTS_DIR = os.path.join(ASSETS_DIR, "esports")
PAGE_MAP_FILE = os.path.join(WEB_DIR, "page_map.json")

REQUEST_DELAY = 0.3
TIMEOUT = 30

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})


def esports_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def get_correct_ext(esports_url):
    """Extract correct file extension from the file= parameter of an esports URL."""
    m = re.search(r'file=([^&\s"\']+)', esports_url)
    if m:
        file_val = m.group(1)
        ext_m = re.search(r'\.(\w{2,4})$', file_val)
        if ext_m:
            return f".{ext_m.group(1).lower()}"
    return ".jpg"


def main():
    with open(PAGE_MAP_FILE, "r") as f:
        page_map = json.load(f)

    # Step 1: Collect all esports URLs by fetching original pages from server
    print("Step 1: Collecting esports URLs from original site...")

    # Focus on pages that likely contain esports images
    target_keys = []
    for key in page_map:
        if page_map[key].get("status") == 200:
            base = key.split("?")[0]
            if base in ("hrac.asp", "soupiska.asp", "index.asp", "zapas.asp",
                        "zapasy.asp", "clanek.asp", "mladez.asp", "tabulka.asp",
                        "statistiky.asp", "media_show.asp"):
                target_keys.append(key)

    print(f"  Will check {len(target_keys)} pages for esports URLs")

    # hash -> {url, correct_ext}
    esports_map = {}
    checked = 0
    errors = 0

    for key in target_keys:
        try:
            time.sleep(REQUEST_DELAY)
            resp = session.get(f"{BASE_URL}/{key}", timeout=TIMEOUT)
            if resp.status_code == 200:
                urls = re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', resp.text)
                # HTML entities may be in the URL
                urls_decoded = []
                for u in urls:
                    u = u.replace("&amp;", "&")
                    urls_decoded.append(u)

                for url in urls_decoded:
                    h = esports_hash(url)
                    if h not in esports_map:
                        ext = get_correct_ext(url)
                        esports_map[h] = {"url": url, "ext": ext}

                checked += 1
                if checked % 100 == 0:
                    print(f"  Checked {checked}/{len(target_keys)} pages, "
                          f"found {len(esports_map)} unique esports images")
        except Exception as e:
            errors += 1
            if errors % 50 == 1:
                print(f"  Error at page {checked}: {e}")

    print(f"  Done: checked {checked} pages, found {len(esports_map)} unique esports images, {errors} errors")

    # Save the mapping for reference
    mapping_file = os.path.join(WEB_DIR, "esports_map.json")
    with open(mapping_file, "w") as f:
        json.dump(esports_map, f, indent=1)
    print(f"  Saved esports map to {mapping_file}")

    # Step 2: Clean up esports directory and download with correct filenames
    print("\nStep 2: Downloading esports images with correct filenames...")

    # Remove all existing files first
    if os.path.exists(ESPORTS_DIR):
        for f in os.listdir(ESPORTS_DIR):
            os.remove(os.path.join(ESPORTS_DIR, f))
    os.makedirs(ESPORTS_DIR, exist_ok=True)

    downloaded = 0
    failed = 0

    for h, info in sorted(esports_map.items()):
        dest = os.path.join(ESPORTS_DIR, f"{h}{info['ext']}")
        try:
            time.sleep(REQUEST_DELAY)
            resp = session.get(info["url"], timeout=TIMEOUT, stream=True)
            if resp.status_code == 200:
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                downloaded += 1
            else:
                failed += 1
        except Exception:
            failed += 1

        if (downloaded + failed) % 50 == 0:
            print(f"  Progress: {downloaded + failed}/{len(esports_map)} "
                  f"(downloaded: {downloaded}, failed: {failed})")

    print(f"  Done: downloaded {downloaded}, failed {failed}")

    # Step 3: Fix HTML references in all stored pages
    print("\nStep 3: Fixing HTML references...")

    # Build regex pattern to find any /assets/esports/HASH.ANYTHING reference
    # and replace with /assets/esports/HASH.CORRECT_EXT
    fixed_pages = 0
    total_replacements = 0

    for key, entry in page_map.items():
        if not entry.get("file") or entry.get("status") != 200:
            continue

        filepath = os.path.join(WEB_DIR, entry["file"])
        if not os.path.exists(filepath):
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()

            original_html = html
            replacements = 0

            # Find all /assets/esports/HASH references
            refs = re.findall(r'/assets/esports/([a-f0-9]{16})\.[^\s"\'<>]+', html)

            for ref_hash in set(refs):
                if ref_hash in esports_map:
                    correct_ext = esports_map[ref_hash]["ext"]
                    # Replace all incorrect references for this hash
                    html = re.sub(
                        rf'/assets/esports/{ref_hash}\.[^\s"\'<>]+',
                        f'/assets/esports/{ref_hash}{correct_ext}',
                        html
                    )
                    replacements += 1

            # Also check for any remaining raw esports URLs that weren't replaced
            remaining_esports = re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', html)
            for eu in remaining_esports:
                eu_decoded = eu.replace("&amp;", "&")
                h = esports_hash(eu_decoded)
                ext = get_correct_ext(eu_decoded)
                local_path = f"/assets/esports/{h}{ext}"
                html = html.replace(eu, local_path)
                replacements += 1
                # Also ensure this image is in our map
                if h not in esports_map:
                    esports_map[h] = {"url": eu_decoded, "ext": ext}

            if html != original_html:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html)
                fixed_pages += 1
                total_replacements += replacements

        except Exception as e:
            print(f"  Error processing {filepath}: {e}")

    print(f"  Fixed {fixed_pages} pages with {total_replacements} total replacements")

    # Step 4: Download any newly discovered esports images
    new_downloads = 0
    for h, info in esports_map.items():
        dest = os.path.join(ESPORTS_DIR, f"{h}{info['ext']}")
        if not os.path.exists(dest):
            try:
                time.sleep(REQUEST_DELAY)
                resp = session.get(info["url"], timeout=TIMEOUT, stream=True)
                if resp.status_code == 200:
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                    new_downloads += 1
            except Exception:
                pass

    if new_downloads:
        print(f"  Downloaded {new_downloads} additional images")

    # Save updated mapping
    with open(mapping_file, "w") as f:
        json.dump(esports_map, f, indent=1)

    # Verify
    print("\nVerification:")
    total_refs = set()
    for key, entry in page_map.items():
        if not entry.get("file") or entry.get("status") != 200:
            continue
        filepath = os.path.join(WEB_DIR, entry["file"])
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
        refs = re.findall(r'/assets/esports/([^\s"\'<>]+)', html)
        total_refs.update(refs)

    matched = sum(1 for r in total_refs if os.path.exists(os.path.join(ESPORTS_DIR, r)))
    print(f"  Total unique esports refs in HTML: {len(total_refs)}")
    print(f"  Matched to files on disk: {matched}")
    print(f"  Unmatched: {len(total_refs) - matched}")
    print(f"  Files in esports dir: {len(os.listdir(ESPORTS_DIR))}")


if __name__ == "__main__":
    main()
