"""Save your free eBay developer keys on this Mac (never in the repo) and test them with one search.

    .venv/bin/python library/ebay_keys.py
"""
import getpass
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hunt

cid = input("Paste the App ID (Client ID), then press return: ").strip()
sec = getpass.getpass("Paste the Cert ID (Client Secret) - it won't show - then press return: ").strip()
os.makedirs(os.path.dirname(hunt.KEYS), exist_ok=True)
json.dump({"client_id": cid, "client_secret": sec}, open(hunt.KEYS, "w"))
os.chmod(hunt.KEYS, 0o600)
try:
    got = hunt.ebay_api("Duracell PowerCheck AA", 1998, listings=2)
    print(f"eBay keys work: {len(got)} photos from the first 2 listings")
except Exception as e:
    print(f"STOP: eBay said no ({e}). Tell Claude exactly this line.")
