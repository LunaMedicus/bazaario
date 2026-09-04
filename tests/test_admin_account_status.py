"""An account and its shop profile must never disagree about suspension."""

from backend.bazaario.models import ShopProfile, User


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def shop_state(app, email="shop@test.az"):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        profile = ShopProfile.query.filter_by(user_id=user.id).first()
        return user.account_status, profile.verification_status


def shop_id(app, email="shop@test.az"):
    with app.app_context():
        return User.query.filter_by(email=email).first().id


def test_suspending_a_shop_from_the_user_list_also_suspends_its_profile(
    client, app, auth_tokens
):
    response = client.post(
        f"/api/admin/users/{shop_id(app)}/suspend", headers=auth(auth_tokens["admin"])
    )
    assert response.status_code == 200
    assert shop_state(app) == ("suspended", "suspended")


def test_restoring_a_verified_shop_returns_it_to_approved(client, app, auth_tokens):
    headers = auth(auth_tokens["admin"])
    identifier = shop_id(app)

    client.post(f"/api/admin/shops/{identifier}/approve", headers=headers)
    client.post(f"/api/admin/users/{identifier}/suspend", headers=headers)
    assert shop_state(app) == ("suspended", "suspended")

    client.post(f"/api/admin/users/{identifier}/restore", headers=headers)
    assert shop_state(app) == ("active", "approved")


def test_restoring_a_never_verified_shop_leaves_it_pending(client, app, auth_tokens):
    headers = auth(auth_tokens["admin"])
    client.post(
        "/api/auth/register/shop",
        json={
            "display_name": "Applicant",
            "email": "applicant@test.az",
            "password": "ApplyPass!123",
            "shop_name": "Applicant Stall",
            "region": "Goychay",
        },
    )
    identifier = shop_id(app, "applicant@test.az")

    client.post(f"/api/admin/users/{identifier}/suspend", headers=headers)
    client.post(f"/api/admin/users/{identifier}/restore", headers=headers)

    # A restore undoes the suspension; it must not double as an approval.
    assert shop_state(app, "applicant@test.az") == ("active", "pending_verification")


def test_a_suspended_shop_disappears_from_the_verification_queue_as_pending(
    client, app, auth_tokens
):
    headers = auth(auth_tokens["admin"])
    client.post(f"/api/admin/users/{shop_id(app)}/suspend", headers=headers)

    approved = client.get("/api/admin/shops?status=approved", headers=headers).get_json()
    assert approved["shops"] == []

    suspended = client.get("/api/admin/shops?status=suspended", headers=headers).get_json()
    assert len(suspended["shops"]) == 1


def test_suspending_a_customer_does_not_touch_any_shop_profile(client, app, auth_tokens):
    with app.app_context():
        customer_id = User.query.filter_by(email="customer@test.az").first().id

    client.post(
        f"/api/admin/users/{customer_id}/suspend", headers=auth(auth_tokens["admin"])
    )
    assert shop_state(app) == ("active", "approved")


def test_an_admin_still_cannot_suspend_their_own_account(client, app, auth_tokens):
    with app.app_context():
        admin_id = User.query.filter_by(email="admin@test.az").first().id

    response = client.post(
        f"/api/admin/users/{admin_id}/suspend", headers=auth(auth_tokens["admin"])
    )
    assert response.status_code == 422
