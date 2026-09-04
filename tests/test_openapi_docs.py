"""The published API description must stay in step with the routes."""

from backend.bazaario.openapi import ALLOWED_CATEGORIES


def test_openapi_document_is_served_without_a_token(client):
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    spec = response.get_json()
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "Bazaario API"


def test_swagger_ui_renders_and_points_at_the_spec(client):
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    body = response.get_data(as_text=True)
    assert "/api/openapi.json" in body
    assert "SPEC_URL" not in body


def test_every_registered_api_route_is_documented(app, client):
    spec = client.get("/api/openapi.json").get_json()
    documented = set(spec["paths"])

    undocumented = set()
    for rule in app.url_map.iter_rules():
        if not str(rule).startswith("/api/"):
            continue
        if rule.endpoint in {"api.openapi_spec", "api.api_docs"}:
            continue
        # Flask writes "<int:product_id>" where OpenAPI writes "{product_id}".
        path = str(rule)
        for converter in ("int:", "string:", "path:"):
            path = path.replace(f"<{converter}", "<")
        path = path.replace("<", "{").replace(">", "}")
        if path not in documented:
            undocumented.add(path)

    assert not undocumented, f"Undocumented API routes: {sorted(undocumented)}"


def test_documented_methods_match_the_registered_methods(app, client):
    spec = client.get("/api/openapi.json").get_json()

    registered = {}
    for rule in app.url_map.iter_rules():
        if not str(rule).startswith("/api/"):
            continue
        path = str(rule)
        for converter in ("int:", "string:", "path:"):
            path = path.replace(f"<{converter}", "<")
        path = path.replace("<", "{").replace(">", "}")
        verbs = {method.lower() for method in rule.methods} - {"head", "options"}
        registered.setdefault(path, set()).update(verbs)

    for path, operations in spec["paths"].items():
        assert path in registered, f"{path} is documented but not routed"
        assert set(operations) <= registered[path], (
            f"{path} documents methods the app does not serve: "
            f"{sorted(set(operations) - registered[path])}"
        )


def test_spec_advertises_the_agricultural_allow_list(client):
    spec = client.get("/api/openapi.json").get_json()
    category = spec["components"]["schemas"]["Product"]["properties"]["category"]
    assert category["enum"] == list(ALLOWED_CATEGORIES)


def test_protected_operations_declare_bearer_security(client):
    spec = client.get("/api/openapi.json").get_json()
    for path, operations in spec["paths"].items():
        if not path.startswith(("/api/customer/", "/api/shop/", "/api/admin/")):
            continue
        for verb, operation in operations.items():
            assert operation.get("security") == [{"bearerAuth": []}], (
                f"{verb.upper()} {path} does not require a bearer token"
            )
