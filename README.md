# Bazaario

Bazaario is a farmer-to-customer marketplace for agricultural products from Azerbaijan. It covers eight categories only: Fruit, Vegetables, Grains, Dairy, Honey & bee products, Herbs, Nuts and Tea.

The repo splits into five parts:

- `backend/` holds the Flask REST API, SQLAlchemy models, JWT claims and role gates.
- `frontend/` holds the React (Vite) app for customers, farmers and admins.
- `scripts/check_images.py` verifies every seeded image URL before seeding runs.
- `seed.py` resets and seeds the database in one command.
- `tests/` covers API behavior, messaging, reviews and access control.

## Quickstart

One command drives everything from the repo root:

```bash
./bazaario dev
```

That starts the API on `127.0.0.1:5050` and the frontend on `127.0.0.1:5173`; Ctrl-C stops both. From a fresh clone, run `./bazaario setup && ./bazaario seed` first. Other subcommands: `api`, `web`, `seed`, `test`, `build`, `images`, `status`.

### 1. Python API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
flask run
```

`flask run` serves the API at `http://localhost:5000`. The default `.env.example` uses a local SQLite file so the first boot needs nothing else. The same `DATABASE_URL` setting accepts PostgreSQL; see the next section.

### 2. React frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite app runs at `http://localhost:5173` and calls `http://localhost:5000/api` by default. To use a different API port without adding another env file:

```bash
VITE_API_URL=http://127.0.0.1:5050/api npm run dev -- --host 127.0.0.1 --port 5173
```

### PostgreSQL

For a local PostgreSQL service, choose a strong local password first and export it (or put it in `.env`):

```bash
export POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
docker compose up -d postgres
# edit .env and set the matching URL:
# DATABASE_URL=postgresql+psycopg://bazaario:<your-password>@127.0.0.1:5432/bazaario
python seed.py
flask run
```

Compose binds the database to loopback and refuses to start without an explicit password. `Flask-SQLAlchemy` talks to PostgreSQL in this mode through `psycopg`. SQLite stays the zero-setup development fallback.

## Demo accounts

`python seed.py` prints these credentials after the image gate and database seed complete:

| Role | Email | Password | Access |
| --- | --- | --- | --- |
| Admin | `admin@bazaario.az` | `AdminDemo!2026` | verification, categories, regions, users |
| Farmer | `farmer@bazaario.az` | `FarmerDemo!2026` | approved farm listings, contact number, buyer messages |
| Customer | `customer@bazaario.az` | `CustomerDemo!2026` | catalog, seller messaging, product reviews |

Only `seed.py` creates admin accounts; there is no public admin registration route.

## Roles and security boundaries

Every JWT carries `role` and `account_status` claims. Protected route groups pass a role decorator before any endpoint logic. A valid token with the wrong role gets a JSON `403` with `error: "forbidden"`.

- Customer: `/api/customer/*`
- Farmer: `/api/farmer/*`
- Admin: `/api/admin/*`
- Public: `/api/auth/register/customer`, `/api/auth/register/farmer`, `/api/auth/login`, `/api/products`, `/api/meta`

Farmer signup creates a `FarmerProfile` with `pending_verification`. Listing create, update and archive return `403` with `code: "farmer_verification_required"` until an admin approves the profile. Suspending a farmer suspends the account too, and suspended or unapproved farms disappear from the public catalog and cannot be bought from. The API checks every farmer-submitted image URL live for an HTTP 200 `image/*` response from an approved host.

## Reviews

Buying on Bazaario is agreement based: there are no baskets, checkout or order records. Customers contact the farm and settle the deal directly. Each signed-in customer can leave one review per product with `POST /api/products/:id/reviews`; posting again updates their existing review. Ratings run from 1 to 5, the product payload carries the average and count, and farmers and admins cannot post reviews.

## Direct seller contact

There are no delivery hubs. Buyers deal with the farm directly, so every product page has two ways to reach the seller.

**Message the seller.** One thread per product per customer. Customers start it on the product page with `POST /api/products/:id/messages`; farmers reply into the same thread by passing `customer_id`. Each dashboard has an inbox (`GET /api/customer/messages`, `GET /api/farmer/messages`), and `GET /api/products/:id/messages` returns the full transcript. Customers read only their own threads, farmers only threads on their own products, admins get refused, and empty bodies return 422.

**Call the seller.** Farmer profiles carry an optional `phone`. Farmers set it from their dashboard (`PUT /api/farmer/phone`) or at signup. The number accepts digits, `+`, spaces, parentheses and hyphens; blank clears it. Every product payload includes it as `farm.phone`, and the frontend renders it as a `tel:` link. Seeded farms ship with plausible +994 numbers.

## Agricultural catalog and image gate

The API rejects any category outside the agricultural allow-list. A non-agricultural category such as `Electronics` gets `422` with `code: "invalid_category"`. Admin category management can activate or deactivate only the same eight categories; arbitrary ones cannot be created. Farmer listing images must come from Unsplash, Pexels or Wikimedia Commons hosts, and the seed gate additionally verifies the live response content type.

The seed covers 10 farms across Goychay, Lankaran, Qabala, Sheki, Astara, Zagatala and Shamkir, plus 41 listings with realistic AZN prices and season windows. Seeded photos use direct Wikimedia Commons URLs, no placeholders.

Run the verification independently at any time:

```bash
.venv/bin/python scripts/check_images.py
# PASS: 41 seeded image URLs returned HTTP 200 with image/* content-type
```

`seed.py` calls the same verifier first and refuses to touch the database if any seeded image fails. The verifier follows redirects, checks the final HTTP status and `image/*` content type, and retries transient Wikimedia `429` responses.

## API verification

Run the automated suite:

```bash
.venv/bin/python -m pytest tests/ -q
```

The tests cover JWT role identity, wrong-role `403` responses, open customer signup, the missing admin registration route, pending farmer publish blocking, category `422`, catalog filters, per-product reviews, message threads and phone validation.

A manual smoke flow after starting `flask run`:

1. Log in as each demo account; each lands on its role-specific `/dashboard` view.
2. As customer, open a product, message the farm and leave a review.
3. Call or message details appear straight on the product page; there is no checkout step.
4. Use the admin verification queue to approve or suspend a new farmer application.

## Frontend surfaces

Customers search and filter the catalog by category, region and season, open product pages that show the source farm, price and season window, message the farm, call it, and leave one review per product.

Farmers see a verification banner before approval, manage listings through a form that enforces the category allow-list, set stock and season windows, publish their contact number, and answer buyer messages from an inbox.

Admins work a pending-farmer queue, approve or suspend farms, suspend or restore users, and manage categories and regions.

The UI keeps to a cream ground (`#FBFAF7`), near-black ink, thin rules, flat orange (`#FF6B00`) and green (`#00A651`) accents, and Space Grotesk/Helvetica type. No gradients, no glass effects.

## Repository commands

```bash
# API tests
.venv/bin/python -m pytest tests/ -q

# Seed (image verification runs first)
.venv/bin/python seed.py

# Frontend production build
cd frontend && npm run build
```
