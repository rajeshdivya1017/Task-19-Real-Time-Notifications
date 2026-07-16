from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
from flask_bcrypt import Bcrypt

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from datetime import timedelta

from db import get_connection
import os
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)

app = Flask(__name__)

CORS(
    app,
    origins=[
        "http://localhost:5173",
        "http://localhost:5174"
    ]
)

socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "http://localhost:5173",
        "http://localhost:5174"
    ],
    async_mode="eventlet"
)


@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    return response

bcrypt = Bcrypt(app)

app.config["JWT_SECRET_KEY"] = "ecommerce_jwt_secret"

app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)

app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

jwt = JWTManager(app)


# =========================
# SOCKET EVENTS
# =========================

@socketio.on("connect")
def handle_connect():
    print(f"✅ Client Connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    print(f"❌ Client Disconnected: {request.sid}")


@socketio.on("join")
def handle_join(data):
    user_id = data.get("user_id")
    role = data.get("role")

    join_room(f"user_{user_id}")

    if role == "admin":
        join_room("admins")
        print("✅ Admin joined admins room")

    emit("joined", {"message": "Joined successfully"})

# =========================
# IMAGE UPLOAD CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/api/upload", methods=["POST"])
@jwt_required()
def upload_image():

    if "image" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only png, jpg, jpeg and webp allowed"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()

    filename = f"{uuid.uuid4().hex}.{ext}"

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)


    user_id = get_jwt_identity()

    image_url = f"/static/uploads/{filename}"


    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute(
        """
        UPDATE users
        SET avatar_url=%s
        WHERE id=%s
        """,
        (image_url, user_id)
    )


    conn.commit()

    

    cursor.close()
    conn.close()


    return jsonify({
        "message": "Avatar uploaded successfully",
        "image_url": image_url
    }), 201
# =========================
# REGISTER
# =========================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "customer")

    if not name or not email or not password:
        return jsonify({"message": "All fields required"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    if cursor.fetchone():
        return jsonify({"message": "Email exists"}), 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    cursor.execute("""
        INSERT INTO users (name, email, password, role)
        VALUES (%s, %s, %s, %s)
    """, (name, email, hashed, role))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Registered"}), 201


# =========================
# LOGIN
# =========================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user or not bcrypt.check_password_hash(
        user["password"],
        password
    ):
        return jsonify({"message": "Invalid login"}), 401

    access_token = create_access_token(
        identity=str(user["id"]),
        additional_claims={
            "role": user["role"],
            "name": user["name"]
        }
    )

    refresh_token = create_refresh_token(
        identity=str(user["id"])
    )

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "avatar_url": user["avatar_url"]  
        }
    }), 200


# =========================
# LOGOUT
# =========================
@app.route("/api/logout")
def logout():
    return jsonify({"message": "Logged out"})


# =========================
# CURRENT USER
# =========================
@app.route("/api/me", methods=["GET"])
@jwt_required()
def me():

    user_id = get_jwt_identity()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            role,
            avatar_url,
            created_at
        FROM users
        WHERE id=%s
    """, (user_id,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user), 200



@app.route("/api/me", methods=["PUT"])
@jwt_required()
def update_profile():

    user_id = get_jwt_identity()

    data = request.get_json()

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()

    if not name or not email:
        return jsonify({
            "error": "Name and Email are required"
        }), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if email already exists for another user
    cursor.execute(
        "SELECT id FROM users WHERE email=%s AND id!=%s",
        (email, user_id)
    )

    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({
            "error": "Email already exists"
        }), 409

    cursor.execute("""
        UPDATE users
        SET name=%s,
            email=%s
        WHERE id=%s
    """, (name, email, user_id))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Profile updated successfully"
    }), 200

@app.route("/api/me/password", methods=["PUT"])
@jwt_required()
def change_password():
    data = request.get_json()

    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    # Validate input
    if not current_password or not new_password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400

    if new_password != confirm_password:
        return jsonify({"message": "New passwords do not match"}), 400

    # Get logged-in user ID from JWT
    current_user_id = get_jwt_identity()

    # Connect to database
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch user's current hashed password
    cursor.execute(
        "SELECT password FROM users WHERE id = %s",
        (current_user_id,)
    )

    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({"message": "User not found"}), 404

    # Verify current password
    if not bcrypt.check_password_hash(user["password"], current_password):
        cursor.close()
        conn.close()
        return jsonify({"message": "Current password is incorrect"}), 400

    # Hash the new password
    hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")

    # Update password
    cursor.execute(
        "UPDATE users SET password = %s WHERE id = %s",
        (hashed_password, current_user_id)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Password updated successfully"}), 200
# =========================
# PRODUCTS
# =========================
@app.route("/api/products")
def get_products():

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 8))
    search = request.args.get("search", "")
    category = request.args.get("category", "")

    offset = (page - 1) * limit

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    where_clause = "WHERE p.name LIKE %s"
    params = [f"%{search}%"]

    if category:
        where_clause += " AND c.name = %s"
        params.append(category)

    # Total count
    count_query = f"""
        SELECT COUNT(*) AS total
        FROM products p
        LEFT JOIN categories c
        ON p.category_id = c.id
        {where_clause}
    """

    cursor.execute(count_query, tuple(params))
    total = cursor.fetchone()["total"]

    # Products
    product_query = f"""
        SELECT
            p.*,
            c.name AS category
        FROM products p
        LEFT JOIN categories c
        ON p.category_id = c.id
        {where_clause}
        ORDER BY p.id DESC
        LIMIT %s OFFSET %s
    """

    cursor.execute(
        product_query,
        tuple(params + [limit, offset])
    )

    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "products": products,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    })
# =========================
# SINGLE PRODUCT
# =========================
@app.route("/api/products/<int:id>")
def get_product(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.*, c.name AS category
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.id=%s
    """, (id,))

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(product)



# =========================
# ADD PRODUCT
# =========================
@app.route("/api/products", methods=["POST"])
@jwt_required()
def add_product():

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"message": "Forbidden"}), 403

    data = request.json

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO products (name, description, price, stock, category_id, image_url)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        data["name"],
        data.get("description"),
        data["price"],
        data["stock"],
        data["category_id"],
        data["image_url"]
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Product added"})


# =========================
# UPDATE PRODUCT
# =========================
@app.route("/api/products/<int:id>", methods=["PUT"])
@jwt_required()
def update_product(id):

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"message": "Forbidden"}), 403

    data = request.json

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE products
        SET name=%s,
            description=%s,
            price=%s,
            stock=%s,
            category_id=%s,
            image_url=%s
        WHERE id=%s
    """, (
        data["name"],
        data.get("description"),
        data["price"],
        data["stock"],
        data["category_id"],
        data["image_url"],
        id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Updated"})

# =========================
# DELETE PRODUCT
# =========================
# =========================
# DELETE PRODUCT
# =========================
@app.route("/api/products/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"message": "Forbidden"}), 403

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM products WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Deleted"})

# =========================
# CREATE ORDER
# =========================
# =========================
# CREATE ORDER
# =========================
@app.route("/api/orders", methods=["POST", "OPTIONS"])
@jwt_required()
def create_order():

    if request.method == "OPTIONS":
        return "", 200

    user_id = get_jwt_identity()

    data = request.json
    address = data.get("address")
    items = data.get("items", [])

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    total = 0

    for i in items:
        cursor.execute(
            "SELECT price FROM products WHERE id=%s",
            (i["product_id"],)
        )
        p = cursor.fetchone()

        if p:
            total += p["price"] * i["quantity"]

    cursor.execute("""
        INSERT INTO orders
        (user_id, total_amount, status, address)
        VALUES (%s,%s,%s,%s)
    """, (
        user_id,
        total,
        "Pending",
        address
    ))

    order_id = cursor.lastrowid

    for i in items:

        cursor.execute(
            "SELECT price FROM products WHERE id=%s",
            (i["product_id"],)
        )

        p = cursor.fetchone()

        if p:
            cursor.execute("""
                INSERT INTO order_items
                (order_id, product_id, quantity, unit_price)
                VALUES (%s,%s,%s,%s)
            """, (
                order_id,
                i["product_id"],
                i["quantity"],
                p["price"]
            ))

    conn.commit()

    # =========================
    # SAVE ADMIN NOTIFICATION
    # =========================

    # Get customer name
    cursor.execute(
        "SELECT name FROM users WHERE id=%s",
        (user_id,)
    )

    customer = cursor.fetchone()

    customer_name = customer["name"] if customer else "Customer"

    # Save notification for all admins
    cursor.execute(
        """
        INSERT INTO notifications (user_id, message, type)
        SELECT id, %s, 'order'
        FROM users
        WHERE role='admin'
        """,
        (
            f"New Order #{order_id} placed by {customer_name} - ₹{total}",
        )
    )

    conn.commit()

    # Send real-time notification

    print("Sending notification to admins room...")
    socketio.emit(
        "new_notification",
        {
            "message": f"New Order #{order_id} placed by {customer_name}",
            "type": "order",
            "order_id": order_id
        },
        room="admins"
    )

    socketio.emit(
    "order_count_update",
    {
        "action": "increment"
    },
    room="admins"
)

    print("✅ Notification sent to admins")

    cursor.close()
    conn.close()

    return jsonify({"message": "Order placed"})
# =========================
# MY ORDERS
# =========================
@app.route("/api/orders/my")
@jwt_required()
def my_orders():

    user_id = get_jwt_identity()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM orders
        WHERE user_id=%s
        ORDER BY id DESC
    """, (user_id,))

    orders = cursor.fetchall()

    for o in orders:

        cursor.execute("""
            SELECT oi.*,
                   p.name AS product_name
            FROM order_items oi
            JOIN products p
            ON oi.product_id = p.id
            WHERE oi.order_id=%s
        """, (o["id"],))

        o["items"] = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(orders)



# =========================
# ADMIN ORDERS
@app.route("/api/admin/orders")
@jwt_required()
def admin_orders():

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"message": "Forbidden"}), 403

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))

    offset = (page - 1) * limit

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
    """)

    total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT o.*,
               u.name AS customer_name
        FROM orders o
        JOIN users u
        ON o.user_id = u.id
        ORDER BY o.id DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))

    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "orders": orders,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    })

# =========================
# UPDATE ORDER STATUS
# =========================
@app.route("/api/orders/<int:id>/status", methods=["PUT"])
@jwt_required()
def update_order_status(id):

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"message": "Forbidden"}), 403

    data = request.json

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE orders SET status=%s WHERE id=%s",
        (data["status"], id)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Order status updated successfully"
    })

# =========================
# REFRESH TOKEN
# =========================
@app.route("/api/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():

    user_id = get_jwt_identity()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    new_access_token = create_access_token(
        identity=str(user["id"]),
        additional_claims={
            "role": user["role"],
            "name": user["name"]
        }
    )

    return jsonify({
        "access_token": new_access_token
    }), 200

# =========================
# GET MY NOTIFICATIONS
# =========================
from datetime import timedelta


@app.route("/api/notifications")
@jwt_required()
def get_notifications():

    user_id = get_jwt_identity()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM notifications
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 10
    """, (user_id,))

    notifications = cursor.fetchall()

    for n in notifications:
        if n["created_at"]:
         n["created_at"] = n["created_at"].isoformat()

    cursor.close()
    conn.close()

    return jsonify(notifications)


# =========================
# MARK ALL NOTIFICATIONS READ
# =========================
@app.route("/api/notifications/read", methods=["PUT"])
@jwt_required()
def mark_notifications_read():

    user_id = get_jwt_identity()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE notifications
        SET is_read=1
        WHERE user_id=%s
    """, (user_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Notifications marked as read"
    })


# =========================
# MARK ALL NOTIFICATIONS AS READ
# =========================
@app.route("/api/notifications/read-all", methods=["PUT"])
@jwt_required()
def mark_all_notifications_read():

    user_id = get_jwt_identity()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = %s
    """, (user_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "All notifications marked as read"
    }), 200
# =========================
# MARK SINGLE NOTIFICATION AS READ
# =========================
@app.route("/api/notifications/<int:id>/read", methods=["PUT"])
@jwt_required()
def mark_notification_read(id):

    user_id = get_jwt_identity()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE id = %s
        AND user_id = %s
    """, (id, user_id))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Notification marked as read"
    }), 200

# =========================
# DELETE NOTIFICATION
# =========================
@app.route("/api/notifications/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_notification(id):

    user_id = get_jwt_identity()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM notifications
        WHERE id = %s
        AND user_id = %s
    """, (id, user_id))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Notification deleted successfully"
    }), 200
# =========================
# RUN
# =========================
if __name__ == "__main__":
    socketio.run(
        app,
        debug=True,
        port=5000
    )