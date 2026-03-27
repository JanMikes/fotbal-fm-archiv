#!/usr/bin/env python3
"""
Final correct esports fix.

The hashes in stored HTML come from URLs that had:
1. mfkfm.cz/ replaced with / (by process_html)
2. &amp; entities preserved (raw HTML text)
Then SHA256-hashed.

We need to: fetch original URLs, apply the same transform, hash them,
then download the original image and save with that hash.
"""

import hashlib
import json
import os
import re
import time
import socket

import requests

BASE_URL = "https://mfkfm.cz"
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
ESPORTS_DIR = os.path.join(WEB_DIR, "assets", "esports")
PAGE_MAP_FILE = os.path.join(WEB_DIR, "page_map.json")

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})


def compute_stored_hash(raw_esports_url):
    """Compute the hash that process_esports_url would produce.

    The scraper pipeline:
    1. process_html replaces mfkfm.cz/ with /
    2. process_esports_url finds the URL and hashes it
    """
    # Apply same transform as process_html
    modified = re.sub(r'https?://(?:www\.)?mfkfm\.cz/', '/', raw_esports_url)
    return hashlib.sha256(modified.encode()).hexdigest()[:16]


def get_correct_ext(esports_url):
    """Extract file extension from the file= parameter."""
    m = re.search(r'file=[^&\s"\']*\.(\w{2,4})(?:[&\s"\']|$)', esports_url)
    if m:
        return f".{m.group(1).lower()}"
    # Try from the modified URL (where mfkfm.cz was replaced)
    m = re.search(r'file=[^&\s"\']*\.(\w{2,4})(?:[&\s"\']|$)',
                  re.sub(r'https?://(?:www\.)?mfkfm\.cz/', '/', esports_url))
    if m:
        return f".{m.group(1).lower()}"
    return ".jpg"


def dns_ok():
    try:
        socket.getaddrinfo("mfkfm.cz", 443)
        return True
    except socket.gaierror:
        return False


def wait_for_dns():
    for i in range(20):
        if dns_ok():
            return True
        print(f"  DNS unavailable, waiting... ({i+1}/20)")
        time.sleep(10)
    return False


def main():
    os.makedirs(ESPORTS_DIR, exist_ok=True)

    with open(PAGE_MAP_FILE, "r") as f:
        page_map = json.load(f)

    # Step 1: Collect ALL esports URLs and compute correct stored hashes
    print("Step 1: Collecting esports URLs from original site...")

    target_keys = [k for k in page_map
                   if page_map[k].get("status") == 200
                   and k.split("?")[0] in ("hrac.asp", "soupiska.asp", "index.asp",
                                            "zapas.asp", "zapasy.asp", "clanek.asp",
                                            "mladez.asp", "tabulka.asp", "statistiky.asp",
                                            "media_show.asp", "fotogalerie.asp")]

    print(f"  Will check {len(target_keys)} pages")

    # stored_hash -> {download_url, ext}
    esports_map = {}
    checked = 0
    errors_consecutive = 0

    for key in target_keys:
        try:
            time.sleep(0.35)
            resp = session.get(f"{BASE_URL}/{key}", timeout=15)
            if resp.status_code == 200:
                raw_urls = re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', resp.text)
                for raw_url in raw_urls:
                    stored_h = compute_stored_hash(raw_url)
                    if stored_h not in esports_map:
                        ext = get_correct_ext(raw_url)
                        # For download, decode &amp; to &
                        download_url = raw_url.replace("&amp;", "&")
                        esports_map[stored_h] = {"download_url": download_url, "ext": ext}
                errors_consecutive = 0
            checked += 1
        except requests.exceptions.ConnectionError:
            errors_consecutive += 1
            if errors_consecutive > 5:
                print(f"  DNS issues at {checked}, waiting...")
                if not wait_for_dns():
                    print("  DNS still down, stopping collection")
                    break
                errors_consecutive = 0
        except Exception:
            checked += 1

        if checked % 200 == 0:
            print(f"  Checked {checked}/{len(target_keys)}, found {len(esports_map)} unique images")

    print(f"  Collection done: {len(esports_map)} unique images from {checked} pages")

    # Save map
    map_file = os.path.join(WEB_DIR, "esports_map_v3.json")
    with open(map_file, "w") as f:
        json.dump(esports_map, f, indent=1)

    # Step 2: Clean up and download images
    print(f"\nStep 2: Downloading {len(esports_map)} esports images...")

    # Clear old files
    for f in os.listdir(ESPORTS_DIR):
        os.remove(os.path.join(ESPORTS_DIR, f))

    downloaded = 0
    failed = 0

    for stored_h, info in sorted(esports_map.items()):
        dest = os.path.join(ESPORTS_DIR, f"{stored_h}{info['ext']}")
        try:
            time.sleep(0.25)
            resp = session.get(info["download_url"], timeout=30, stream=True)
            if resp.status_code == 200:
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                downloaded += 1
            else:
                failed += 1
        except requests.exceptions.ConnectionError:
            if not wait_for_dns():
                break
            failed += 1
        except Exception:
            failed += 1

        if (downloaded + failed) % 100 == 0:
            print(f"  {downloaded + failed}/{len(esports_map)} "
                  f"(ok={downloaded}, fail={failed})")

    print(f"  Downloaded {downloaded}, failed {failed}")

    # Step 3: Fix HTML references
    print(f"\nStep 3: Fixing HTML references...")

    fixed_pages = 0

    for key, entry in page_map.items():
        if not entry.get("file") or entry.get("status") != 200:
            continue
        filepath = os.path.join(WEB_DIR, entry["file"])
        if not os.path.exists(filepath):
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()

            original = html

            # Fix /assets/esports/HASH.WRONG_EXT → /assets/esports/HASH.CORRECT_EXT
            def fix_ref(match):
                h = match.group(1)
                if h in esports_map:
                    return f'/assets/esports/{h}{esports_map[h]["ext"]}'
                # Try to find file on disk
                for ext in [".png", ".jpg", ".jpeg", ".gif"]:
                    if os.path.exists(os.path.join(ESPORTS_DIR, f"{h}{ext}")):
                        return f'/assets/esports/{h}{ext}'
                return match.group(0)

            html = re.sub(r'/assets/esports/([a-f0-9]{16})[^\s"\'<>]*', fix_ref, html)

            if html != original:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html)
                fixed_pages += 1

        except Exception as e:
            print(f"  Error: {e}")

    print(f"  Fixed {fixed_pages} pages")

    # Step 4: Verify
    print(f"\nStep 4: Verification...")

    total_refs = set()
    for key, entry in page_map.items():
        if not entry.get("file") or entry.get("status") != 200:
            continue
        filepath = os.path.join(WEB_DIR, entry["file"])
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
        for ref in re.findall(r'/assets/esports/([^\s"\'<>]+)', html):
            total_refs.add(ref)

    matched = sum(1 for r in total_refs
                  if os.path.exists(os.path.join(ESPORTS_DIR, r)))
    unmatched = [r for r in sorted(total_refs) if not os.path.exists(os.path.join(ESPORTS_DIR, r))]
    print(f"  Unique esports refs in HTML: {len(total_refs)}")
    print(f"  Matched to files: {matched}")
    print(f"  Unmatched: {len(unmatched)}")
    if unmatched:
        print(f"  Sample unmatched: {unmatched[:5]}")
    print(f"  Files in esports dir: {len(os.listdir(ESPORTS_DIR))}")


if __name__ == "__main__":
    main()
