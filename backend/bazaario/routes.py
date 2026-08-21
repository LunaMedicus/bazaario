from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import or_

from .extensions import db
from .models import (
    ALLOWED_CATEGORIES,
    ALLOWED_ROLES,
    ORDER_STATUSES,
    Category,
    DisputeFlag,
    FarmerProfile,
    Order,
    OrderAudit,
    OrderItem,
    Product,
    Region,
    Review,
    User,
    utc_now,
)


api = Blueprint("api", __name__)
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
    return request.get_json(silent=True) or {}


def _required(data, *fields):
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ApiError(f"Missing required field(s): {', '.join(missing)}", 422, "validation_error")


def _current_user():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        raise ApiError("User no longer exists", 401, "unauthorized")
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
            if user.account_status == "suspended":
                return jsonify(_error_payload("Account is suspended", "account_suspended")), 403
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
    _required(data, "email", "password", "display_name")
    email = _normal_email(data["email"])
    if "@" not in email or len(data["password"]) < 8:
        raise ApiError("Use a valid email and a password of at least 8 characters", 422, "validation_error")
    if User.query.filter_by(email=email).first():
        raise ApiError("An account with this email already exists", 409, "email_exists")
    user = User(email=email, display_name=str(data["display_name"]).strip(), role=role)
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()
    return user


def _product_payload(data):
    _required(data, "name", "category", "price_azn", "stock", "season", "image_url")
    category = str(data["category"]).strip()
    if category not in ALLOWED_CATEGORIES:
        raise ApiError(
            "Only agricultural categories are allowed",
            422,
            "invalid_category",
        )
    try:
        price = Decimal(str(data["price_azn"]))
    except (InvalidOperation, TypeError):
        raise ApiError("price_azn must be a number", 422, "validation_error")
    try:
        stock = int(data["stock"])
    except (TypeError, ValueError):
        raise ApiError("stock must be a whole number", 422, "validation_error")
    image_url = str(data["image_url"]).strip()
    parsed = urlparse(image_url)
    if price < 0 or stock < 0:
        raise ApiError("Price and stock cannot be negative", 422, "validation_error")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ApiError("image_url must be an http(s) URL", 422, "validation_error")
    if (parsed.hostname or "").lower() not in IMAGE_SOURCE_HOSTS:
        raise ApiError(
            "Use a hotlinkable Unsplash, Pexels, or Wikimedia Commons image",
            422,
            "image_source_not_allowed",
        )
    return {
        "name": str(data["name"]).strip(),
        "category": category,
        "price_azn": price.quantize(Decimal("0.01")),
        "stock": stock,
        "season": str(data["season"]).strip(),
        "image_url": image_url,
        "description": str(data.get("description", "")).strip(),
    }


def _ensure_can_publish(user):
    profile = user.farmer_profile
    if not profile or profile.verification_status != "approved":
        raise ApiError(
            "Your farm must be approved before publishing listings",
            403,
            "farmer_verification_required",
        )


def _order_dict(order):
    return {
        "id": order.id,
        "status": order.status,
        "total_azn": float(order.total_azn or Decimal("0")),
        "delivery_address": order.delivery_address,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "customer": {
            "id": order.customer.id,
            "name": order.customer.display_name,
            "email": order.customer.email,
        }
        if order.customer
        else None,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": item.product.name,
                "quantity": item.quantity,
                "unit_price_azn": float(item.unit_price_azn or Decimal("0")),
                "line_total_azn": float(
                    (item.unit_price_azn or Decimal("0")) * item.quantity
                ),
                "farmer_id": item.product.farmer_id,
                "farm_name": item.product.farmer.farmer_profile.farm_name
                if item.product.farmer and item.product.farmer.farmer_profile
                else None,
            }
            for item in order.items
        ],
        "audit": [audit.to_dict() for audit in order.audits],
        "reviews": [review.to_dict() for review in order.reviews],
    }


def _farmer_order_query(user_id):
    return (
        Order.query.join(OrderItem)
        .join(Product)
        .filter(Product.farmer_id == user_id)
        .distinct()
        .order_by(Order.created_at.desc())
    )


def _farmer_owns_order(order, user_id):
    return any(item.product.farmer_id == user_id for item in order.items)


def _transition(order, target, actor):
    if target not in ORDER_STATUSES:
        raise ApiError("Unknown order status", 422, "validation_error")
    target_index = ORDER_STATUSES.index(target)
    expected_from = ORDER_STATUSES[target_index - 1] if target_index else None
    if order.status != expected_from:
        raise ApiError(
            f"Order must be {expected_from or 'new'} before it can become {target}",
            409,
            "invalid_transition",
        )
    previous = order.status
    order.status = target
    order.updated_at = utc_now()
    db.session.add(
        OrderAudit(
            order=order,
            actor_id=actor.id,
            actor_role=actor.role,
            from_status=previous,
            to_status=target,
        )
    )


def _commit():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


@api.post("/auth/register/customer")
def register_customer():
    user = _create_user(_data(), "customer")
    _commit()
    return jsonify({"user": user.to_dict(), "message": "Customer account created"}), 201


@api.post("/auth/register/farmer")
def register_farmer():
    data = _data()
    _required(data, "farm_name", "region", "document_reference")
    user = _create_user(data, "farmer")
    profile = FarmerProfile(
        user_id=user.id,
        farm_name=str(data["farm_name"]).strip(),
        region=str(data["region"]).strip(),
        document_reference=str(data["document_reference"]).strip(),
        verification_status="pending_verification",
    )
    db.session.add(profile)
    _commit()
    return jsonify({"user": user.to_dict(), "message": "Farmer application submitted"}), 201


@api.post("/auth/login")
def login():
    data = _data()
    _required(data, "email", "password")
    user = User.query.filter_by(email=_normal_email(data["email"])).first()
    if not user or not user.check_password(data["password"]):
        raise ApiError("Invalid email or password", 401, "invalid_credentials")
    if user.account_status == "suspended":
        raise ApiError("Account is suspended", 403, "account_suspended")
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
    query = Product.query.join(User).join(FarmerProfile).filter(Product.available.is_(True), Product.stock > 0)
    category = request.args.get("category")
    if category:
        if category not in ALLOWED_CATEGORIES:
            raise ApiError("Only agricultural categories are allowed", 422, "invalid_category")
        query = query.filter(Product.category == category)
    if request.args.get("region"):
        query = query.filter(FarmerProfile.region == request.args["region"])
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
    product = db.session.get(Product, product_id)
    if not product or not product.available:
        raise ApiError("Product not found", 404, "not_found")
    payload = product.to_dict()
    payload["reviews"] = [review.to_dict() for review in product.reviews]
    return jsonify({"product": payload})


@api.get("/customer/dashboard")
@jwt_required()
@role_required("customer")
def customer_dashboard():
    user = _current_user()
    recent = Order.query.filter_by(customer_id=user.id).order_by(Order.created_at.desc()).limit(5).all()
    return jsonify(
        {
            "user": user.to_dict(),
            "order_count": Order.query.filter_by(customer_id=user.id).count(),
            "recent_orders": [_order_dict(order) for order in recent],
            "catalog_count": Product.query.filter_by(available=True).count(),
        }
    )


@api.get("/customer/orders")
@jwt_required()
@role_required("customer")
def customer_orders():
    user = _current_user()
    orders = Order.query.filter_by(customer_id=user.id).order_by(Order.created_at.desc()).all()
    return jsonify({"orders": [_order_dict(order) for order in orders]})


@api.post("/customer/orders")
@jwt_required()
@role_required("customer")
def create_order():
    user = _current_user()
    data = _data()
    _required(data, "items", "delivery_address", "payment_method")
    if not isinstance(data["items"], list) or not data["items"]:
        raise ApiError("At least one basket item is required", 422, "validation_error")
    if data["payment_method"] not in {"cash_on_delivery", "card_sandbox"}:
        raise ApiError("Choose cash_on_delivery or card_sandbox", 422, "validation_error")
    quantities = {}
    for item in data["items"]:
        try:
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])
        except (KeyError, TypeError, ValueError):
            raise ApiError("Each item needs a product_id and whole-number quantity", 422, "validation_error")
        if quantity < 1:
            raise ApiError("Item quantities must be at least one", 422, "validation_error")
        quantities[product_id] = quantities.get(product_id, 0) + quantity

    products_by_id = {
        product.id: product
        for product in Product.query.filter(Product.id.in_(quantities.keys())).all()
    }
    if len(products_by_id) != len(quantities):
        raise ApiError("One or more products were not found", 404, "product_not_found")
    if len({product.farmer_id for product in products_by_id.values()}) > 1:
        raise ApiError(
            "A checkout must contain products from one farm",
            422,
            "multiple_farms",
        )
    total = Decimal("0")
    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        if not product.available or product.stock < quantity:
            raise ApiError(f"{product.name} does not have enough stock", 409, "stock_unavailable")
        total += Decimal(product.price_azn) * quantity

    order = Order(
        customer_id=user.id,
        status="placed",
        total_azn=total.quantize(Decimal("0.01")),
        delivery_address=str(data["delivery_address"]).strip(),
        payment_method=data["payment_method"],
        payment_status="sandbox_approved" if data["payment_method"] == "card_sandbox" else "cash_due",
    )
    db.session.add(order)
    db.session.flush()
    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        product.stock -= quantity
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price_azn=product.price_azn,
            )
        )
    db.session.add(
        OrderAudit(
            order_id=order.id,
            actor_id=user.id,
            actor_role=user.role,
            from_status=None,
            to_status="placed",
        )
    )
    _commit()
    return jsonify({"order": _order_dict(order), "message": "Order placed"}), 201


@api.get("/customer/orders/<int:order_id>")
@jwt_required()
@role_required("customer")
def customer_order_detail(order_id):
    order = db.session.get(Order, order_id)
    user = _current_user()
    if not order or order.customer_id != user.id:
        raise ApiError("Order not found", 404, "not_found")
    return jsonify({"order": _order_dict(order)})


@api.post("/customer/orders/<int:order_id>/delivered")
@jwt_required()
@role_required("customer")
def mark_delivered(order_id):
    user = _current_user()
    order = db.session.get(Order, order_id)
    if not order or order.customer_id != user.id:
        raise ApiError("Order not found", 404, "not_found")
    _transition(order, "delivered", user)
    _commit()
    return jsonify({"order": _order_dict(order), "message": "Delivery confirmed"})


@api.post("/customer/orders/<int:order_id>/reviews")
@jwt_required()
@role_required("customer")
def create_review(order_id):
    user = _current_user()
    order = db.session.get(Order, order_id)
    if not order or order.customer_id != user.id:
        raise ApiError("Order not found", 404, "not_found")
    if order.status != "delivered":
        raise ApiError("Reviews unlock after delivery", 409, "review_locked")
    data = _data()
    _required(data, "product_id", "rating")
    try:
        product_id = int(data["product_id"])
        rating = int(data["rating"])
    except (TypeError, ValueError):
        raise ApiError("product_id and rating must be integers", 422, "validation_error")
    if rating < 1 or rating > 5:
        raise ApiError("rating must be between 1 and 5", 422, "validation_error")
    if not any(item.product_id == product_id for item in order.items):
        raise ApiError("You can only review products from this order", 403, "forbidden")
    if Review.query.filter_by(order_id=order.id, product_id=product_id).first():
        raise ApiError("This product has already been reviewed", 409, "review_exists")
    review = Review(
        order_id=order.id,
        product_id=product_id,
        customer_id=user.id,
        rating=rating,
        body=str(data.get("body", "")).strip(),
    )
    db.session.add(review)
    _commit()
    return jsonify({"review": review.to_dict()}), 201


@api.post("/customer/orders/<int:order_id>/dispute")
@jwt_required()
@role_required("customer")
def create_dispute(order_id):
    user = _current_user()
    order = db.session.get(Order, order_id)
    if not order or order.customer_id != user.id:
        raise ApiError("Order not found", 404, "not_found")
    data = _data()
    _required(data, "reason")
    flag = DisputeFlag(order_id=order.id, raised_by_id=user.id, reason=str(data["reason"]).strip())
    db.session.add(flag)
    _commit()
    return jsonify({"dispute": flag.to_dict()}), 201


@api.get("/farmer/dashboard")
@jwt_required()
@role_required("farmer")
def farmer_dashboard():
    user = _current_user()
    profile = user.farmer_profile
    orders = _farmer_order_query(user.id).all()
    earnings = sum(
        item.unit_price_azn * item.quantity
        for order in orders
        if order.status == "delivered"
        for item in order.items
        if item.product.farmer_id == user.id
    )
    return jsonify(
        {
            "user": user.to_dict(),
            "verification_status": profile.verification_status if profile else "pending_verification",
            "listing_count": Product.query.filter_by(farmer_id=user.id).count(),
            "incoming_order_count": len(orders),
            "pending_order_count": sum(order.status == "placed" for order in orders),
            "earnings_azn": float(earnings or Decimal("0")),
            "listings": [product.to_dict() for product in Product.query.filter_by(farmer_id=user.id).order_by(Product.created_at.desc()).all()],
        }
    )


@api.get("/farmer/listings")
@jwt_required()
@role_required("farmer")
def farmer_listings():
    user = _current_user()
    return jsonify({"listings": [product.to_dict() for product in Product.query.filter_by(farmer_id=user.id).order_by(Product.created_at.desc()).all()]})


@api.post("/farmer/listings")
@jwt_required()
@role_required("farmer")
def create_listing():
    user = _current_user()
    data = _data()
    payload = _product_payload(data)
    _ensure_can_publish(user)
    product = Product(farmer_id=user.id, **payload)
    db.session.add(product)
    _commit()
    return jsonify({"product": product.to_dict()}), 201


@api.put("/farmer/listings/<int:product_id>")
@jwt_required()
@role_required("farmer")
def update_listing(product_id):
    user = _current_user()
    data = _data()
    payload = _product_payload(data)
    _ensure_can_publish(user)
    product = db.session.get(Product, product_id)
    if not product or product.farmer_id != user.id:
        raise ApiError("Listing not found", 404, "not_found")
    for key, value in payload.items():
        setattr(product, key, value)
    _commit()
    return jsonify({"product": product.to_dict()})


@api.delete("/farmer/listings/<int:product_id>")
@jwt_required()
@role_required("farmer")
def delete_listing(product_id):
    user = _current_user()
    _ensure_can_publish(user)
    product = db.session.get(Product, product_id)
    if not product or product.farmer_id != user.id:
        raise ApiError("Listing not found", 404, "not_found")
    product.available = False
    _commit()
    return jsonify({"message": "Listing archived"})


@api.get("/farmer/orders")
@jwt_required()
@role_required("farmer")
def farmer_orders():
    user = _current_user()
    return jsonify({"orders": [_order_dict(order) for order in _farmer_order_query(user.id).all()]})


@api.post("/farmer/orders/<int:order_id>/confirm")
@jwt_required()
@role_required("farmer")
def farmer_confirm(order_id):
    user = _current_user()
    order = db.session.get(Order, order_id)
    if not order or not _farmer_owns_order(order, user.id):
        raise ApiError("Order not found", 404, "not_found")
    _transition(order, "confirmed", user)
    _commit()
    return jsonify({"order": _order_dict(order), "message": "Order confirmed"})


@api.post("/farmer/orders/<int:order_id>/harvested")
@jwt_required()
@role_required("farmer")
def farmer_harvested(order_id):
    user = _current_user()
    order = db.session.get(Order, order_id)
    if not order or not _farmer_owns_order(order, user.id):
        raise ApiError("Order not found", 404, "not_found")
    _transition(order, "harvested", user)
    _commit()
    return jsonify({"order": _order_dict(order), "message": "Harvest marked complete"})


@api.get("/admin/dashboard")
@jwt_required()
@role_required("admin")
def admin_dashboard():
    pending = FarmerProfile.query.filter_by(verification_status="pending_verification").count()
    return jsonify(
        {
            "user": _current_user().to_dict(),
            "pending_farmer_count": pending,
            "user_count": User.query.count(),
            "order_count": Order.query.count(),
            "open_dispute_count": DisputeFlag.query.filter_by(status="open").count(),
            "category_count": Category.query.filter_by(active=True).count(),
            "region_count": Region.query.filter_by(active=True).count(),
        }
    )


@api.get("/admin/farmers")
@jwt_required()
@role_required("admin")
def admin_farmers():
    query = FarmerProfile.query.join(User).order_by(FarmerProfile.id.desc())
    if request.args.get("status"):
        query = query.filter(FarmerProfile.verification_status == request.args["status"])
    return jsonify(
        {
            "farmers": [
                {
                    "user": profile.user.to_dict(include_profile=False),
                    "profile": profile.to_dict(),
                }
                for profile in query.all()
            ]
        }
    )


@api.post("/admin/farmers/<int:user_id>/approve")
@jwt_required()
@role_required("admin")
def approve_farmer(user_id):
    profile = FarmerProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        raise ApiError("Farmer profile not found", 404, "not_found")
    profile.verification_status = "approved"
    profile.verified_at = utc_now()
    profile.user.account_status = "active"
    _commit()
    return jsonify({"farmer": profile.user.to_dict(), "message": "Farmer approved"})


@api.post("/admin/farmers/<int:user_id>/suspend")
@jwt_required()
@role_required("admin")
def suspend_farmer(user_id):
    profile = FarmerProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        raise ApiError("Farmer profile not found", 404, "not_found")
    profile.verification_status = "suspended"
    profile.user.account_status = "suspended"
    _commit()
    return jsonify({"farmer": profile.user.to_dict(), "message": "Farmer suspended"})


@api.post("/admin/farmers/<int:user_id>/restore")
@jwt_required()
@role_required("admin")
def restore_farmer(user_id):
    profile = FarmerProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        raise ApiError("Farmer profile not found", 404, "not_found")
    profile.verification_status = "approved"
    profile.user.account_status = "active"
    _commit()
    return jsonify({"farmer": profile.user.to_dict(), "message": "Farmer restored"})


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
    _required(data, "name")
    name = str(data["name"]).strip()
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
    _required(data, "name")
    name = str(data["name"]).strip()
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


@api.get("/admin/orders")
@jwt_required()
@role_required("admin")
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify({"orders": [_order_dict(order) for order in orders]})


@api.post("/admin/orders/<int:order_id>/in-transit")
@jwt_required()
@role_required("admin")
def admin_in_transit(order_id):
    user = _current_user()
    order = db.session.get(Order, order_id)
    if not order:
        raise ApiError("Order not found", 404, "not_found")
    _transition(order, "in_transit", user)
    _commit()
    return jsonify({"order": _order_dict(order), "message": "Order marked in transit"})


@api.get("/admin/disputes")
@jwt_required()
@role_required("admin")
def admin_disputes():
    disputes = DisputeFlag.query.order_by(DisputeFlag.created_at.desc()).all()
    return jsonify({"disputes": [flag.to_dict() for flag in disputes]})


@api.post("/admin/disputes/<int:dispute_id>/resolve")
@jwt_required()
@role_required("admin")
def resolve_dispute(dispute_id):
    flag = db.session.get(DisputeFlag, dispute_id)
    if not flag:
        raise ApiError("Dispute not found", 404, "not_found")
    flag.status = "resolved"
    flag.resolved_at = utc_now()
    _commit()
    return jsonify({"dispute": flag.to_dict()})
