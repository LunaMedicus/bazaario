# Bazaario

Bazaario is a farmer-to-customer marketplace for agricultural products from Azerbaijan. It is intentionally limited to eight catalog categories: **Fruit, Vegetables, Grains, Dairy, Honey & bee products, Herbs, Nuts, and Tea**.

The repository is a production-shaped vertical slice:

- `backend/` — Flask REST API, SQLAlchemy models, JWT claims, role gates, order invariants
- `frontend/` — React + Vite customer, farmer, and admin surfaces
- `scripts/check_images.py` — verifies every seeded image URL before seeding
- `seed.py` — one reset-and-seed command
- `tests/` — API behavior and lifecycle tests

## Quickstart

### 1. Python API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
flask run
```

`flask run` serves the API at `http://localhost:5000`. The default `.env.example` uses a local SQLite file so the first boot is self-contained. The app also supports PostgreSQL through the same `DATABASE_URL` setting; see the PostgreSQL section below.

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

For a local PostgreSQL service:

```bash
docker compose up -d postgres
# edit .env and set:
# DATABASE_URL=postgresql+psycopg://bazaario:bazaario@localhost:5432/bazaario
python seed.py
flask run
```

`Flask-SQLAlchemy` uses PostgreSQL in this mode through `psycopg`. SQLite is only the zero-setup development fallback; the application does not use an alternate persistence layer.

## Demo accounts

`python seed.py` prints these credentials after the image gate and database seed complete:

| Role | Email | Password | Access |
| --- | --- | --- | --- |
| Admin | `admin@bazaario.az` | `AdminDemo!2026` | verification, categories, regions, users, orders, disputes |
| Farmer | `farmer@bazaario.az` | `FarmerDemo!2026` | approved farm listings, incoming orders, earnings |
| Customer | `customer@bazaario.az` | `CustomerDemo!2026` | catalog, basket, checkout, tracking, reviews |

Admin accounts are created only in `seed.py`; there is no public admin registration route.

## Roles and security boundaries

Every JWT contains `role` and `account_status` claims. Protected route groups use a role decorator before endpoint business logic. A valid token with the wrong role receives a JSON `403` with `error: "forbidden"`.

- Customer: `/api/customer/*`
- Farmer: `/api/farmer/*`
- Admin: `/api/admin/*`
- Public: `/api/auth/register/customer`, `/api/auth/register/farmer`, `/api/auth/login`, `/api/products`, `/api/meta`

Farmer signup creates a `FarmerProfile` with `pending_verification`. Listing create/update/archive checks the profile status and returns `403` with `code: "farmer_verification_required"` until an admin approves it. Suspending a farmer also suspends the account.

## Order lifecycle invariant

The only valid state sequence is:

```text
placed → confirmed → harvested → in_transit → delivered
```

| Transition | Owner | API |
| --- | --- | --- |
| create `placed` | customer | `POST /api/customer/orders` |
| `placed → confirmed` | farmer owning the order's listing | `POST /api/farmer/orders/:id/confirm` |
| `confirmed → harvested` | farmer owning the order's listing | `POST /api/farmer/orders/:id/harvested` |
| `harvested → in_transit` | admin / courier surface | `POST /api/admin/orders/:id/in-transit` |
| `in_transit → delivered` | customer who placed the order | `POST /api/customer/orders/:id/delivered` |

A transition with a skip, repeat, or backwards move returns `409` with `code: "invalid_transition"`. Every transition writes one `order_audits` row with actor, role, previous state, next state, and a UTC timestamp. The initial placement is also an audit row, so a completed order has exactly five audit rows.

Checkout supports cash-on-delivery and a deterministic `card_sandbox` authorization stub. Stock is checked and reserved when the order is placed. Reviews are rejected until the customer marks the order delivered and can only reference products from that order.

## Agricultural catalog and image gate

Product categories are enforced by the API against the fixed agricultural allow-list. A non-agricultural category (for example, `Electronics`) returns `422` with `code: "invalid_category"`. Admin category management can activate/deactivate only the same eight allowed categories; arbitrary categories cannot be created. Farmer listing images are constrained to hotlinkable Unsplash, Pexels, or Wikimedia Commons hosts, while the seed gate additionally verifies the live response content type.

The seed has 10 farms across Goychay, Lankaran, Qabala, Sheki, Astara, Zagatala, and Shamkir, plus 41 agricultural listings with realistic AZN prices and season windows. Seed photos are direct Wikimedia Commons image URLs. No placeholders or generated artwork are used.

Run the verification independently at any time:

```bash
.venv/bin/python scripts/check_images.py
# PASS: 41 seeded image URLs returned HTTP 200 with image/* content-type
```

`seed.py` calls the same verifier first and refuses to drop or modify the database if any seeded image fails. The verifier follows redirects, checks the final HTTP status and `image/*` content type, and retries transient Wikimedia `429` responses.

## API verification

Run the automated suite:

```bash
.venv/bin/python -m pytest tests/ -q
```

The tests cover JWT role identity, wrong-role `403` responses, open customer signup, admin registration absence, pending farmer publish blocking, category `422`, catalog filters, order transition sequencing, and the exact five-row audit invariant.

A manual smoke flow after starting `flask run`:

1. Log in as each demo account; each lands on its role-specific `/dashboard` view.
2. As customer, add a product to the basket and choose cash or sandbox card checkout.
3. As the owning farmer, accept the order and mark it harvested.
4. As admin, mark it in transit.
5. As customer, confirm delivered; the review action then unlocks.
6. Use the admin verification queue to approve or suspend a new farmer application.

## Frontend surfaces

- **Customer:** searchable gallery, category/region/season filters, product detail with farm source, local basket, checkout, five-state tracking timeline, delivery-gated review and dispute flag.
- **Farmer:** verification banner, listing CRUD form with agricultural category enforcement, stock and season fields, incoming order accept/harvest actions, delivered earnings summary.
- **Admin:** pending verification queue, approval/suspension, user suspend/restore, order oversight and transit action, dispute resolution surface. API endpoints also expose category and region management.

The visual system is deliberately restrained: `#FBFAF7` cream ground, `#111` ink, thin black rules, flat `#FF6B00` orange and `#00A651` green accents, Space Grotesk/Helvetica typography, gallery spacing, and no gradients or glass effects.

## Repository commands

```bash
# API tests
.venv/bin/python -m pytest tests/ -q

# Seed (image verification runs first)
.venv/bin/python seed.py

# Frontend production build
cd frontend && npm run build
```
