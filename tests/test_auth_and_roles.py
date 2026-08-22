from tests.conftest import login
from backend.bazaario.extensions import db
from backend.bazaario.models import User


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_jwt_role_claim_lands_on_role_specific_identity(client, auth_tokens):
    response = client.get("/api/auth/me", headers=bearer(auth_tokens["customer"]))

    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "customer"


def test_wrong_role_calls_are_rejected_before_role_business_logic(client, auth_tokens):
    customer_headers = bearer(auth_tokens["customer"])
    shop_headers = bearer(auth_tokens["shop"])

    shop_response = client.get("/api/shop/dashboard", headers=customer_headers)
    admin_response = client.get("/api/admin/dashboard", headers=shop_headers)

    assert shop_response.status_code == 403
    assert admin_response.status_code == 403
    assert shop_response.get_json()["error"] == "forbidden"
    assert admin_response.get_json()["error"] == "forbidden"


def test_customer_registration_is_open_but_admin_registration_is_not(client):
    customer_response = client.post(
        "/api/auth/register/customer",
        json={
            "email": "new.customer@test.az",
            "password": "NewCustomer!123",
            "display_name": "New Customer",
        },
    )
    admin_response = client.post(
        "/api/auth/register/admin",
        json={
            "email": "bad.admin@test.az",
            "password": "BadAdmin!123",
        },
    )

    assert customer_response.status_code == 201
    assert admin_response.status_code == 404


def test_suspended_account_is_rejected_even_with_an_existing_token(client, auth_tokens):
    response = client.post(
        "/api/admin/users/3/suspend", headers=bearer(auth_tokens["admin"])
    )
    assert response.status_code == 200

    dashboard = client.get(
        "/api/customer/dashboard", headers=bearer(auth_tokens["customer"])
    )
    assert dashboard.status_code == 403
    assert dashboard.get_json()["code"] == "account_suspended"

    me = client.get("/api/auth/me", headers=bearer(auth_tokens["customer"]))
    assert me.status_code == 403
    assert me.get_json()["code"] == "account_suspended"


def test_role_claim_must_match_current_user_role(app, client, auth_tokens):
    with app.app_context():
        user = User.query.filter_by(email="customer@test.az").first()
        user.role = "shop"
        db.session.commit()

    dashboard = client.get(
        "/api/customer/dashboard", headers=bearer(auth_tokens["customer"])
    )

    assert dashboard.status_code == 403
    assert dashboard.get_json()["error"] == "forbidden"


def test_suspended_shop_products_are_hidden_and_unreviewable(client, auth_tokens):
    suspended = client.post(
        "/api/admin/shops/2/suspend", headers=bearer(auth_tokens["admin"])
    )
    assert suspended.status_code == 200

    catalog = client.get("/api/products")
    detail = client.get("/api/products/1")
    review = client.post(
        "/api/products/1/reviews",
        headers=bearer(auth_tokens["customer"]),
        json={"rating": 5},
    )

    assert catalog.status_code == 200
    assert all(product["shop"]["id"] != 2 for product in catalog.get_json()["products"])
    assert detail.status_code == 404
    assert review.status_code == 404


def test_shop_registration_starts_pending_and_cannot_publish(client):
    registration = client.post(
        "/api/auth/register/shop",
        json={
            "email": "pending.shop@test.az",
            "password": "PendingShop!123",
            "display_name": "Pending Shop Owner",
            "shop_name": "Pending Lankaran Shop",
            "region": "Lankaran",
        },
    )
    assert registration.status_code == 201
    token = login(client, "pending.shop@test.az", "PendingShop!123")

    listing = client.post(
        "/api/shop/listings",
        headers=bearer(token),
        json={
            "name": "Pending Tomatoes",
            "category": "Vegetables",
            "price_azn": 3.25,
            "stock": 10,
            "season": "June–September",
            "image_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=1200&q=80",
        },
    )

    assert listing.status_code == 403
    assert listing.get_json()["code"] == "shop_verification_required"


def test_archived_category_rejects_new_listings(client, auth_tokens):
    categories = client.get(
        "/api/admin/categories", headers=bearer(auth_tokens["admin"])
    ).get_json()["categories"]
    fruit = next(category for category in categories if category["name"] == "Fruit")

    archived = client.delete(
        f"/api/admin/categories/{fruit['id']}", headers=bearer(auth_tokens["admin"])
    )
    assert archived.status_code == 200

    listing = client.post(
        "/api/shop/listings",
        headers=bearer(auth_tokens["shop"]),
        json={
            "name": "Archived Category Apples",
            "category": "Fruit",
            "price_azn": 4.5,
            "stock": 10,
            "season": "August–October",
            "image_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=1200&q=80",
        },
    )

    assert listing.status_code == 422
    assert listing.get_json()["code"] == "category_archived"


def test_customers_and_shops_exchange_product_messages(client, auth_tokens):
    started = client.post(
        "/api/products/1/messages",
        headers=bearer(auth_tokens["customer"]),
        json={"body": "Is this harvest available this week?"},
    )
    assert started.status_code == 201

    thread = client.get("/api/shop/messages", headers=bearer(auth_tokens["shop"]))
    assert thread.status_code == 200
    target = thread.get_json()["threads"][0]
    assert target["product_id"] == 1
    assert target["message_count"] == 1

    reply = client.post(
        "/api/products/1/messages",
        headers=bearer(auth_tokens["shop"]),
        json={
            "body": "Yes, call me to arrange pickup.",
            "customer_id": target["customer_id"],
        },
    )
    assert reply.status_code == 201

    transcript = client.get(
        "/api/products/1/messages", headers=bearer(auth_tokens["customer"])
    )
    bodies = [message["body"] for message in transcript.get_json()["messages"]]
    assert bodies == [
        "Is this harvest available this week?",
        "Yes, call me to arrange pickup.",
    ]

    other = client.post(
        "/api/auth/register/shop",
        json={
            "email": "second.shop@test.az",
            "password": "SecondShoper!123",
            "display_name": "Second Shop",
            "shop_name": "Second Test Shop",
            "region": "Goychay",
            "region2": None,
        },
    )
    assert other.status_code == 201
    other_shop = client.post(
        "/api/auth/login",
        json={"email": "second.shop@test.az", "password": "SecondShoper!123"},
    )
    assert other_shop.status_code == 200
    blocked = client.get(
        "/api/products/1/messages",
        headers=bearer(other_shop.get_json()["access_token"]),
    )
    assert blocked.status_code == 404


def test_shop_phone_validation_and_clearing(client, auth_tokens):
    updated = client.put(
        "/api/shop/phone",
        headers=bearer(auth_tokens["shop"]),
        json={"phone": "+994 50 123 45 67"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["profile"]["phone"] == "+994 50 123 45 67"

    cleared = client.put(
        "/api/shop/phone",
        headers=bearer(auth_tokens["shop"]),
        json={"phone": "   "},
    )
    assert cleared.status_code == 200
    assert cleared.get_json()["profile"]["phone"] is None

    invalid = client.put(
        "/api/shop/phone",
        headers=bearer(auth_tokens["shop"]),
        json={"phone": "not a phone"},
    )
    assert invalid.status_code == 422
