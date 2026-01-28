from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import User
import re

auth_bp = Blueprint("auth", __name__)

# Validation patterns
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[^\s]{8,}$")


def is_valid_email(email):
    return EMAIL_REGEX.match(email)


def is_valid_username(username):
    return USERNAME_REGEX.match(username)


def is_strong_password(password):
    return PASSWORD_REGEX.match(password)


# ================= REGISTER ================= #
@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        # Validation
        if not all([username, email, password]):
            return jsonify({"error": "All fields are required"}), 400

        if not is_valid_username(username):
            return jsonify({
                "error": "Username must be 3-20 characters (letters, numbers, underscore)"
            }), 400

        if not is_valid_email(email):
            return jsonify({"error": "Invalid email format"}), 400

        if not is_strong_password(password):
            return jsonify({
                "error": "Password must be at least 8 characters with letters and numbers"
            }), 400

        # Check for existing user
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 400

        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        # Login for session-based templates
        login_user(user, remember=True)

        # Auto-login after registration
        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            "message": "Registration successful",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


# ================= LOGIN ================= #
@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid username or password"}), 401

        # Login for session-based templates
        login_user(user, remember=True)
        
        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }), 200

    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


# ================= PROFILE ================= #
@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }), 200

    except Exception as e:
        return jsonify({"error": f"Profile fetch failed: {str(e)}"}), 500


# ================= LOGOUT ================= #
@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200