"""OpenAPI 3.0 description of the Bazaario REST API.

The document is built in Python rather than checked in as YAML so the
category allow-list, role names and error codes stay in step with the
values the routes actually enforce. `GET /api/openapi.json` serves it and
`GET /api/docs` renders it with Swagger UI.
"""

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

SEASONS = ("Spring", "Summer", "Autumn", "Winter", "All year")


def _error(description):
    return {
        "description": description,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/Error"}}
        },
    }


def _json(ref, description="Success"):
    return {
        "description": description,
        "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{ref}"}}},
    }


def _body(ref, required=True):
    return {
        "required": required,
        "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{ref}"}}},
    }


SCHEMAS = {
    "Error": {
        "type": "object",
        "properties": {
            "error": {"type": "string", "example": "forbidden"},
            "code": {
                "type": "string",
                "description": "Stable machine-readable reason. Absent on generic errors.",
                "example": "shop_verification_required",
            },
            "message": {"type": "string"},
        },
        "required": ["error"],
    },
    "Message": {
        "type": "object",
        "properties": {"message": {"type": "string"}},
    },
    "User": {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "example": 3},
            "email": {"type": "string", "format": "email"},
            "display_name": {"type": "string"},
            "role": {"type": "string", "enum": ["customer", "shop", "admin"]},
            "account_status": {"type": "string", "enum": ["active", "suspended"]},
            "created_at": {"type": "string", "format": "date-time"},
            "shop_profile": {"$ref": "#/components/schemas/ShopProfile"},
        },
    },
    "ShopProfile": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "shop_name": {"type": "string", "example": "Goychay Orchard Cooperative"},
            "region": {"type": "string", "example": "Goychay"},
            "phone": {"type": "string", "nullable": True, "example": "+994 22 216 01 45"},
            "verification_status": {
                "type": "string",
                "enum": ["pending_verification", "approved", "suspended"],
            },
            "verified_at": {"type": "string", "format": "date-time", "nullable": True},
        },
    },
    "Product": {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "example": 12},
            "name": {"type": "string", "example": "Goychay Red Apples"},
            "category": {"type": "string", "enum": list(ALLOWED_CATEGORIES)},
            "price_azn": {"type": "number", "format": "double", "example": 4.8},
            "stock": {"type": "integer", "example": 80},
            "season": {"type": "string", "example": "August-October"},
            "image_url": {"type": "string", "format": "uri"},
            "description": {"type": "string"},
            "available": {"type": "boolean"},
            "region": {"type": "string", "nullable": True},
            "shop": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "region": {"type": "string", "nullable": True},
                    "phone": {"type": "string", "nullable": True},
                },
            },
            "rating": {
                "type": "number",
                "nullable": True,
                "description": "Mean of all review ratings, one decimal. Null with no reviews.",
                "example": 4.5,
            },
            "review_count": {"type": "integer", "example": 2},
        },
    },
    "ProductDetail": {
        "allOf": [
            {"$ref": "#/components/schemas/Product"},
            {
                "type": "object",
                "properties": {
                    "reviews": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Review"},
                    }
                },
            },
        ]
    },
    "Review": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "product_id": {"type": "integer"},
            "customer_id": {
                "type": "integer",
                "description": "Author id. Compare with the signed-in user to find your own review.",
            },
            "customer": {"type": "string", "nullable": True, "description": "Author display name."},
            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
            "body": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
        },
    },
    "ChatMessage": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "product_id": {"type": "integer"},
            "product_name": {"type": "string", "nullable": True},
            "customer_id": {"type": "integer"},
            "sender_role": {"type": "string", "enum": ["customer", "shop"]},
            "sender": {"type": "string", "nullable": True},
            "body": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
        },
    },
    "ThreadDigest": {
        "type": "object",
        "description": "One conversation, keyed by product and customer, newest first.",
        "properties": {
            "product_id": {"type": "integer"},
            "product_name": {"type": "string", "nullable": True},
            "customer_id": {"type": "integer"},
            "customer_name": {"type": "string", "nullable": True},
            "shop_name": {"type": "string", "nullable": True},
            "message_count": {"type": "integer"},
            "last_body": {"type": "string", "nullable": True},
            "last_sender_role": {"type": "string", "nullable": True},
            "last_created_at": {"type": "string", "format": "date-time", "nullable": True},
        },
    },
    "Taxonomy": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "active": {"type": "boolean"},
        },
    },
    "AuthResponse": {
        "type": "object",
        "properties": {
            "access_token": {
                "type": "string",
                "description": "HS256 JWT carrying `role` and `account_status` claims.",
            },
            "user": {"$ref": "#/components/schemas/User"},
        },
    },
    "LoginRequest": {
        "type": "object",
        "required": ["email", "password"],
        "properties": {
            "email": {"type": "string", "format": "email", "example": "customer@bazaario.az"},
            "password": {"type": "string", "format": "password", "example": "CustomerDemo!2026"},
        },
    },
    "CustomerRegistration": {
        "type": "object",
        "required": ["display_name", "email", "password"],
        "properties": {
            "display_name": {"type": "string", "maxLength": 120, "example": "Aysel Mammadova"},
            "email": {"type": "string", "format": "email", "maxLength": 255},
            "password": {"type": "string", "format": "password", "minLength": 8},
        },
    },
    "ShopRegistration": {
        "type": "object",
        "required": ["display_name", "email", "password", "shop_name", "region"],
        "properties": {
            "display_name": {"type": "string", "maxLength": 120},
            "email": {"type": "string", "format": "email", "maxLength": 255},
            "password": {"type": "string", "format": "password", "minLength": 8},
            "shop_name": {"type": "string", "maxLength": 160, "example": "Qabala Highland Garden"},
            "region": {"type": "string", "maxLength": 120, "example": "Qabala"},
            "phone": {
                "type": "string",
                "nullable": True,
                "description": "Optional. Digits, +, spaces, parentheses and hyphens; at least 4 digits.",
                "example": "+994 24 218 03 67",
            },
        },
    },
    "ListingRequest": {
        "type": "object",
        "required": ["name", "category", "price_azn", "stock", "season", "image_url"],
        "properties": {
            "name": {"type": "string", "maxLength": 180, "example": "Goychay Red Apples"},
            "category": {"type": "string", "enum": list(ALLOWED_CATEGORIES)},
            "price_azn": {"type": "number", "minimum": 0, "maximum": 99999999.99, "example": 4.8},
            "stock": {"type": "integer", "minimum": 0, "example": 80},
            "season": {"type": "string", "maxLength": 120, "example": "August-October"},
            "image_url": {
                "type": "string",
                "format": "uri",
                "description": (
                    "Must be hosted on images.unsplash.com, images.pexels.com or "
                    "upload.wikimedia.org, and must answer HTTP 200 with an image/* "
                    "content type under 10 MB."
                ),
            },
            "description": {"type": "string", "nullable": True},
        },
    },
    "ReviewRequest": {
        "type": "object",
        "required": ["rating"],
        "properties": {
            "rating": {"type": "integer", "minimum": 1, "maximum": 5, "example": 5},
            "body": {"type": "string", "nullable": True, "example": "Very fresh, picked the same week."},
        },
    },
    "MessageRequest": {
        "type": "object",
        "required": ["body"],
        "properties": {
            "body": {"type": "string", "maxLength": 2000},
            "customer_id": {
                "type": "integer",
                "description": "Shops only: the customer whose thread is being answered.",
            },
        },
    },
    "PhoneRequest": {
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "nullable": True,
                "description": "Blank or null clears the number.",
                "example": "+994 22 216 01 45",
            }
        },
    },
    "TaxonomyRequest": {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
    },
}


def _tagged(tag, summary, *, security=True, **extra):
    operation = {"tags": [tag], "summary": summary}
    if security:
        operation["security"] = [{"bearerAuth": []}]
    operation.update(extra)
    return operation


def build_spec(server_url="/"):
    unauthorized = _error("Missing, malformed or expired token.")
    forbidden = _error("The token's role may not call this route, or the account is suspended.")
    not_found = _error("The resource does not exist or is not visible to this caller.")
    validation = _error("The payload failed validation. `code` names the specific rule.")

    paths = {
        "/api/auth/register/customer": {
            "post": _tagged(
                "Authentication",
                "Register a customer account",
                security=False,
                description="Open self-service signup. Admin accounts have no public route; only `seed.py` creates them.",
                requestBody=_body("CustomerRegistration"),
                responses={
                    "201": _json("User", "Account created."),
                    "409": _error("An account already uses this email."),
                    "422": validation,
                },
            )
        },
        "/api/auth/register/shop": {
            "post": _tagged(
                "Authentication",
                "Apply for a shop account",
                security=False,
                description=(
                    "Creates the user and a ShopProfile in `pending_verification`. "
                    "Listings stay blocked until an admin approves the profile."
                ),
                requestBody=_body("ShopRegistration"),
                responses={
                    "201": _json("User", "Application submitted."),
                    "409": _error("An account already uses this email."),
                    "422": validation,
                },
            )
        },
        "/api/auth/login": {
            "post": _tagged(
                "Authentication",
                "Exchange credentials for a JWT",
                security=False,
                requestBody=_body("LoginRequest"),
                responses={
                    "200": _json("AuthResponse", "Signed in."),
                    "401": _error("Invalid email or password."),
                    "403": _error("The account is suspended."),
                },
            )
        },
        "/api/auth/me": {
            "get": _tagged(
                "Authentication",
                "Read the signed-in user",
                responses={"200": _json("User"), "401": unauthorized, "403": forbidden},
            )
        },
        "/api/meta": {
            "get": _tagged(
                "Catalog",
                "List active categories, regions and seasons",
                security=False,
                description="Drives the catalog filters. Cached publicly for 60 seconds.",
                responses={"200": {"description": "Filter vocabulary."}},
            )
        },
        "/api/products": {
            "get": _tagged(
                "Catalog",
                "Search the public catalog",
                security=False,
                description=(
                    "Returns in-stock listings from approved, active shops only. "
                    "Unfiltered reads are cached publicly for 60 seconds."
                ),
                parameters=[
                    {
                        "name": "q",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "Search term, matched against name, description, category and shop name.",
                    },
                    {
                        "name": "q_original",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "Pre-translation term, retried when `q` finds nothing.",
                    },
                    {
                        "name": "category",
                        "in": "query",
                        "schema": {"type": "string", "enum": list(ALLOWED_CATEGORIES)},
                    },
                    {"name": "region", "in": "query", "schema": {"type": "string"}},
                    {
                        "name": "season",
                        "in": "query",
                        "schema": {"type": "string", "enum": list(SEASONS)},
                        "description": "Season names expand to their month terms before matching.",
                    },
                ],
                responses={
                    "200": {"description": "Matching listings and a count."},
                    "422": _error("`category` is outside the agricultural allow-list."),
                },
            )
        },
        "/api/products/{product_id}": {
            "get": _tagged(
                "Catalog",
                "Read one listing with its reviews",
                security=False,
                parameters=[
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                responses={"200": _json("ProductDetail"), "404": not_found},
            )
        },
        "/api/products/{product_id}/reviews": {
            "post": _tagged(
                "Reviews",
                "Publish or update your review",
                description=(
                    "One review per customer per product. Posting again overwrites the "
                    "existing one. Shops and admins are refused."
                ),
                parameters=[
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                requestBody=_body("ReviewRequest"),
                responses={
                    "201": _json("Review", "Review saved."),
                    "401": unauthorized,
                    "403": forbidden,
                    "404": not_found,
                    "422": validation,
                },
            )
        },
        "/api/products/{product_id}/messages": {
            "get": _tagged(
                "Messaging",
                "Read a product conversation",
                description=(
                    "Customers see only their own thread; shops see every thread on their "
                    "own listing. Admins are refused."
                ),
                parameters=[
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                responses={"200": {"description": "The transcript."}, "401": unauthorized, "403": forbidden, "404": not_found},
            ),
            "post": _tagged(
                "Messaging",
                "Send a message about a listing",
                description="Shops must pass `customer_id` and can only answer a thread the customer started.",
                parameters=[
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                requestBody=_body("MessageRequest"),
                responses={
                    "201": _json("ChatMessage", "Message sent."),
                    "401": unauthorized,
                    "403": forbidden,
                    "404": not_found,
                    "422": validation,
                },
            ),
        },
        "/api/customer/dashboard": {
            "get": _tagged(
                "Customer",
                "Customer dashboard counters",
                responses={"200": {"description": "Profile plus catalog and thread counts."}, "401": unauthorized, "403": forbidden},
            )
        },
        "/api/customer/favorites": {
            "get": _tagged(
                "Customer",
                "List saved products",
                description="Newest first. Listings that went out of stock or were archived are skipped.",
                responses={"200": {"description": "Saved products and a count."}, "401": unauthorized, "403": forbidden},
            )
        },
        "/api/customer/favorites/{product_id}": {
            "post": _tagged(
                "Customer",
                "Save a product",
                description="Idempotent: saving twice returns 200 with the existing entry instead of a duplicate.",
                parameters=[
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                responses={
                    "201": {"description": "Saved."},
                    "200": {"description": "Already saved."},
                    "401": unauthorized,
                    "403": forbidden,
                    "404": not_found,
                },
            ),
            "delete": _tagged(
                "Customer",
                "Remove a saved product",
                description="Idempotent: removing something that was never saved still returns 200.",
                parameters=[
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                responses={"200": {"description": "Removed."}, "401": unauthorized, "403": forbidden},
            ),
        },
        "/api/customer/messages": {
            "get": _tagged(
                "Customer",
                "List your conversations",
                responses={"200": {"description": "Thread digests, newest first."}, "401": unauthorized, "403": forbidden},
            )
        },
        "/api/shop/dashboard": {
            "get": _tagged(
                "Shop",
                "Shop dashboard with every listing",
                responses={"200": {"description": "Verification status, counts and listings."}, "401": unauthorized, "403": forbidden},
            )
        },
        "/api/shop/listings": {
            "get": _tagged(
                "Shop",
                "List your own listings",
                description="Includes archived listings, which the public catalog hides.",
                responses={"200": {"description": "Your listings, newest first."}, "401": unauthorized, "403": forbidden},
            ),
            "post": _tagged(
                "Shop",
                "Publish a listing",
                description=(
                    "Refused with `shop_verification_required` until an admin approves the shop. "
                    "The image URL is fetched and verified before the row is written."
                ),
                requestBody=_body("ListingRequest"),
                responses={
                    "201": _json("Product", "Listing published."),
                    "401": unauthorized,
                    "403": forbidden,
                    "422": validation,
                },
            ),
        },
        "/api/shop/listings/{product_id}": {
            "put": _tagged(
                "Shop",
                "Replace one of your listings",
                parameters=[
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                requestBody=_body("ListingRequest"),
                responses={
                    "200": _json("Product", "Listing updated."),
                    "401": unauthorized,
                    "403": forbidden,
                    "404": not_found,
                    "422": validation,
                },
            ),
            "delete": _tagged(
                "Shop",
                "Archive one of your listings",
                description="Soft delete: the row stays and `available` flips to false.",
                parameters=[
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                responses={"200": _json("Message", "Listing archived."), "401": unauthorized, "403": forbidden, "404": not_found},
            ),
        },
        "/api/shop/phone": {
            "put": _tagged(
                "Shop",
                "Set or clear your public contact number",
                description="The number appears on every one of your product pages as a tel: link.",
                requestBody=_body("PhoneRequest"),
                responses={"200": {"description": "Contact number updated."}, "401": unauthorized, "403": forbidden, "404": not_found, "422": validation},
            )
        },
        "/api/shop/messages": {
            "get": _tagged(
                "Shop",
                "List buyer conversations on your listings",
                responses={"200": {"description": "Thread digests, newest first."}, "401": unauthorized, "403": forbidden},
            )
        },
        "/api/admin/dashboard": {
            "get": _tagged(
                "Admin",
                "Marketplace counters",
                responses={"200": {"description": "Pending shops, users, listings, taxonomy sizes."}, "401": unauthorized, "403": forbidden},
            )
        },
        "/api/admin/shops": {
            "get": _tagged(
                "Admin",
                "List shop applications",
                parameters=[
                    {
                        "name": "status",
                        "in": "query",
                        "schema": {
                            "type": "string",
                            "enum": ["pending_verification", "approved", "suspended"],
                        },
                    }
                ],
                responses={"200": {"description": "Shop users with their profiles."}, "401": unauthorized, "403": forbidden},
            )
        },
        "/api/admin/shops/{user_id}/approve": {
            "post": _tagged(
                "Admin",
                "Approve a shop",
                description="Marks the profile approved, stamps `verified_at` and reactivates the account.",
                parameters=[{"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                responses={"200": {"description": "Shop approved."}, "401": unauthorized, "403": forbidden, "404": not_found},
            )
        },
        "/api/admin/shops/{user_id}/suspend": {
            "post": _tagged(
                "Admin",
                "Suspend a shop",
                description="Suspends the profile and the account together, hiding every listing from the catalog.",
                parameters=[{"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                responses={"200": {"description": "Shop suspended."}, "401": unauthorized, "403": forbidden, "404": not_found},
            )
        },
        "/api/admin/shops/{user_id}/restore": {
            "post": _tagged(
                "Admin",
                "Restore a suspended shop",
                parameters=[{"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                responses={"200": {"description": "Shop restored."}, "401": unauthorized, "403": forbidden, "404": not_found},
            )
        },
        "/api/admin/users": {
            "get": _tagged(
                "Admin",
                "List every account",
                responses={"200": {"description": "Users, newest first."}, "401": unauthorized, "403": forbidden},
            )
        },
        "/api/admin/users/{user_id}/suspend": {
            "post": _tagged(
                "Admin",
                "Suspend an account",
                description="Suspending a shop account also suspends its shop profile. Admins cannot suspend themselves.",
                parameters=[{"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                responses={"200": {"description": "Account suspended."}, "401": unauthorized, "403": forbidden, "404": not_found, "422": validation},
            )
        },
        "/api/admin/users/{user_id}/restore": {
            "post": _tagged(
                "Admin",
                "Restore an account",
                description="Restoring a shop account also returns its profile to approved.",
                parameters=[{"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                responses={"200": {"description": "Account restored."}, "401": unauthorized, "403": forbidden, "404": not_found},
            )
        },
        "/api/admin/categories": {
            "get": _tagged(
                "Admin",
                "List categories",
                responses={"200": {"description": "Every category with its active flag."}, "401": unauthorized, "403": forbidden},
            ),
            "post": _tagged(
                "Admin",
                "Activate an allow-listed category",
                description=(
                    "Only the eight agricultural categories can be activated. Anything else is "
                    "refused with `invalid_category`; arbitrary categories cannot be created."
                ),
                requestBody=_body("TaxonomyRequest"),
                responses={"201": _json("Taxonomy", "Category active."), "401": unauthorized, "403": forbidden, "422": validation},
            ),
        },
        "/api/admin/categories/{category_id}": {
            "delete": _tagged(
                "Admin",
                "Archive a category",
                description="Archived categories stop accepting new listings and leave the public filter list.",
                parameters=[{"name": "category_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                responses={"200": _json("Message", "Category archived."), "401": unauthorized, "403": forbidden, "404": not_found},
            )
        },
        "/api/admin/regions": {
            "get": _tagged(
                "Admin",
                "List regions",
                responses={"200": {"description": "Every region with its active flag."}, "401": unauthorized, "403": forbidden},
            ),
            "post": _tagged(
                "Admin",
                "Add or reactivate a region",
                requestBody=_body("TaxonomyRequest"),
                responses={"201": _json("Taxonomy", "Region active."), "401": unauthorized, "403": forbidden, "422": validation},
            ),
        },
        "/api/admin/regions/{region_id}": {
            "delete": _tagged(
                "Admin",
                "Archive a region",
                parameters=[{"name": "region_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                responses={"200": _json("Message", "Region archived."), "401": unauthorized, "403": forbidden, "404": not_found},
            )
        },
    }

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Bazaario API",
            "version": "1.0.0",
            "description": (
                "Bazaario is a shop-to-customer marketplace for Azerbaijani agricultural "
                "produce across eight categories.\n\n"
                "Buying is agreement based: there is no basket, checkout or order record. "
                "Customers reach a shop by message thread or phone and settle the deal "
                "directly.\n\n"
                "### Authentication\n"
                "`POST /api/auth/login` returns an HS256 JWT carrying `role` and "
                "`account_status` claims. Send it as `Authorization: Bearer <token>`. "
                "Press **Authorize** above and paste the token to try protected routes.\n\n"
                "### Roles\n"
                "Every protected route runs a role gate before any endpoint logic. A valid "
                "token with the wrong role gets `403` with `error: \"forbidden\"`.\n\n"
                "| Prefix | Role |\n| --- | --- |\n"
                "| `/api/customer/*` | customer |\n"
                "| `/api/shop/*` | shop |\n"
                "| `/api/admin/*` | admin |\n\n"
                "### Demo accounts\n"
                "`admin@bazaario.az` / `AdminDemo!2026`\n\n"
                "`shop@bazaario.az` / `ShopDemo!2026`\n\n"
                "`customer@bazaario.az` / `CustomerDemo!2026`"
            ),
        },
        "servers": [{"url": server_url, "description": "This deployment"}],
        "tags": [
            {"name": "Authentication", "description": "Signup, login and identity."},
            {"name": "Catalog", "description": "Public browsing and search. No token needed."},
            {"name": "Reviews", "description": "One rating and comment per customer per product."},
            {"name": "Messaging", "description": "Direct buyer-to-shop threads, one per product per customer."},
            {"name": "Customer", "description": "Customer dashboard and saved products."},
            {"name": "Shop", "description": "Listing management and buyer replies. Needs an approved shop."},
            {"name": "Admin", "description": "Verification queue, accounts and taxonomy."},
        ],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Paste the `access_token` returned by `POST /api/auth/login`.",
                }
            },
            "schemas": SCHEMAS,
        },
    }


SWAGGER_UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Bazaario API reference</title>
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css"
    />
    <style>
      body { margin: 0; background: #fbfaf7; }
      .topbar { display: none; }
      .swagger-ui .info .title { font-family: "Space Grotesk", Helvetica, Arial, sans-serif; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js" crossorigin></script>
    <script>
      window.onload = function () {
        window.ui = SwaggerUIBundle({
          url: "SPEC_URL",
          dom_id: "#swagger-ui",
          deepLinking: true,
          persistAuthorization: true,
          displayRequestDuration: true,
          docExpansion: "list",
          defaultModelsExpandDepth: 0,
          presets: [SwaggerUIBundle.presets.apis],
        });
      };
    </script>
  </body>
</html>
"""
