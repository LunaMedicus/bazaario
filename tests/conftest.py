import pytest

from backend.bazaario import create_app
from backend.bazaario.extensions import db
from backend.bazaario.models import Category, FarmerProfile, Product, Region, User


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "JWT_SECRET_KEY": "test-secret-that-is-long-enough-for-hs256",
        }
    )
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Category(name="Fruit"),
                Category(name="Vegetables"),
                Region(name="Goychay"),
            ]
        )
        admin = User(email="admin@test.az", role="admin", display_name="Admin")
        admin.set_password("AdminPass!123")
        farmer = User(email="farmer@test.az", role="farmer", display_name="Farmer")
        farmer.set_password("FarmerPass!123")
        customer = User(email="customer@test.az", role="customer", display_name="Customer")
        customer.set_password("CustomerPass!123")
        db.session.add_all([admin, farmer, customer])
        db.session.flush()
        db.session.add(
            FarmerProfile(
                user_id=farmer.id,
                farm_name="Test Goychay Farm",
                region="Goychay",
                document_reference="DOC-TEST-001",
                verification_status="approved",
            )
        )
        db.session.add(
            Product(
                farmer_id=farmer.id,
                name="Test Apples",
                category="Fruit",
                price_azn=4.50,
                stock=20,
                season="August–October",
                image_url="https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=1200&q=80",
                description="Crisp apples from the test farm.",
            )
        )
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password):
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()["access_token"]


@pytest.fixture()
def auth_tokens(client):
    return {
        "admin": login(client, "admin@test.az", "AdminPass!123"),
        "farmer": login(client, "farmer@test.az", "FarmerPass!123"),
        "customer": login(client, "customer@test.az", "CustomerPass!123"),
    }
