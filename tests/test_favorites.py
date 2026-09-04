"""Saved products: ownership, idempotence and catalog visibility rules."""

from backend.bazaario.extensions import db
from backend.bazaario.models import Product, User


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def only_product_id(app):
    with app.app_context():
        return Product.query.first().id


def test_customer_saves_lists_and_removes_a_product(client, app, auth_tokens):
    product_id = only_product_id(app)
    headers = auth(auth_tokens["customer"])

    created = client.post(f"/api/customer/favorites/{product_id}", headers=headers)
    assert created.status_code == 201
    assert created.get_json()["is_favorite"] is True

    listed = client.get("/api/customer/favorites", headers=headers)
    assert listed.status_code == 200
    body = listed.get_json()
    assert body["count"] == 1
    assert [product["id"] for product in body["favorites"]] == [product_id]

    removed = client.delete(f"/api/customer/favorites/{product_id}", headers=headers)
    assert removed.status_code == 200
    assert removed.get_json()["is_favorite"] is False
    assert client.get("/api/customer/favorites", headers=headers).get_json()["count"] == 0


def test_saving_twice_does_not_create_a_duplicate(client, app, auth_tokens):
    product_id = only_product_id(app)
    headers = auth(auth_tokens["customer"])

    assert client.post(f"/api/customer/favorites/{product_id}", headers=headers).status_code == 201
    again = client.post(f"/api/customer/favorites/{product_id}", headers=headers)
    assert again.status_code == 200
    assert again.get_json()["is_favorite"] is True
    assert client.get("/api/customer/favorites", headers=headers).get_json()["count"] == 1


def test_removing_something_never_saved_is_not_an_error(client, app, auth_tokens):
    product_id = only_product_id(app)
    response = client.delete(
        f"/api/customer/favorites/{product_id}", headers=auth(auth_tokens["customer"])
    )
    assert response.status_code == 200
    assert response.get_json()["is_favorite"] is False


def test_favorites_are_private_to_the_customer_who_saved_them(client, app, auth_tokens):
    product_id = only_product_id(app)
    client.post(
        f"/api/customer/favorites/{product_id}", headers=auth(auth_tokens["customer"])
    )

    other = client.post(
        "/api/auth/register/customer",
        json={
            "display_name": "Second Customer",
            "email": "second@test.az",
            "password": "SecondPass!123",
        },
    )
    assert other.status_code == 201
    token = client.post(
        "/api/auth/login", json={"email": "second@test.az", "password": "SecondPass!123"}
    ).get_json()["access_token"]

    assert client.get("/api/customer/favorites", headers=auth(token)).get_json()["count"] == 0


def test_shops_and_admins_cannot_use_the_favorites_routes(client, app, auth_tokens):
    product_id = only_product_id(app)
    for role in ("shop", "admin"):
        headers = auth(auth_tokens[role])
        assert client.get("/api/customer/favorites", headers=headers).status_code == 403
        assert client.post(f"/api/customer/favorites/{product_id}", headers=headers).status_code == 403
        assert client.delete(f"/api/customer/favorites/{product_id}", headers=headers).status_code == 403


def test_favorites_require_a_token(client, app):
    product_id = only_product_id(app)
    assert client.get("/api/customer/favorites").status_code == 401
    assert client.post(f"/api/customer/favorites/{product_id}").status_code == 401


def test_saving_a_product_that_is_not_publicly_visible_is_refused(client, app, auth_tokens):
    product_id = only_product_id(app)
    with app.app_context():
        product = db.session.get(Product, product_id)
        product.stock = 0
        db.session.commit()

    response = client.post(
        f"/api/customer/favorites/{product_id}", headers=auth(auth_tokens["customer"])
    )
    assert response.status_code == 404
    assert response.get_json()["code"] == "not_found"


def test_a_saved_product_drops_out_of_the_list_when_its_shop_is_suspended(
    client, app, auth_tokens
):
    product_id = only_product_id(app)
    headers = auth(auth_tokens["customer"])
    assert client.post(f"/api/customer/favorites/{product_id}", headers=headers).status_code == 201

    with app.app_context():
        shop = User.query.filter_by(role="shop").first()
        shop_id = shop.id
    client.post(f"/api/admin/shops/{shop_id}/suspend", headers=auth(auth_tokens["admin"]))

    body = client.get("/api/customer/favorites", headers=headers).get_json()
    assert body["count"] == 0
    assert body["favorites"] == []


def test_a_saved_product_drops_out_of_the_list_when_it_is_archived(client, app, auth_tokens):
    product_id = only_product_id(app)
    headers = auth(auth_tokens["customer"])
    client.post(f"/api/customer/favorites/{product_id}", headers=headers)

    client.delete(f"/api/shop/listings/{product_id}", headers=auth(auth_tokens["shop"]))

    assert client.get("/api/customer/favorites", headers=headers).get_json()["count"] == 0
