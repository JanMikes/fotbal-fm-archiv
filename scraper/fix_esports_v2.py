#!/usr/bin/env python3
"""
Fix esports image references v2 - works in batches with DNS resilience.

Strategy:
1. Uses already collected esports_map.json if available
2. Fetches remaining pages in small batches with DNS recovery
3. Fixes HTML refs and downloads images
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
ESPORTS_MAP_FILE = os.path.join(WEB_DIR, "esports_map.json")

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})


def esports_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def get_correct_ext(url):
    m = re.search(r'file=([^&\s"\']+)', url)
    if m:
        ext_m = re.search(r'\.(\w{2,4})$', m.group(1))
        if ext_m:
            return f".{ext_m.group(1).lower()}"
    return ".jpg"


def dns_ok():
    try:
        socket.getaddrinfo("mfkfm.cz", 443)
        return True
    except socket.gaierror:
        return False


def wait_for_dns():
    """Wait for DNS to become available again."""
    for i in range(30):
        if dns_ok():
            return True
        print(f"  DNS unavailable, waiting... ({i+1}/30)")
        time.sleep(10)
    return False


def main():
    os.makedirs(ESPORTS_DIR, exist_ok=True)

    with open(PAGE_MAP_FILE, "r") as f:
        page_map = json.load(f)

    # Load existing esports map
    esports_map = {}
    if os.path.exists(ESPORTS_MAP_FILE):
        with open(ESPORTS_MAP_FILE, "r") as f:
            esports_map = json.load(f)
        print(f"Loaded existing esports map: {len(esports_map)} entries")

    # Step 1: Collect esports URLs from pages we haven't checked yet
    # Track which pages we've already checked
    checked_file = os.path.join(WEB_DIR, "esports_checked.json")
    checked_keys = set()
    if os.path.exists(checked_file):
        with open(checked_file, "r") as f:
            checked_keys = set(json.load(f))

    target_keys = []
    for key in page_map:
        if page_map[key].get("status") != 200:
            continue
        if key in checked_keys:
            continue
        base = key.split("?")[0]
        if base in ("hrac.asp", "soupiska.asp", "index.asp", "zapas.asp",
                     "zapasy.asp", "clanek.asp", "mladez.asp", "tabulka.asp",
                     "statistiky.asp", "media_show.asp", "fotogalerie.asp"):
            target_keys.append(key)

    print(f"Step 1: {len(target_keys)} pages remaining to check for esports URLs")

    batch_size = 200
    total_checked = 0
    dns_failures = 0

    for i in range(0, len(target_keys), batch_size):
        batch = target_keys[i:i + batch_size]

        if not dns_ok():
            print(f"  DNS down at batch {i}, waiting...")
            if not wait_for_dns():
                print("  DNS still down, stopping collection")
                break

        for key in batch:
            try:
                time.sleep(0.4)
                resp = session.get(f"{BASE_URL}/{key}", timeout=15)
                if resp.status_code == 200:
                    urls = re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', resp.text)
                    for u in urls:
                        u = u.replace("&amp;", "&")
                        h = esports_hash(u)
                        if h not in esports_map:
                            esports_map[h] = {"url": u, "ext": get_correct_ext(u)}
                checked_keys.add(key)
                total_checked += 1
            except requests.exceptions.ConnectionError:
                dns_failures += 1
                if dns_failures > 5:
                    print(f"  Too many DNS failures, pausing batch...")
                    if not wait_for_dns():
                        break
                    dns_failures = 0
            except Exception:
                checked_keys.add(key)
                total_checked += 1

        # Save progress after each batch
        with open(ESPORTS_MAP_FILE, "w") as f:
            json.dump(esports_map, f, indent=1)
        with open(checked_file, "w") as f:
            json.dump(list(checked_keys), f)

        print(f"  Batch {i//batch_size + 1}: checked {total_checked} total, "
              f"{len(esports_map)} unique esports images")

    print(f"  Collection done: {len(esports_map)} unique esports images from {total_checked} new pages")

    # Step 2: Download images
    print(f"\nStep 2: Downloading {len(esports_map)} esports images...")

    # Clean up old files
    for f in os.listdir(ESPORTS_DIR):
        os.remove(os.path.join(ESPORTS_DIR, f))

    downloaded = 0
    failed = 0

    for h, info in sorted(esports_map.items()):
        dest = os.path.join(ESPORTS_DIR, f"{h}{info['ext']}")
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        try:
            time.sleep(0.3)
            resp = session.get(info["url"], timeout=30, stream=True)
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
    print(f"\nStep 3: Fixing HTML references in all pages...")

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

            # Fix /assets/esports/HASH.WRONG_EXT references
            def fix_ref(match):
                ref_hash = match.group(1)
                if ref_hash in esports_map:
                    return f'/assets/esports/{ref_hash}{esports_map[ref_hash]["ext"]}'
                return match.group(0)

            html = re.sub(r'/assets/esports/([a-f0-9]{16})[^\s"\'<>]*', fix_ref, html)

            # Also fix any remaining raw esports URLs
            esports_urls = re.findall(r'https?://php\.esports\.cz/images/[^\s"\'<>]+', html)
            for eu in esports_urls:
                eu_clean = eu.replace("&amp;", "&")
                h = esports_hash(eu_clean)
                ext = get_correct_ext(eu_clean)
                html = html.replace(eu, f"/assets/esports/{h}{ext}")

            if html != original:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html)
                fixed_pages += 1

        except Exception as e:
            print(f"  Error: {filepath}: {e}")

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
    print(f"  Unique esports refs in HTML: {len(total_refs)}")
    print(f"  Matched to files: {matched}")
    print(f"  Unmatched: {len(total_refs) - matched}")
    if total_refs - {r for r in total_refs if os.path.exists(os.path.join(ESPORTS_DIR, r))}:
        unmatched = [r for r in total_refs if not os.path.exists(os.path.join(ESPORTS_DIR, r))]
        print(f"  Sample unmatched: {unmatched[:5]}")


if __name__ == "__main__":
    main()
