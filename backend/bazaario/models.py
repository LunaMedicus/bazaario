from datetime import datetime
from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


ALLOWED_ROLES = ("customer", "farmer", "admin")
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
ORDER_STATUSES = ("placed", "confirmed", "harvested", "in_transit", "delivered")


def utc_now():
    return datetime.utcnow()


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(
            "role IN ('customer', 'farmer', 'admin')",
            name="ck_users_role",
        ),
        db.CheckConstraint(
            "account_status IN ('active', 'suspended')",
            name="ck_users_account_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), nullable=False, default="Bazaario user")
    role = db.Column(db.String(20), nullable=False)
    account_status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    farmer_profile = db.relationship(
        "FarmerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    products = db.relationship("Product", back_populates="farmer")
    customer_orders = db.relationship(
        "Order", back_populates="customer", foreign_keys="Order.customer_id"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_profile=True):
        payload = {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role,
            "account_status": self.account_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_profile and self.role == "farmer" and self.farmer_profile:
            payload["farmer_profile"] = self.farmer_profile.to_dict()
        return payload


class FarmerProfile(db.Model):
    __tablename__ = "farmer_profiles"
    __table_args__ = (
        db.CheckConstraint(
            "verification_status IN ('pending_verification', 'approved', 'suspended')",
            name="ck_farmer_profiles_verification_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    farm_name = db.Column(db.String(160), nullable=False)
    region = db.Column(db.String(120), nullable=False)
    document_reference = db.Column(db.String(255), nullable=False)
    verification_status = db.Column(
        db.String(30), nullable=False, default="pending_verification"
    )
    verified_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="farmer_profile")

    def to_dict(self):
        return {
            "id": self.id,
            "farm_name": self.farm_name,
            "region": self.region,
            "document_reference": self.document_reference,
            "verification_status": self.verification_status,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "active": self.active}


class Region(db.Model):
    __tablename__ = "regions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "active": self.active}


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.CheckConstraint(
            "category IN ('Fruit', 'Vegetables', 'Grains', 'Dairy', 'Honey & bee products', 'Herbs', 'Nuts', 'Tea')",
            name="ck_products_agricultural_category",
        ),
        db.CheckConstraint("price_azn >= 0", name="ck_products_non_negative_price"),
        db.CheckConstraint("stock >= 0", name="ck_products_non_negative_stock"),
    )

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    price_azn = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    season = db.Column(db.String(120), nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    available = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    farmer = db.relationship("User", back_populates="products")
    order_items = db.relationship("OrderItem", back_populates="product")
    reviews = db.relationship("Review", back_populates="product")

    def to_dict(self):
        profile = self.farmer.farmer_profile if self.farmer else None
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price_azn": float(self.price_azn or Decimal("0")),
            "stock": self.stock,
            "season": self.season,
            "image_url": self.image_url,
            "description": self.description,
            "available": self.available,
            "region": profile.region if profile else None,
            "farm": {
                "id": self.farmer_id,
                "name": profile.farm_name if profile else self.farmer.display_name,
                "region": profile.region if profile else None,
            },
            "rating": round(
                sum(review.rating for review in self.reviews) / len(self.reviews), 1
            )
            if self.reviews
            else None,
            "review_count": len(self.reviews),
        }


class Order(db.Model):
    __tablename__ = "orders"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('placed', 'confirmed', 'harvested', 'in_transit', 'delivered')",
            name="ck_orders_status",
        ),
        db.CheckConstraint("total_azn >= 0", name="ck_orders_non_negative_total"),
        db.CheckConstraint(
            "payment_method IN ('cash_on_delivery', 'card_sandbox')",
            name="ck_orders_payment_method",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="placed", index=True)
    total_azn = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_address = db.Column(db.String(255), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    payment_status = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    customer = db.relationship(
        "User", back_populates="customer_orders", foreign_keys=[customer_id]
    )
    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    audits = db.relationship(
        "OrderAudit", back_populates="order", cascade="all, delete-orphan", order_by="OrderAudit.id"
    )
    reviews = db.relationship(
        "Review", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_order_items_positive_quantity"),
        db.CheckConstraint("unit_price_azn >= 0", name="ck_order_items_non_negative_price"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_azn = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")


class OrderAudit(db.Model):
    __tablename__ = "order_audits"
    __table_args__ = (
        db.UniqueConstraint("order_id", "to_status", name="uq_order_audit_transition"),
        db.CheckConstraint(
            "to_status IN ('placed', 'confirmed', 'harvested', 'in_transit', 'delivered')",
            name="ck_order_audits_to_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    actor_role = db.Column(db.String(20), nullable=False)
    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    order = db.relationship("Order", back_populates="audits")
    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (
        db.UniqueConstraint("order_id", "product_id", name="uq_review_order_product"),
        db.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    order = db.relationship("Order", back_populates="reviews")
    product = db.relationship("Product", back_populates="reviews")
    customer = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "customer": self.customer.display_name if self.customer else None,
            "rating": self.rating,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DisputeFlag(db.Model):
    __tablename__ = "dispute_flags"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('open', 'resolved')",
            name="ck_dispute_flags_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    raised_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    resolved_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship("Order")
    raised_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "raised_by": self.raised_by.display_name if self.raised_by else None,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
