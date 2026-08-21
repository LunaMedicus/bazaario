from flask import Flask, jsonify
from flask_cors import CORS

from .config import Config
from .extensions import db, jwt


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    jwt.init_app(app)
    origins = [origin.strip() for origin in app.config["CORS_ORIGINS"].split(",") if origin.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}})

    from .routes import api

    app.register_blueprint(api, url_prefix="/api")

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
