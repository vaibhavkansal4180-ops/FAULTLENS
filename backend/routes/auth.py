import functools
from flask import Blueprint, request, jsonify, session
from backend.extensions import db
from backend.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def get_current_user():
    """Retrieves current logged-in user from session or header fallback."""
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)

    # API header fallback for test automation: X-User-Id
    api_user_id = request.headers.get("X-User-Id")
    if api_user_id:
        try:
            return db.session.get(User, int(api_user_id))
        except (ValueError, TypeError):
            return None
    return None


def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication required. Please log in."}), 401
            if user.role not in allowed_roles:
                return jsonify({
                    "error": f"Permission denied. Required role in {list(allowed_roles)}, current role: {user.role}"
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "VIEWER").upper()
    full_name = data.get("full_name", "").strip()

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required."}), 400

    if role not in ["ADMIN", "TECHNICIAN", "VIEWER"]:
        role = "VIEWER"

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "A user with that username or email already exists."}), 409

    new_user = User(
        username=username,
        email=email,
        role=role,
        full_name=full_name or username
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    session["user_id"] = new_user.id
    session["role"] = new_user.role

    return jsonify({
        "message": "User registered successfully.",
        "user": new_user.to_dict()
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    identifier = data.get("username", "").strip()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"error": "Username or email and password are required."}), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials provided."}), 401

    session["user_id"] = user.id
    session["role"] = user.role

    return jsonify({
        "message": "Authentication successful.",
        "user": user.to_dict()
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Successfully logged out."}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None}), 200
    return jsonify({"authenticated": True, "user": user.to_dict()}), 200
