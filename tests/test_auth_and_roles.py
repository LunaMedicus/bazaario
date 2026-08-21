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
    farmer_headers = bearer(auth_tokens["farmer"])

    farmer_response = client.get("/api/farmer/dashboard", headers=customer_headers)
    admin_response = client.get("/api/admin/dashboard", headers=farmer_headers)

    assert farmer_response.status_code == 403
    assert admin_response.status_code == 403
    assert farmer_response.get_json()["error"] == "forbidden"
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
        user.role = "farmer"
        db.session.commit()

    dashboard = client.get(
        "/api/customer/dashboard", headers=bearer(auth_tokens["customer"])
    )

    assert dashboard.status_code == 403
    assert dashboard.get_json()["error"] == "forbidden"


def test_suspended_farmer_products_are_hidden_and_not_orderable(client, auth_tokens):
    suspended = client.post(
        "/api/admin/farmers/2/suspend", headers=bearer(auth_tokens["admin"])
    )
    assert suspended.status_code == 200

    catalog = client.get("/api/products")
    detail = client.get("/api/products/1")
    checkout = client.post(
        "/api/customer/orders",
        headers=bearer(auth_tokens["customer"]),
        json={
            "items": [{"product_id": 1, "quantity": 1}],
            "delivery_address": "Test address",
            "payment_method": "cash_on_delivery",
        },
    )

    assert catalog.status_code == 200
    assert all(product["farm"]["id"] != 2 for product in catalog.get_json()["products"])
    assert detail.status_code == 404
    assert checkout.status_code == 404


def test_farmer_registration_starts_pending_and_cannot_publish(client):
    registration = client.post(
        "/api/auth/register/farmer",
        json={
            "email": "pending.farmer@test.az",
            "password": "PendingFarmer!123",
            "display_name": "Pending Farmer",
            "farm_name": "Pending Lankaran Farm",
            "region": "Lankaran",
            "document_reference": "DOC-PENDING-01",
        },
    )
    assert registration.status_code == 201
    token = login(client, "pending.farmer@test.az", "PendingFarmer!123")

    listing = client.post(
        "/api/farmer/listings",
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
    assert listing.get_json()["code"] == "farmer_verification_required"


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
        "/api/farmer/listings",
        headers=bearer(auth_tokens["farmer"]),
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


def test_customers_and_farmers_exchange_product_messages(client, auth_tokens):
    started = client.post(
        "/api/products/1/messages",
        headers=bearer(auth_tokens["customer"]),
        json={"body": "Is this harvest available this week?"},
    )
    assert started.status_code == 201

    thread = client.get("/api/farmer/messages", headers=bearer(auth_tokens["farmer"]))
    assert thread.status_code == 200
    target = thread.get_json()["threads"][0]
    assert target["product_id"] == 1
    assert target["message_count"] == 1

    reply = client.post(
        "/api/products/1/messages",
        headers=bearer(auth_tokens["farmer"]),
        json={
            "body": "Yes — call me to arrange pickup.",
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
        "Yes — call me to arrange pickup.",
    ]

    other = client.post(
        "/api/auth/register/farmer",
        json={
            "email": "second.farmer@test.az",
            "password": "SecondFarmer!123",
            "display_name": "Second Farmer",
            "farm_name": "Second Test Farm",
            "region": "Goychay",
            "document_reference": "DOC-TEST-002",
        },
    )
    assert other.status_code == 201
    other_farmer = client.post(
        "/api/auth/login",
        json={"email": "second.farmer@test.az", "password": "SecondFarmer!123"},
    )
    assert other_farmer.status_code == 200
    blocked = client.get(
        "/api/products/1/messages",
        headers=bearer(other_farmer.get_json()["access_token"]),
    )
    assert blocked.status_code == 404


def test_farmer_phone_validation_and_clearing(client, auth_tokens):
    updated = client.put(
        "/api/farmer/phone",
        headers=bearer(auth_tokens["farmer"]),
        json={"phone": "+994 50 123 45 67"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["profile"]["phone"] == "+994 50 123 45 67"

    cleared = client.put(
        "/api/farmer/phone",
        headers=bearer(auth_tokens["farmer"]),
        json={"phone": "   "},
    )
    assert cleared.status_code == 200
    assert cleared.get_json()["profile"]["phone"] is None

    invalid = client.put(
        "/api/farmer/phone",
        headers=bearer(auth_tokens["farmer"]),
        json={"phone": "not a phone"},
    )
    assert invalid.status_code == 422
