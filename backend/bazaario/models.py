from datetime import datetime
from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


ALLOWED_ROLES = ("customer", "shop", "admin")


def utc_now():
    return datetime.utcnow()


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(
            "role IN ('customer', 'shop', 'admin')",
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

    shop_profile = db.relationship(
        "ShopProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    products = db.relationship("Product", back_populates="shop")

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
        if include_profile and self.role == "shop" and self.shop_profile:
            payload["shop_profile"] = self.shop_profile.to_dict()
        return payload


class ShopProfile(db.Model):
    __tablename__ = "shop_profiles"
    __table_args__ = (
        db.CheckConstraint(
            "verification_status IN ('pending_verification', 'approved', 'suspended')",
            name="ck_shop_profiles_verification_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    shop_name = db.Column(db.String(160), nullable=False)
    region = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    verification_status = db.Column(
        db.String(30), nullable=False, default="pending_verification"
    )
    verified_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="shop_profile")

    def to_dict(self):
        return {
            "id": self.id,
            "shop_name": self.shop_name,
            "region": self.region,
            "phone": self.phone,
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
    shop_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    price_azn = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    season = db.Column(db.String(120), nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    available = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    shop = db.relationship("User", back_populates="products")
    reviews = db.relationship(
        "Review", back_populates="product", cascade="all, delete-orphan"
    )

    def to_dict(self):
        profile = self.shop.shop_profile if self.shop else None
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
            "shop": {
                "id": self.shop_id,
                "name": profile.shop_name if profile else self.shop.display_name,
                "region": profile.region if profile else None,
                "phone": profile.phone if profile else None,
            },
            "rating": round(
                sum(review.rating for review in self.reviews) / len(self.reviews), 1
            )
            if self.reviews
            else None,
            "review_count": len(self.reviews),
        }


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (
        db.UniqueConstraint("product_id", "customer_id", name="uq_review_product_customer"),
        db.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    product = db.relationship("Product", back_populates="reviews")
    customer = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "customer": self.customer.display_name if self.customer else None,
            "rating": self.rating,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Message(db.Model):
    __tablename__ = "messages"
    __table_args__ = (
        db.Index("ix_messages_thread", "product_id", "customer_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    sender_role = db.Column(
        db.String(20), nullable=False
    )  # "customer" or "shop"; shop identity = product.shop_id
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    product = db.relationship("Product")
    customer = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "customer_id": self.customer_id,
            "sender_role": self.sender_role,
            "sender": (
                self.customer.display_name
                if self.sender_role == "customer" and self.customer
                else (self.product.shop.display_name if self.product and self.product.shop else None)
            ),
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
