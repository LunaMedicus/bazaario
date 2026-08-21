from tests.conftest import login


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


def test_farmer_cannot_review_products(client, auth_tokens):
    product_id = client.get("/api/products").get_json()["products"][0]["id"]

    blocked = client.post(
        f"/api/products/{product_id}/reviews",
        headers=bearer(auth_tokens["farmer"]),
        json={"rating": 5},
    )

    assert blocked.status_code == 403
