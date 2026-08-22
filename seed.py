#!/usr/bin/env python3
"""Reset and seed Bazaario's development database."""

from backend.bazaario import create_app
from backend.bazaario.seed_data import DEMO_PASSWORDS, seed_database
from scripts.check_images import verify_urls


app = create_app()


if __name__ == "__main__":
    checked, failures = verify_urls()
    if failures:
        raise SystemExit(
            f"Refusing to seed: {len(failures)} of {checked} image URLs failed verification."
        )
    with app.app_context():
        counts = seed_database()
    print(f"Seeded {counts['shops']} shops, {counts['products']} products, and {counts['categories']} categories.")
    print("Demo credentials:")
    print("  admin@bazaario.az / " + DEMO_PASSWORDS["admin@bazaario.az"])
    print("  shop@bazaario.az / " + DEMO_PASSWORDS["shop@bazaario.az"])
    print("  customer@bazaario.az / " + DEMO_PASSWORDS["customer@bazaario.az"])
