from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlparse

import requests
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import (
    Category,
    ShopProfile,
    Message,
    Product,
    Region,
    Review,
    User,
    utc_now,
)


api = Blueprint("api", __name__)
ALLOWED_CATEGORIES = (
    "Fruit",
    "Vegetables",
    "Grains",
    "Dairy",
    "Honey & bee products",
    "Herbs",
    "Nuts",
    "Tea",
)
IMAGE_SOURCE_HOSTS = {
    "images.unsplash.com",
    "images.pexels.com",
    "upload.wikimedia.org",
}
SEASON_TERMS = {
    "Spring": ("Spring", "March", "April", "May"),
    "Summer": ("Summer", "June", "July", "August"),
    "Autumn": ("Autumn", "September", "October", "November"),
    "Winter": ("Winter", "December", "January", "February"),
}


class ApiError(Exception):
    def __init__(self, message, status=400, code=None):
        self.message = message
        self.status = status
        self.code = code
        super().__init__(message)


def _error_payload(message, code=None):
    payload = {"error": message}
    if code:
        payload["code"] = code
    return payload


@api.errorhandler(ApiError)
def handle_api_error(error):
    return jsonify(_error_payload(error.message, error.code)), error.status


def _data():
    payload = request.get_json(silent=True)
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ApiError("Request JSON must be an object", 422, "validation_error")
    return payload


def _required(data, *fields):
    missing = [
        field
        for field in fields
        if field not in data
        or data[field] is None
        or (isinstance(data[field], str) and not data[field].strip())
    ]
    if missing:
        raise ApiError(f"Missing required field(s): {', '.join(missing)}", 422, "validation_error")


def _text(data, field, max_length=None):
    _required(data, field)
    value = data[field]
    if not isinstance(value, str):
        raise ApiError(f"{field} must be text", 422, "validation_error")
    value = value.strip()
    if max_length and len(value) > max_length:
        raise ApiError(f"{field} is too long", 422, "validation_error")
    if not value:
        raise ApiError(f"{field} cannot be blank", 422, "validation_error")
    return value


def _current_user():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        raise ApiError("User no longer exists", 401, "unauthorized")
    if user.account_status == "suspended":
        raise ApiError("Account is suspended", 403, "account_suspended")
    if user.account_status != "active":
        raise ApiError("Account is not active", 403, "account_inactive")
    return user


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = get_jwt().get("role")
            if role not in allowed_roles:
                return jsonify({"error": "forbidden", "message": "You do not have permission for this role"}), 403
            user = db.session.get(User, int(get_jwt_identity()))
            if not user:
                return jsonify(_error_payload("User no longer exists", "unauthorized")), 401
            if user.account_status != "active":
                if user.account_status == "suspended":
                    return jsonify(_error_payload("Account is suspended", "account_suspended")), 403
                return jsonify(_error_payload("Account is not active", "account_inactive")), 403
            if user.role != role:
                return jsonify({"error": "forbidden", "message": "You do not have permission for this role"}), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _auth_payload(user):
    claims = {"role": user.role, "account_status": user.account_status}
    token = create_access_token(identity=str(user.id), additional_claims=claims)
    return {"access_token": token, "user": user.to_dict()}


def _normal_email(value):
    return str(value or "").strip().lower()


def _create_user(data, role):
    email = _text(data, "email", 255).lower()
    password = _text(data, "password", 200)
    display_name = _text(data, "display_name", 120)
    if "@" not in email or len(password) < 8:
        raise ApiError("Use a valid email and a password of at least 8 characters", 422, "validation_error")
    if User.query.filter_by(email=email).first():
        raise ApiError("An account with this email already exists", 409, "email_exists")
    user = User(email=email, display_name=display_name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def _verify_image_url(image_url):
    try:
        response = requests.get(
            image_url,
            headers={"User-Agent": "Bazaario image verifier/1.0"},
            allow_redirects=True,
            stream=True,
            timeout=(5, 10),
        )
    except requests.RequestException as exc:
        raise ApiError("image_url could not be verified", 422, "image_not_verified") from exc

    try:
        final_host = (urlparse(response.url).hostname or "").lower()
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        content_length = response.headers.get("Content-Length")
        if (
            response.status_code != 200
            or not content_type.startswith("image/")
            or final_host not in IMAGE_SOURCE_HOSTS
            or (content_length and int(content_length) > 10 * 1024 * 1024)
        ):
            raise ApiError(
                "image_url must resolve to a live image under 10 MB",
                422,
                "image_not_verified",
            )
    except (TypeError, ValueError) as exc:
        raise ApiError("image_url could not be verified", 422, "image_not_verified") from exc
    finally:
        response.close()


def _product_payload(data):
    name = _text(data, "name", 180)
    category = _text(data, "category", 80)
    season = _text(data, "season", 120)
    image_url = _text(data, "image_url", 2048)
    if category not in ALLOWED_CATEGORIES:
        raise ApiError(
            "Only agricultural categories are allowed",
            422,
            "invalid_category",
        )
    category_row = Category.query.filter_by(name=category).first()
    if category_row and not category_row.active:
        raise ApiError(
            "This category is archived and no longer accepts new listings",
            422,
            "category_archived",
        )
    try:
        price = Decimal(str(data["price_azn"]))
    except (InvalidOperation, TypeError, ValueError):
        raise ApiError("price_azn must be a number", 422, "validation_error")
    if not price.is_finite():
        raise ApiError("price_azn must be finite", 422, "validation_error")
    try:
        stock = int(data["stock"])
    except (TypeError, ValueError, OverflowError):
        raise ApiError("stock must be a whole number", 422, "validation_error")
    if isinstance(data["stock"], bool) or stock < 0:
        raise ApiError("stock must be a non-negative whole number", 422, "validation_error")
    if price < 0 or price > Decimal("99999999.99"):
        raise ApiError("price_azn is outside the supported range", 422, "validation_error")
    try:
        price = price.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ApiError("price_azn has too many decimal places", 422, "validation_error") from exc
    parsed = urlparse(image_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ApiError("image_url must be an http(s) URL", 422, "validation_error")
    if (parsed.hostname or "").lower() not in IMAGE_SOURCE_HOSTS:
        raise ApiError(
            "Use a hotlinkable Unsplash, Pexels, or Wikimedia Commons image",
            422,
            "image_source_not_allowed",
        )
    description = data.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise ApiError("description must be text", 422, "validation_error")
    return {
        "name": name,
        "category": category,
        "price_azn": price,
        "stock": stock,
        "season": season,
        "image_url": image_url,
        "description": description.strip(),
    }


def _ensure_can_publish(user):
    profile = user.shop_profile
    if not profile or profile.verification_status != "approved":
        raise ApiError(
            "Your shop must be approved before publishing listings",
            403,
            "shop_verification_required",
        )


def _commit():
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ApiError("The operation conflicts with current data", 409, "conflict") from exc
    except Exception:
        db.session.rollback()
        raise


@api.post("/auth/register/customer")
def register_customer():
    user = _create_user(_data(), "customer")
    _commit()
    return jsonify({"user": user.to_dict(), "message": "Customer account created"}), 201


@api.post("/auth/register/shop")
def register_shop():
    data = _data()
    shop_name = _text(data, "shop_name", 160)
    region = _text(data, "region", 120)
    user = _create_user(data, "shop")
    profile = ShopProfile(
        user_id=user.id,
        shop_name=shop_name,
        region=region,
        phone=_normalise_phone(data.get("phone")),
        verification_status="pending_verification",
    )
    db.session.add(profile)
    _commit()
    return jsonify({"user": user.to_dict(), "message": "Shop application submitted"}), 201


@api.post("/auth/login")
def login():
    data = _data()
    email = _text(data, "email", 255).lower()
    password = _text(data, "password", 200)
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise ApiError("Invalid email or password", 401, "invalid_credentials")
    if user.account_status != "active":
        if user.account_status == "suspended":
            raise ApiError("Account is suspended", 403, "account_suspended")
        raise ApiError("Account is not active", 403, "account_inactive")
    return jsonify(_auth_payload(user))


@api.get("/auth/me")
@jwt_required()
def me():
    return jsonify({"user": _current_user().to_dict()})


@api.get("/meta")
def meta():
    categories = [row.name for row in Category.query.filter_by(active=True).order_by(Category.name)]
    regions = [row.name for row in Region.query.filter_by(active=True).order_by(Region.name)]
    if not categories:
        categories = list(ALLOWED_CATEGORIES)
    return jsonify({"categories": categories, "regions": regions, "seasons": ["Spring", "Summer", "Autumn", "Winter", "All year"]})


@api.get("/products")
def products():
    query = (
        Product.query
        .join(User, Product.shop_id == User.id)
        .join(ShopProfile, ShopProfile.user_id == User.id)
        .filter(
            Product.available.is_(True),
            Product.stock > 0,
            User.account_status == "active",
            ShopProfile.verification_status == "approved",
        )
    )
    category = request.args.get("category")
    if category:
        if category not in ALLOWED_CATEGORIES:
            raise ApiError("Only agricultural categories are allowed", 422, "invalid_category")
        query = query.filter(Product.category == category)
    if request.args.get("region"):
        query = query.filter(ShopProfile.region == request.args["region"])
    if request.args.get("season"):
        season_terms = SEASON_TERMS.get(request.args["season"], (request.args["season"],))
        query = query.filter(
            or_(*(Product.season.ilike(f"%{term}%") for term in season_terms))
        )
    if request.args.get("q"):
        term = f"%{request.args['q'].strip()}%"
        query = query.filter(Product.name.ilike(term) | Product.description.ilike(term))
    rows = query.order_by(Product.created_at.desc()).all()
    return jsonify({"products": [product.to_dict() for product in rows], "count": len(rows)})


@api.get("/products/<int:product_id>")
def product_detail(product_id):
    product = (
        Product.query
        .join(User, Product.shop_id == User.id)
        .join(ShopProfile, ShopProfile.user_id == User.id)
        .filter(
            Product.id == product_id,
            Product.available.is_(True),
            User.account_status == "active",
            ShopProfile.verification_status == "approved",
        )
        .first()
    )
    if not product:
        raise ApiError("Product not found", 404, "not_found")
    payload = product.to_dict()
    payload["reviews"] = [review.to_dict() for review in product.reviews]
    return jsonify({"product": payload})


@api.post("/products/<int:product_id>/reviews")
@jwt_required()
@role_required("customer")
def create_product_review(product_id):
    user = _current_user()
    product = (
        Product.query
        .join(User, Product.shop_id == User.id)
        .join(ShopProfile, ShopProfile.user_id == User.id)
        .filter(
            Product.id == product_id,
            User.account_status == "active",
            ShopProfile.verification_status == "approved",
        )
        .first()
    )
    if not product:
        raise ApiError("Product not found", 404, "not_found")
    data = _data()
    _required(data, "rating")
    try:
        rating = int(data["rating"])
    except (TypeError, ValueError):
        raise ApiError("rating must be an integer", 422, "validation_error")
    if rating < 1 or rating > 5:
        raise ApiError("rating must be between 1 and 5", 422, "validation_error")
    body = data.get("body", "")
    if body is None:
        body = ""
    if not isinstance(body, str):
        raise ApiError("body must be text", 422, "validation_error")
    existing = Review.query.filter_by(product_id=product.id, customer_id=user.id).first()
    if existing:
        existing.rating = rating
        existing.body = body.strip()
        review = existing
    else:
        review = Review(
            product_id=product.id,
            customer_id=user.id,
            rating=rating,
            body=body.strip(),
        )
        db.session.add(review)
    _commit()
    return jsonify({"review": review.to_dict()}), 201


@api.get("/customer/dashboard")
@jwt_required()
@role_required("customer")
def customer_dashboard():
    user = _current_user()
    return jsonify(
        {
            "user": user.to_dict(),
            "catalog_count": Product.query.filter_by(available=True).count(),
            "message_thread_count": Message.query.filter_by(customer_id=user.id)
            .with_entities(Message.product_id, Message.customer_id)
            .distinct()
            .count(),
        }
    )


PHONE_ALLOWED_CHARACTERS = set("0123456789+ ()-")


def _normalise_phone(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ApiError("phone must be text", 422, "validation_error")
    phone = value.strip()
    if not phone:
        return None
    digits = sum(character.isdigit() for character in phone)
    if len(phone) > 40 or digits < 4 or not set(phone) <= PHONE_ALLOWED_CHARACTERS:
        raise ApiError("Enter a valid contact number", 422, "validation_error")
    return phone


@api.put("/shop/phone")
@jwt_required()
@role_required("shop")
def update_shop_phone():
    user = _current_user()
    profile = user.shop_profile
    if not profile:
        raise ApiError("Shop profile not found", 404, "not_found")
    data = _data()
    profile.phone = _normalise_phone(data.get("phone"))
    _commit()
    return jsonify({"profile": profile.to_dict(), "message": "Contact number updated"})


def _thread_digests(messages, name_for_customer):
    threads = {}
    order = []
    for message in sorted(messages, key=lambda item: (item.created_at, item.id)):
        key = (message.product_id, message.customer_id)
        thread = threads.get(key)
        if thread is None:
            thread = {
                "product_id": message.product_id,
                "product_name": message.product.name if message.product else None,
                "customer_id": message.customer_id,
                "customer_name": name_for_customer(message),
                "shop_name": message.product.shop.display_name
                if message.product and message.product.shop
                else None,
                "message_count": 0,
                "last_body": None,
                "last_sender_role": None,
                "last_created_at": None,
            }
            threads[key] = thread
            order.append(key)
        thread["message_count"] += 1
        thread["last_body"] = message.body
        thread["last_sender_role"] = message.sender_role
        thread["last_created_at"] = message.created_at.isoformat() if message.created_at else None
    return [threads[key] for key in order]


@api.get("/shop/messages")
@jwt_required()
@role_required("shop")
def shop_messages():
    user = _current_user()
    messages = (
        Message.query.join(Product, Message.product_id == Product.id)
        .filter(Product.shop_id == user.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    digests = _thread_digests(messages, lambda message: message.customer.display_name if message.customer else None)
    return jsonify({"threads": list(reversed(digests))})


@api.get("/customer/messages")
@jwt_required()
@role_required("customer")
def customer_messages():
    user = _current_user()
    messages = (
        Message.query.filter_by(customer_id=user.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    digests = _thread_digests(
        messages,
        lambda message: message.product.shop.display_name
        if message.product and message.product.shop
        else None,
    )
    return jsonify({"threads": list(reversed(digests))})


def _load_product_for_messaging(product_id, user):
    product = db.session.get(Product, product_id)
    if not product:
        raise ApiError("Product not found", 404, "not_found")
    if user.role == "shop":
        if product.shop_id != user.id:
            raise ApiError("Product not found", 404, "not_found")
        return product, "shop"
    if user.role != "customer":
        raise ApiError("Only customers and shops exchange messages", 403, "forbidden")
    return product, "customer"


@api.get("/products/<int:product_id>/messages")
@jwt_required()
def product_messages(product_id):
    user = _current_user()
    product, role = _load_product_for_messaging(product_id, user)
    query = Message.query.filter_by(product_id=product.id)
    if role == "customer":
        query = query.filter_by(customer_id=user.id)
    messages = query.order_by(Message.created_at.asc(), Message.id.asc()).all()
    return jsonify(
        {
            "product": {"id": product.id, "name": product.name},
            "viewer_role": role,
            "messages": [message.to_dict() for message in messages],
        }
    )


@api.post("/products/<int:product_id>/messages")
@jwt_required()
def send_product_message(product_id):
    user = _current_user()
    product, role = _load_product_for_messaging(product_id, user)
    data = _data()
    body = _text(data, "body", 2000)
    customer_id = user.id
    if role == "shop":
        target = data.get("customer_id")
        if isinstance(target, bool) or not isinstance(target, int):
            raise ApiError("customer_id is required to reply in a thread", 422, "validation_error")
        customer_id = target
        started = (
            Message.query.filter_by(
                product_id=product.id, customer_id=customer_id, sender_role="customer"
            ).first()
        )
        if not started:
            raise ApiError("Thread not found", 404, "not_found")
    message = Message(product_id=product.id, customer_id=customer_id, sender_role=role, body=body)
    db.session.add(message)
    _commit()
    return jsonify({"message": message.to_dict()}), 201


@api.get("/shop/dashboard")
@jwt_required()
@role_required("shop")
def shop_dashboard():
    user = _current_user()
    profile = user.shop_profile
    return jsonify(
        {
            "user": user.to_dict(),
            "verification_status": profile.verification_status if profile else "pending_verification",
            "listing_count": Product.query.filter_by(shop_id=user.id).count(),
            "listings": [product.to_dict() for product in Product.query.filter_by(shop_id=user.id).order_by(Product.created_at.desc()).all()],
        }
    )


@api.get("/shop/listings")
@jwt_required()
@role_required("shop")
def shop_listings():
    user = _current_user()
    return jsonify({"listings": [product.to_dict() for product in Product.query.filter_by(shop_id=user.id).order_by(Product.created_at.desc()).all()]})


@api.post("/shop/listings")
@jwt_required()
@role_required("shop")
def create_listing():
    user = _current_user()
    _ensure_can_publish(user)
    data = _data()
    payload = _product_payload(data)
    _verify_image_url(payload["image_url"])
    product = Product(shop_id=user.id, **payload)
    db.session.add(product)
    _commit()
    return jsonify({"product": product.to_dict()}), 201


@api.put("/shop/listings/<int:product_id>")
@jwt_required()
@role_required("shop")
def update_listing(product_id):
    user = _current_user()
    _ensure_can_publish(user)
    product = db.session.get(Product, product_id)
    if not product or product.shop_id != user.id:
        raise ApiError("Listing not found", 404, "not_found")
    data = _data()
    payload = _product_payload(data)
    _verify_image_url(payload["image_url"])
    for key, value in payload.items():
        setattr(product, key, value)
    _commit()
    return jsonify({"product": product.to_dict()})


@api.delete("/shop/listings/<int:product_id>")
@jwt_required()
@role_required("shop")
def delete_listing(product_id):
    user = _current_user()
    _ensure_can_publish(user)
    product = db.session.get(Product, product_id)
    if not product or product.shop_id != user.id:
        raise ApiError("Listing not found", 404, "not_found")
    product.available = False
    _commit()
    return jsonify({"message": "Listing archived"})


@api.get("/admin/dashboard")
@jwt_required()
@role_required("admin")
def admin_dashboard():
    pending = ShopProfile.query.filter_by(verification_status="pending_verification").count()
    return jsonify(
        {
            "user": _current_user().to_dict(),
            "pending_shop_count": pending,
            "user_count": User.query.count(),
            "listing_count": Product.query.filter_by(available=True).count(),
            "category_count": Category.query.filter_by(active=True).count(),
            "region_count": Region.query.filter_by(active=True).count(),
        }
    )


@api.get("/admin/shops")
@jwt_required()
@role_required("admin")
def admin_shops():
    query = ShopProfile.query.join(User).order_by(ShopProfile.id.desc())
    if request.args.get("status"):
        query = query.filter(ShopProfile.verification_status == request.args["status"])
    return jsonify(
        {
            "shops": [
                {
                    "user": profile.user.to_dict(include_profile=False),
                    "profile": profile.to_dict(),
                }
                for profile in query.all()
            ]
        }
    )


@api.post("/admin/shops/<int:user_id>/approve")
@jwt_required()
@role_required("admin")
def approve_shop(user_id):
    profile = ShopProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        raise ApiError("Shop profile not found", 404, "not_found")
    profile.verification_status = "approved"
    profile.verified_at = utc_now()
    profile.user.account_status = "active"
    _commit()
    return jsonify({"shop": profile.user.to_dict(), "message": "Shop approved"})


@api.post("/admin/shops/<int:user_id>/suspend")
@jwt_required()
@role_required("admin")
def suspend_shop(user_id):
    profile = ShopProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        raise ApiError("Shop profile not found", 404, "not_found")
    profile.verification_status = "suspended"
    profile.user.account_status = "suspended"
    _commit()
    return jsonify({"shop": profile.user.to_dict(), "message": "Shop suspended"})


@api.post("/admin/shops/<int:user_id>/restore")
@jwt_required()
@role_required("admin")
def restore_shop(user_id):
    profile = ShopProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        raise ApiError("Shop profile not found", 404, "not_found")
    profile.verification_status = "approved"
    profile.user.account_status = "active"
    _commit()
    return jsonify({"shop": profile.user.to_dict(), "message": "Shop restored"})


@api.get("/admin/users")
@jwt_required()
@role_required("admin")
def admin_users():
    return jsonify({"users": [user.to_dict() for user in User.query.order_by(User.created_at.desc()).all()]})


@api.post("/admin/users/<int:user_id>/suspend")
@jwt_required()
@role_required("admin")
def suspend_user(user_id):
    admin = _current_user()
    if admin.id == user_id:
        raise ApiError("An admin cannot suspend their own account", 422, "validation_error")
    user = db.session.get(User, user_id)
    if not user:
        raise ApiError("User not found", 404, "not_found")
    user.account_status = "suspended"
    _commit()
    return jsonify({"user": user.to_dict(), "message": "User suspended"})


@api.post("/admin/users/<int:user_id>/restore")
@jwt_required()
@role_required("admin")
def restore_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise ApiError("User not found", 404, "not_found")
    user.account_status = "active"
    _commit()
    return jsonify({"user": user.to_dict(), "message": "User restored"})


@api.get("/admin/categories")
@jwt_required()
@role_required("admin")
def admin_categories():
    return jsonify({"categories": [category.to_dict() for category in Category.query.order_by(Category.name).all()]})


@api.post("/admin/categories")
@jwt_required()
@role_required("admin")
def create_category():
    data = _data()
    name = _text(data, "name", 80)
    if name not in ALLOWED_CATEGORIES:
        raise ApiError("Category is outside the agricultural catalog", 422, "invalid_category")
    category = Category.query.filter_by(name=name).first()
    if category:
        category.active = True
    else:
        category = Category(name=name)
        db.session.add(category)
    _commit()
    return jsonify({"category": category.to_dict()}), 201


@api.delete("/admin/categories/<int:category_id>")
@jwt_required()
@role_required("admin")
def archive_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        raise ApiError("Category not found", 404, "not_found")
    category.active = False
    _commit()
    return jsonify({"message": "Category archived"})


@api.get("/admin/regions")
@jwt_required()
@role_required("admin")
def admin_regions():
    return jsonify({"regions": [region.to_dict() for region in Region.query.order_by(Region.name).all()]})


@api.post("/admin/regions")
@jwt_required()
@role_required("admin")
def create_region():
    data = _data()
    name = _text(data, "name", 120)
    if len(name) < 2:
        raise ApiError("Region name is too short", 422, "validation_error")
    region = Region.query.filter_by(name=name).first()
    if region:
        region.active = True
    else:
        region = Region(name=name)
        db.session.add(region)
    _commit()
    return jsonify({"region": region.to_dict()}), 201


@api.delete("/admin/regions/<int:region_id>")
@jwt_required()
@role_required("admin")
def archive_region(region_id):
    region = db.session.get(Region, region_id)
    if not region:
        raise ApiError("Region not found", 404, "not_found")
    region.active = False
    _commit()
    return jsonify({"message": "Region archived"})