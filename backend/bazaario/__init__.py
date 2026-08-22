from flask import Flask, jsonify, request
from flask_cors import CORS

from .config import Config
from .extensions import db, jwt


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    # Gzip JSON payloads. The catalog compresses roughly ten to one, so
    # clients download far fewer bytes.
    app.config["COMPRESS_MIMETYPES"] = [
        "application/json",
        "text/html",
        "text/css",
        "text/plain",
    ]
    app.config["COMPRESS_LEVEL"] = 6
    from flask_compress import Compress

    Compress(app)

    db.init_app(app)
    jwt.init_app(app)
    origins = [origin.strip() for origin in app.config["CORS_ORIGINS"].split(",") if origin.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}})

    from .routes import api

    app.register_blueprint(api, url_prefix="/api")

    @app.after_request
    def cache_public_catalog(response):
        # Public, unauthenticated catalog reads are safe to reuse for a short
        # window; anything else must not be stored.
        if (
            response.status_code == 200
            and request.method == "GET"
            and request.path in {"/api/products", "/api/meta"}
            and not request.args.get("q")
        ):
            response.headers["Cache-Control"] = "public, max-age=60"
        return response

    @jwt.unauthorized_loader
    def missing_token(message):
        return jsonify(error="unauthorized", message=message), 401

    @jwt.invalid_token_loader
    def invalid_token(message):
        return jsonify(error="unauthorized", message=message), 401

    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_payload):
        return jsonify(error="unauthorized", message="Token has expired"), 401

    with app.app_context():
        db.create_all()

    return app
