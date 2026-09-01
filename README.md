# Bazaario

Bazaario is a shop-to-customer marketplace for agricultural products from Azerbaijan. It covers eight categories only: Fruit, Vegetables, Grains, Dairy, Honey & bee products, Herbs, Nuts and Tea.

Live deployment: [bazaario-sepia.vercel.app](https://bazaario-sepia.vercel.app)

The repo splits into five parts:

- `backend/` holds the Flask REST API, SQLAlchemy models, JWT claims and role gates.
- `frontend/` holds the React (Vite) app for customers, shops and admins.
- `scripts/check_images.py` verifies every seeded image URL before seeding runs.
- `seed.py` resets and seeds the database in one command.
- `tests/` covers API behavior, messaging, reviews and access control.

## Quickstart

One command drives everything from the repo root:

**macOS / Linux:**
```bash
./bazaario dev
```

**Windows (PowerShell):**
```powershell
.\bazaario.ps1 dev
```

That starts the API on `127.0.0.1:8000` and the frontend on `127.0.0.1:5173`. Ctrl-C stops both. From a fresh clone, run `./bazaario setup && ./bazaario seed` first (or `.\bazaario.ps1 setup; .\bazaario.ps1 seed` on Windows). Other subcommands: `api`, `web`, `seed`, `test`, `build`, `images`, `status`.

### 1. Python API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
python app.py
```

`python app.py` serves the API at `http://127.0.0.1:8000`. The default `.env.example` uses a local SQLite file so the first boot needs nothing else. The same `DATABASE_URL` setting accepts PostgreSQL and Supabase URLs.

### 2. React frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite app runs at `http://127.0.0.1:5173` and proxies `/api` to `http://127.0.0.1:8000`.

### PostgreSQL and Supabase

For a local PostgreSQL service, choose a password and export it:

```bash
export POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
docker compose up -d postgres
# edit .env and set the matching URL:
# DATABASE_URL=postgresql+psycopg://bazaario:<your-password>@127.0.0.1:5432/bazaario
python seed.py
python app.py
```

For Supabase, copy the connection string from your Supabase project settings (Transaction Pooler, port 6543) and run the seed once:

```bash
DATABASE_URL="postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres" python seed.py
```

## Deployment to Vercel

The repository includes `vercel.json` and `api/index.py` for deployment on Vercel.

1. Import the repository into Vercel.
2. Add environment variables in Vercel project settings:
   * `DATABASE_URL`: Your Supabase transaction pooler URL.
   * `JWT_SECRET_KEY`: A random hex string for signing tokens.
   * `CORS_ORIGINS`: Your production domain URL.
3. Deploy. Vercel builds the static React frontend from `frontend/` and routes `/api/*` requests to the Flask serverless function.

## Demo accounts

`python seed.py` prints these credentials after the image gate and database seed complete:

| Role | Email | Password | Access |
| --- | --- | --- | --- |
| Admin | `admin@bazaario.az` | `AdminDemo!2026` | verification, categories, regions, users |
| Shop | `shop@bazaario.az` | `ShopDemo!2026` | approved shop listings, contact number, buyer messages |
| Customer | `customer@bazaario.az` | `CustomerDemo!2026` | catalog, seller messaging, product reviews |

Only `seed.py` creates admin accounts; there is no public admin registration route.

## Roles and security boundaries

Every JWT carries `role` and `account_status` claims. Protected route groups pass a role decorator before any endpoint logic. A valid token with the wrong role gets a JSON `403` with `error: "forbidden"`.

- Customer: `/api/customer/*`
- Shop: `/api/shop/*`
- Admin: `/api/admin/*`
- Public: `/api/auth/register/customer`, `/api/auth/register/shop`, `/api/auth/login`, `/api/products`, `/api/meta`

Shop signup creates a `ShopProfile` with `pending_verification`. Listing create, update and archive return `403` with `code: "shop_verification_required"` until an admin approves the profile. Suspending a shop suspends the account too, and suspended or unapproved shops disappear from the public catalog. The API checks every shop-submitted image URL live for an HTTP 200 `image/*` response from an approved host.

## Reviews

Buying on Bazaario is agreement based: there are no baskets, checkout or order records. Customers contact the shop and settle the deal directly. Each signed-in customer can leave one review per product with `POST /api/products/:id/reviews`; posting again updates their existing review. Ratings run from 1 to 5, the product payload carries the average and count, and shop accounts and admins cannot post reviews.

## Direct seller contact

There are no delivery hubs. Buyers deal with the shop directly, so every product page has two ways to reach the seller.

**Message the seller.** One thread per product per customer. Customers start it on the product page with `POST /api/products/:id/messages`; shops reply into the same thread by passing `customer_id`. Each dashboard has an inbox (`GET /api/customer/messages`, `GET /api/shop/messages`), and `GET /api/products/:id/messages` returns the full transcript. Customers read only their own threads, shops only threads on their own products, admins get refused, and empty bodies return 422.

**Call the seller.** Shop profiles carry an optional `phone`. Shops set it from their dashboard (`PUT /api/shop/phone`) or at signup. The number accepts digits, `+`, spaces, parentheses and hyphens; blank clears it. Every product payload includes it as `shop.phone`, and the frontend renders it as a `tel:` link. Seeded shops ship with plausible +994 numbers.

## Agricultural catalog and image gate

The API rejects any category outside the agricultural allow-list. A non-agricultural category such as `Electronics` gets `422` with `code: "invalid_category"`. Admin category management can activate or deactivate only the same eight categories; arbitrary ones cannot be created. Shop listing images must come from Unsplash, Pexels or Wikimedia Commons hosts, and the seed gate additionally verifies the live response content type.

The seed covers 10 shops across Goychay, Lankaran, Qabala, Sheki, Astara, Zagatala and Shamkir, plus 41 listings with realistic AZN prices and season windows. Seeded photos use direct Wikimedia Commons URLs, no placeholders.

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

The tests cover JWT role identity, wrong-role `403` responses, open customer signup, the missing admin registration route, pending shop publish blocking, category `422`, catalog filters, per-product reviews, message threads and phone validation.

A manual smoke flow after starting `flask run`:

1. Log in as each demo account; each lands on its role-specific `/dashboard` view.
2. As customer, open a product, message the shop and leave a review.
3. Call or message details appear straight on the product page; there is no checkout step.
4. Use the admin verification queue to approve or suspend a new shop application.

## Frontend surfaces

Customers search and filter the catalog by category, region and season, open product pages that show the source shop, price and season window, message the shop, call it, and leave one review per product.

Shops see a verification banner before approval, manage listings through a form that enforces the category allow-list, set stock and season windows, publish their contact number, and answer buyer messages from an inbox.

Admins work a pending-shop queue, approve or suspend shops, suspend or restore users, and manage categories and regions.

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
