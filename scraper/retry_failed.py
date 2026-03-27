#!/usr/bin/env python3
"""
Retry downloading pages that returned non-200 status codes.
"""

import hashlib
import json
import os
import re
import sys
import time

import requests

BASE_URL = "https://mfkfm.cz"
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
PAGES_DIR = os.path.join(WEB_DIR, "pages")
PAGE_MAP_FILE = os.path.join(WEB_DIR, "page_map.json")

REQUEST_DELAY = 0.5
TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def url_hash(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def process_html(html):
    """Post-process HTML: rewrite absolute URLs, strip tracking."""
    html = re.sub(r'https?://(?:www\.)?mfkfm\.cz/', '/', html)
    html = re.sub(r'<script[^>]*google[_-]?analytics[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<script[^>]*gtag[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<script[^>]*>\s*\(function\s*\(\s*i\s*,\s*s\s*,\s*o\s*,\s*g\s*,\s*r\s*,\s*a\s*,\s*m\s*\).*?</script>", '', html, flags=re.DOTALL)
    html = re.sub(r'<script[^>]*toplist[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<a[^>]*toplist[^>]*>.*?</a>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<img[^>]*toplist[^>]*/?>',  '', html, flags=re.IGNORECASE)

    # Replace esports proxy URLs with local paths
    esports_urls = re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', html)
    for eu in esports_urls:
        h = hashlib.sha256(eu.encode()).hexdigest()[:16]
        ext = ".jpg"
        file_match = re.search(r'file=[^&]*\.(\w{2,4})(?:[&\s"\']|$)', eu)
        if file_match:
            ext = f".{file_match.group(1).lower()}"
        html = html.replace(eu, f"/assets/esports/{h}{ext}")

    return html


def main():
    with open(PAGE_MAP_FILE, "r") as f:
        page_map = json.load(f)

    # Find all entries to retry
    to_retry = []
    for key, entry in page_map.items():
        status = entry.get("status", 0)
        if status != 200 and status != 404:
            to_retry.append(key)

    print(f"Found {len(to_retry)} pages to retry")

    if not to_retry:
        print("Nothing to retry!")
        return

    stats = {"ok": 0, "still_bad": 0, "error": 0, "skipped": 0}

    for i, key in enumerate(to_retry):
        url = f"{BASE_URL}/{key}"
        try:
            time.sleep(REQUEST_DELAY)
            resp = session.get(url, timeout=TIMEOUT)

            if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", ""):
                html = process_html(resp.text)

                # Check if it's actually content (not just a tiny error page)
                if len(html) > 500:
                    h = url_hash(key)
                    filename = f"pages/{h}.html"
                    filepath = os.path.join(WEB_DIR, filename)

                    # Remove old file if exists
                    old_entry = page_map[key]
                    if old_entry.get("file"):
                        old_path = os.path.join(WEB_DIR, old_entry["file"])
                        if os.path.exists(old_path) and old_path != filepath:
                            os.remove(old_path)

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(html)

                    page_map[key] = {"file": filename, "status": 200}
                    stats["ok"] += 1
                else:
                    stats["still_bad"] += 1
            elif resp.status_code == 404:
                page_map[key] = {"file": None, "status": 404}
                # Remove old file
                old_entry = page_map.get(key, {})
                if old_entry.get("file"):
                    old_path = os.path.join(WEB_DIR, old_entry["file"])
                    if os.path.exists(old_path):
                        os.remove(old_path)
                stats["skipped"] += 1
            else:
                stats["still_bad"] += 1

        except requests.RequestException as e:
            stats["error"] += 1
            if stats["error"] % 10 == 1:
                print(f"  Error at {i}: {e}")

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(to_retry)}] ok={stats['ok']} bad={stats['still_bad']} "
                  f"404={stats['skipped']} err={stats['error']}")

            # Save periodically
            if (i + 1) % 500 == 0:
                with open(PAGE_MAP_FILE, "w", encoding="utf-8") as f:
                    json.dump(page_map, f, ensure_ascii=False, indent=1)

    # Final save
    with open(PAGE_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(page_map, f, ensure_ascii=False, indent=1)

    print(f"\nDone! ok={stats['ok']} bad={stats['still_bad']} 404={stats['skipped']} err={stats['error']}")

    # Summary
    ok_count = sum(1 for v in page_map.values() if v.get("status") == 200 and v.get("file"))
    print(f"Total OK pages in map: {ok_count}")


if __name__ == "__main__":
    main()
