#!/usr/bin/env python3
"""
Final esports fix - handles the &amp; vs & hash mismatch.

The original scraper hashed URLs with &amp; (HTML-encoded), producing
hashes in the HTML like /assets/esports/945007816f9b6de4.XXX.
The esports_map.json has hashes from decoded URLs (with &).
We need to build a mapping from HTML-hashes to correct files.
"""

import hashlib
import json
import os
import re
import shutil

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
ESPORTS_DIR = os.path.join(WEB_DIR, "assets", "esports")
PAGE_MAP_FILE = os.path.join(WEB_DIR, "page_map.json")
ESPORTS_MAP_FILE = os.path.join(WEB_DIR, "esports_map.json")


def main():
    with open(PAGE_MAP_FILE, "r") as f:
        page_map = json.load(f)

    with open(ESPORTS_MAP_FILE, "r") as f:
        esports_map = json.load(f)

    print(f"Esports map has {len(esports_map)} entries (decoded hashes)")

    # Step 1: Build mapping from decoded-hash -> (raw-hash, correct_ext)
    # For each URL in esports_map, compute both hashes
    decoded_to_raw = {}  # decoded_hash -> (raw_hash, correct_ext, url)

    for decoded_hash, info in esports_map.items():
        url = info["url"]
        ext = info["ext"]

        # Compute raw (HTML) hash - with &amp;
        raw_url = url.replace("&", "&amp;")
        raw_hash = hashlib.sha256(raw_url.encode()).hexdigest()[:16]

        decoded_to_raw[decoded_hash] = {
            "raw_hash": raw_hash,
            "ext": ext,
            "url": url
        }

    # Build: raw_hash -> correct_ext
    raw_hash_to_ext = {}
    for dh, info in decoded_to_raw.items():
        raw_hash_to_ext[info["raw_hash"]] = info["ext"]

    print(f"Built {len(raw_hash_to_ext)} raw-hash -> ext mappings")

    # Step 2: Collect all unique hashes from HTML to understand what we need
    html_hashes = set()
    for key, entry in page_map.items():
        if not entry.get("file") or entry.get("status") != 200:
            continue
        filepath = os.path.join(WEB_DIR, entry["file"])
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
        for m in re.findall(r'/assets/esports/([a-f0-9]{16})', html):
            html_hashes.add(m)

    print(f"Found {len(html_hashes)} unique hashes in HTML")

    matched_raw = sum(1 for h in html_hashes if h in raw_hash_to_ext)
    matched_decoded = sum(1 for h in html_hashes if h in esports_map)
    print(f"  Matched as raw hashes: {matched_raw}")
    print(f"  Matched as decoded hashes: {matched_decoded}")
    print(f"  Unmatched: {len(html_hashes) - matched_raw - matched_decoded}")

    # Step 3: Rename/copy existing esports files to use raw hashes
    # Current files use decoded hashes; we need files with raw hashes
    print(f"\nStep 3: Setting up esports files with correct names...")

    # First, catalog existing files
    existing_files = {}  # hash_part -> full_filename
    for f in os.listdir(ESPORTS_DIR):
        hash_part = f.split(".")[0]
        existing_files[hash_part] = f

    # Create new files with raw-hash names
    created = 0
    for decoded_hash, info in decoded_to_raw.items():
        raw_hash = info["raw_hash"]
        ext = info["ext"]
        target_name = f"{raw_hash}{ext}"
        target_path = os.path.join(ESPORTS_DIR, target_name)

        # Source: file with decoded hash
        if decoded_hash in existing_files:
            source_path = os.path.join(ESPORTS_DIR, existing_files[decoded_hash])
            if not os.path.exists(target_path):
                shutil.copy2(source_path, target_path)
                created += 1

    print(f"  Created {created} files with raw-hash names")

    # Step 4: Fix HTML references
    print(f"\nStep 4: Fixing HTML references...")

    # Build combined hash -> correct_ext map (both raw and decoded hashes)
    all_hash_ext = {}
    all_hash_ext.update(raw_hash_to_ext)
    for dh, info in esports_map.items():
        all_hash_ext[dh] = info["ext"]

    fixed_pages = 0
    total_fixes = 0

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

            # Fix all /assets/esports/HASH.* references
            def fix_ref(match):
                h = match.group(1)
                full = match.group(0)
                if h in all_hash_ext:
                    return f'/assets/esports/{h}{all_hash_ext[h]}'
                # If hash not known, keep as-is but try to fix obvious broken extensions
                current_ext = full.split(h, 1)[1] if h in full else ""
                if current_ext and not re.match(r'\.(png|jpg|jpeg|gif|svg|webp)$', current_ext):
                    # Try to find a file on disk with this hash
                    for ext in [".png", ".jpg", ".jpeg", ".gif"]:
                        if os.path.exists(os.path.join(ESPORTS_DIR, f"{h}{ext}")):
                            return f'/assets/esports/{h}{ext}'
                return full

            html = re.sub(r'/assets/esports/([a-f0-9]{16})[^\s"\'<>]*', fix_ref, html)

            if html != original:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html)
                fixed_pages += 1
                total_fixes += 1

        except Exception as e:
            print(f"  Error: {e}")

    print(f"  Fixed {fixed_pages} pages")

    # Step 5: Verify
    print(f"\nStep 5: Verification...")

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
    unmatched = [r for r in total_refs if not os.path.exists(os.path.join(ESPORTS_DIR, r))]
    print(f"  Unique esports refs in HTML: {len(total_refs)}")
    print(f"  Matched to files: {matched}")
    print(f"  Unmatched: {len(unmatched)}")
    if unmatched:
        print(f"  Sample unmatched: {unmatched[:10]}")
    print(f"  Files in esports dir: {len(os.listdir(ESPORTS_DIR))}")
    total_size = sum(os.path.getsize(os.path.join(ESPORTS_DIR, f))
                     for f in os.listdir(ESPORTS_DIR))
    print(f"  Esports dir size: {total_size / (1024*1024):.1f} MB")


if __name__ == "__main__":
    main()
