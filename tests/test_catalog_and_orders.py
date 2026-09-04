from tests.conftest import login

from backend.bazaario.extensions import db
from backend.bazaario.models import Product, User


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_non_agricultural_category_is_rejected_with_422(client, auth_tokens):
    response = client.post(
        "/api/shop/listings",
        headers=bearer(auth_tokens["shop"]),
        json={
            "name": "Wireless Speaker",
            "category": "Electronics",
            "price_azn": 50,
            "stock": 2,
            "season": "All year",
            "image_url": "https://images.unsplash.com/photo-1545454675-3531b543be5d?w=1200&q=80",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["code"] == "invalid_category"


def test_listing_rejects_non_hotlink_image_sources(client, auth_tokens):
    response = client.post(
        "/api/shop/listings",
        headers=bearer(auth_tokens["shop"]),
        json={
            "name": "Sample Apples",
            "category": "Fruit",
            "price_azn": 4,
            "stock": 2,
            "season": "Autumn",
            "image_url": "https://example.com/not-a-photo.jpg",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["code"] == "image_source_not_allowed"


def test_listing_rejects_an_allowed_host_that_is_not_a_live_image(client, auth_tokens):
    response = client.post(
        "/api/shop/listings",
        headers=bearer(auth_tokens["shop"]),
        json={
            "name": "Missing Photo Apples",
            "category": "Fruit",
            "price_azn": 4,
            "stock": 2,
            "season": "Autumn",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/does-not-exist-bazaario.jpg",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["code"] == "image_not_verified"


def test_non_finite_price_is_rejected_with_422(client, auth_tokens):
    response = client.post(
        "/api/shop/listings",
        headers=bearer(auth_tokens["shop"]),
        json={
            "name": "Invalid Price Apples",
            "category": "Fruit",
            "price_azn": "NaN",
            "stock": 2,
            "season": "Autumn",
            "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=1200&q=80",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["code"] == "validation_error"


def test_customer_can_filter_catalog_by_category(client):
    response = client.get("/api/products?category=Fruit")

    assert response.status_code == 200
    assert response.get_json()["products"]
    assert all(product["category"] == "Fruit" for product in response.get_json()["products"])

    autumn = client.get("/api/products?season=Autumn")
    assert autumn.status_code == 200
    assert autumn.get_json()["products"]


def test_catalog_search_combines_translated_and_original_terms(client, app):
    with app.app_context():
        shop = User.query.filter_by(email="shop@test.az").one()
        db.session.add(
            Product(
                shop_id=shop.id,
                name="Wildflower Honey Jar",
                category="Honey & bee products",
                price_azn=16,
                stock=12,
                season="May–September",
                image_url="https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=1200&q=80",
                description="Raw honey from meadow hives.",
            )
        )
        db.session.add(
            Product(
                shop_id=shop.id,
                name="Balanced Orchard Box",
                category="Fruit",
                price_azn=10,
                stock=8,
                season="All year",
                image_url="https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=1200&q=80",
                description="A mixed fruit box.",
            )
        )
        db.session.commit()

    honey = client.get(
        "/api/products", query_string={"q": "honey", "q_original": "Bal"}
    )
    assert honey.status_code == 200
    assert {product["category"] for product in honey.get_json()["products"]} == {
        "Honey & bee products"
    }

    apples = client.get(
        "/api/products", query_string={"q": "apple", "q_original": "alma"}
    )
    assert apples.status_code == 200
    assert [product["name"] for product in apples.get_json()["products"]] == [
        "Test Apples"
    ]

    fallback = client.get(
        "/api/products",
        query_string={"q": "not-in-the-catalog", "q_original": "Balanced"},
    )
    assert fallback.status_code == 200
    assert [product["name"] for product in fallback.get_json()["products"]] == [
        "Balanced Orchard Box"
    ]


def test_non_object_json_payload_returns_422(client, auth_tokens):
    response = client.post(
        "/api/products/1/reviews",
        headers=bearer(auth_tokens["customer"]),
        json=["not", "an", "object"],
    )

    assert response.status_code == 422
    assert response.get_json()["code"] == "validation_error"


def test_customer_reviews_a_product_and_updates_their_review(client, auth_tokens):
    product_id = client.get("/api/products").get_json()["products"][0]["id"]
    headers = bearer(auth_tokens["customer"])

    first = client.post(
        f"/api/products/{product_id}/reviews",
        headers=headers,
        json={"rating": 5, "body": "Excellent dried figs."},
    )
    assert first.status_code == 201, first.get_json()

    updated = client.post(
        f"/api/products/{product_id}/reviews",
        headers=headers,
        json={"rating": 4, "body": "Still very good."},
    )
    assert updated.status_code == 201
    detail = client.get(f"/api/products/{product_id}").get_json()["product"]
    assert len(detail["reviews"]) == 1
    assert detail["reviews"][0]["rating"] == 4
    assert detail["review_count"] == 1


def test_shop_accounts_cannot_review_products(client, auth_tokens):
    product_id = client.get("/api/products").get_json()["products"][0]["id"]

    blocked = client.post(
        f"/api/products/{product_id}/reviews",
        headers=bearer(auth_tokens["shop"]),
        json={"rating": 5},
    )

    assert blocked.status_code == 403


def test_reviews_identify_their_author_by_id_not_display_name(client, auth_tokens):
    """Two customers may share a display name; only the id tells them apart."""
    client.post(
        "/api/auth/register/customer",
        json={
            "display_name": "Customer",  # same display name as the fixture user
            "email": "twin@test.az",
            "password": "TwinPass!123",
        },
    )
    twin = client.post(
        "/api/auth/login", json={"email": "twin@test.az", "password": "TwinPass!123"}
    ).get_json()

    client.post(
        "/api/products/1/reviews",
        json={"rating": 5, "body": "From the fixture customer."},
        headers={"Authorization": f"Bearer {auth_tokens['customer']}"},
    )
    client.post(
        "/api/products/1/reviews",
        json={"rating": 2, "body": "From the twin."},
        headers={"Authorization": f"Bearer {twin['access_token']}"},
    )

    reviews = client.get("/api/products/1").get_json()["product"]["reviews"]
    assert len(reviews) == 2
    assert {review["customer"] for review in reviews} == {"Customer"}

    by_twin = [r for r in reviews if r["customer_id"] == twin["user"]["id"]]
    assert len(by_twin) == 1
    assert by_twin[0]["body"] == "From the twin."


def test_the_shop_dashboard_does_not_scale_queries_with_listing_count(
    client, app, auth_tokens
):
    """Rendering the dashboard must not cost a query per listing."""
    from sqlalchemy import event

    from backend.bazaario.extensions import db

    headers = {"Authorization": f"Bearer {auth_tokens['shop']}"}
    listing = {
        "category": "Fruit",
        "price_azn": 3.0,
        "stock": 5,
        "season": "All year",
        "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=1200&q=80",
    }
    for index in range(6):
        client.post("/api/shop/listings", json={**listing, "name": f"Extra {index}"}, headers=headers)

    statements = []
    with app.app_context():
        engine = db.engine

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        response = client.get("/api/shop/dashboard", headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", record)

    assert response.status_code == 200
    assert response.get_json()["listing_count"] == 7
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    # Identity lookup, the eager listing query and its reviews load -- a
    # constant, not one query per listing.
    assert len(selects) <= 8, f"{len(selects)} SELECTs for 7 listings:\n" + "\n".join(selects)
