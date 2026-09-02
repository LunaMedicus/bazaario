#!/usr/bin/env python3
"""Verify every image URL used by the seed dataset.

Usage: python scripts/check_images.py
"""

from pathlib import Path
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.bazaario.seed_data import SEED_PRODUCTS  # noqa: E402


HEADERS = {"User-Agent": "Bazaario image verifier/1.0 (contact: dev@bazaario.az)"}


def verify_urls(products=SEED_PRODUCTS, timeout=30):
    failures = []
    checked = 0
    session = requests.Session()
    for product in products:
        url = product["image_url"]
        checked += 1
        response = None
        last_error = None
        for attempt in range(3):
            try:
                response = session.get(
                    url,
                    headers=HEADERS,
                    stream=True,
                    timeout=(10, timeout),
                    allow_redirects=True,
                )
                if response.status_code != 429 or attempt == 2:
                    break
                response.close()
                time.sleep(2**attempt)
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        if response is None:
            failures.append({"name": product["name"], "url": url, "error": str(last_error)})
        else:
            content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if response.status_code != 200 or not content_type.startswith("image/"):
                failures.append(
                    {
                        "name": product["name"],
                        "url": url,
                        "status": response.status_code,
                        "content_type": content_type,
                    }
                )
            response.close()
        time.sleep(0.35)
    return checked, failures


def main():
    checked, failures = verify_urls()
    if failures:
        print(f"FAILED: {len(failures)} of {checked} seeded image URLs are invalid")
        for failure in failures:
            print(failure)
        return 1
    print(f"PASS: {checked} seeded image URLs returned HTTP 200 with image/* content-type")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
