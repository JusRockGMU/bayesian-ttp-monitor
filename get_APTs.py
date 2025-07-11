#!/usr/bin/env python3

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote

# -------------------------
# CONFIGURATION
# -------------------------

BASE_URL = "https://center-for-threat-informed-defense.github.io/attack-flow/example_flows/"
OUTPUT_FOLDER = "inputs"

# -------------------------
# CREATE OUTPUT FOLDER
# -------------------------

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------------
# FETCH HTML PAGE
# -------------------------

try:
    print(f"[INFO] Fetching APT list from: {BASE_URL}")
    resp = requests.get(BASE_URL)
    resp.raise_for_status()
except requests.RequestException as e:
    print(f"[ERROR] Failed to download page: {e}")
    exit(1)

# -------------------------
# PARSE JSON LINKS
# -------------------------

soup = BeautifulSoup(resp.text, "html.parser")
links = soup.find_all("a", href=True)

json_links = [
    link["href"]
    for link in links
    if link["href"].endswith(".json")
]

if not json_links:
    print("[WARN] No JSON links found!")
    exit(0)

print(f"[INFO] Found {len(json_links)} JSON files.")

# -------------------------
# DOWNLOAD EACH JSON FILE
# -------------------------

for link in json_links:
    # Construct filename
    filename = unquote(os.path.basename(link))
    apt_name = filename.replace(".json", "").replace(" ", "")
    local_file = os.path.join(OUTPUT_FOLDER, f"{apt_name}.json")

    # Skip if already downloaded
    if os.path.exists(local_file):
        print(f"[SKIP] Already exists: {apt_name}.json")
        continue

    # Download the JSON
    try:
        url = urljoin(BASE_URL, link)
        print(f"[DOWNLOAD] {apt_name}.json → {local_file}")
        r = requests.get(url)
        r.raise_for_status()
        with open(local_file, "wb") as f:
            f.write(r.content)
        print(f"[SUCCESS] Saved {local_file}")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to download {apt_name}.json: {e}")
