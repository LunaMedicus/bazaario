from werkzeug.test import Client
from werkzeug.wrappers import Response

from api.index import app


def test_vercel_rewrite_restores_public_api_path():
    client = Client(app, Response)
    response = client.get("/api/index.py?path=meta")

    assert response.status_code == 200
    payload = response.get_json()
    assert "Fruit" in payload["categories"]
