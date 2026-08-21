from tests.conftest import login
from backend.bazaario.extensions import db


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_non_agricultural_category_is_rejected_with_422(client, auth_tokens):
    response = client.post(
        "/api/farmer/listings",
        headers=bearer(auth_tokens["farmer"]),
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
        "/api/farmer/listings",
        headers=bearer(auth_tokens["farmer"]),
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
        "/api/farmer/listings",
        headers=bearer(auth_tokens["farmer"]),
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
        "/api/farmer/listings",
        headers=bearer(auth_tokens["farmer"]),
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


def test_non_object_json_payload_returns_422(client, auth_tokens):
    response = client.post(
        "/api/customer/orders",
        headers=bearer(auth_tokens["customer"]),
        json=["not", "an", "object"],
    )

    assert response.status_code == 422
    assert response.get_json()["code"] == "validation_error"


def test_order_lifecycle_is_sequential_and_creates_exactly_five_audits(
    app, client, auth_tokens
):
    headers = bearer(auth_tokens["customer"])
    products = client.get("/api/products").get_json()["products"]
    product_id = products[0]["id"]

    placed = client.post(
        "/api/customer/orders",
        headers=headers,
        json={
            "items": [{"product_id": product_id, "quantity": 2}],
            "delivery_address": "12 Nizami Street, Baku",
            "payment_method": "cash_on_delivery",
        },
    )
    assert placed.status_code == 201, placed.get_json()
    order_id = placed.get_json()["order"]["id"]
    assert placed.get_json()["order"]["status"] == "placed"
    assert len(placed.get_json()["order"]["audit"] ) == 1

    farmer_headers = bearer(auth_tokens["farmer"])
    confirmed = client.post(
        f"/api/farmer/orders/{order_id}/confirm", headers=farmer_headers
    )
    harvested = client.post(
        f"/api/farmer/orders/{order_id}/harvested", headers=farmer_headers
    )
    transit = client.post(
        f"/api/admin/orders/{order_id}/in-transit",
        headers=bearer(auth_tokens["admin"]),
    )
    delivered = client.post(
        f"/api/customer/orders/{order_id}/delivered", headers=headers
    )

    assert confirmed.status_code == 200
    assert harvested.status_code == 200
    assert transit.status_code == 200
    assert delivered.status_code == 200
    assert delivered.get_json()["order"]["status"] == "delivered"

    with app.app_context():
        from backend.bazaario.models import Order, OrderAudit

        order = db.session.get(Order, order_id)
        audits = OrderAudit.query.filter_by(order_id=order_id).order_by(OrderAudit.id).all()
        assert order.status == "delivered"
        assert len(audits) == 5
        assert [audit.to_status for audit in audits] == [
            "placed",
            "confirmed",
            "harvested",
            "in_transit",
            "delivered",
        ]


def test_order_transition_cannot_skip_a_state(client, auth_tokens):
    product_id = client.get("/api/products").get_json()["products"][0]["id"]
    placed = client.post(
        "/api/customer/orders",
        headers=bearer(auth_tokens["customer"]),
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            "delivery_address": "Test address",
            "payment_method": "card_sandbox",
        },
    )
    order_id = placed.get_json()["order"]["id"]

    skipped = client.post(
        f"/api/admin/orders/{order_id}/in-transit",
        headers=bearer(auth_tokens["admin"]),
    )

    assert skipped.status_code == 409
    assert skipped.get_json()["code"] == "invalid_transition"
