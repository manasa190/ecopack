from flask import Flask, render_template, jsonify, redirect, url_for
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager, logout_user
from sqlalchemy import inspect
import pandas as pd
import os

from config import Config
from database import db
from models import User, Material, Product, Recommendation
from auth import auth_bp
from recommendations import recommendations_bp
from analytics import analytics_bp


def seed_materials():
    """Seed database with materials from CSV or create sample data"""
    if Material.query.first() is not None:
        print("✅ Materials already seeded")
        return

    materials = []
    
    # Try to load from CSV file if it exists
    csv_path = "materials_final.csv"
    if os.path.exists(csv_path):
        try:
            print(f"📂 Loading materials from {csv_path}...")
            materials_df = pd.read_csv(csv_path)
            
            for _, row in materials_df.iterrows():
                materials.append(Material(
                    material_name=row['material_name'],
                    strength_rating=int(row['strength_rating']),
                    weight_capacity_kg=float(row['weight_capacity_kg']),
                    biodegradability_score=int(row['biodegradability_score']),
                    recyclability_percent=float(row['recyclability_percent']),
                    co2_emission_score=float(row['co2_emission_score']),
                    cost_per_kg=float(row['cost_per_kg'])
                ))
            print(f"✅ Seeded {len(materials)} materials from CSV")
        except Exception as e:
            print(f"❌ Failed to load CSV: {e}")
            materials = create_sample_materials()
    else:
        print("📝 CSV not found, creating sample materials...")
        materials = create_sample_materials()
    
    db.session.bulk_save_objects(materials)
    db.session.commit()
    print(f"✅ Database seeded with {len(materials)} materials")


def create_sample_materials():
    """Create sample materials for testing"""
    return [
        Material(
            material_name="Recycled Cardboard",
            strength_rating=8,
            weight_capacity_kg=60,
            biodegradability_score=10,
            recyclability_percent=90,
            co2_emission_score=0.6,
            cost_per_kg=1.2
        ),
        Material(
            material_name="Kraft Paper",
            strength_rating=5,
            weight_capacity_kg=30,
            biodegradability_score=10,
            recyclability_percent=85,
            co2_emission_score=0.8,
            cost_per_kg=1.5
        ),
        Material(
            material_name="PLA Bioplastic",
            strength_rating=6,
            weight_capacity_kg=40,
            biodegradability_score=9,
            recyclability_percent=30,
            co2_emission_score=1.5,
            cost_per_kg=4.0
        ),
        Material(
            material_name="Glass Jar",
            strength_rating=9,
            weight_capacity_kg=80,
            biodegradability_score=10,
            recyclability_percent=100,
            co2_emission_score=3.0,
            cost_per_kg=2.0
        ),
        Material(
            material_name="Bamboo Fiber",
            strength_rating=7,
            weight_capacity_kg=45,
            biodegradability_score=9,
            recyclability_percent=70,
            co2_emission_score=1.0,
            cost_per_kg=3.5
        ),
        Material(
            material_name="Mushroom Packaging",
            strength_rating=4,
            weight_capacity_kg=20,
            biodegradability_score=10,
            recyclability_percent=100,
            co2_emission_score=0.2,
            cost_per_kg=5.0
        ),
    ]


def create_app():
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    
    CORS(app, supports_credentials=True)
    
    jwt = JWTManager(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login_page'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "Invalid token"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"error": "Authorization required"}), 401

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(recommendations_bp, url_prefix="/api/recommendations")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

    # Initialize database
    with app.app_context():
        try:
            # Check if schema needs updating
            inspector = inspect(db.engine)
            if inspector.has_table("products"):
                cols = [c['name'] for c in inspector.get_columns("products")]
                if "food_type" not in cols:
                    print("🔄 Schema mismatch detected. Recreating database...")
                    db.drop_all()
        except Exception as e:
            print(f"⚠️ Schema check warning: {e}")
        
        db.create_all()
        seed_materials()
        print("🚀 Database ready!")

    # Frontend routes
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/signup")
    def signup_page():
        return render_template("signup.html")

    @app.route("/dashboard")
    def dashboard_page():
        from datetime import datetime
        return render_template("dashboard.html", current_date=datetime.now().strftime("%B %d, %Y"))

    @app.route("/product-input")
    def product_input_page():
        return render_template("product_input.html")

    @app.route("/recommendations")
    def recommendations_page():
        return render_template("recommendations.html")

    @app.route("/analytics")
    def analytics_page():
        return render_template("analytics.html")

    @app.route("/report")
    def report_page():
        return render_template("report.html")

    @app.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for('login_page'))

    # Health check
    @app.route("/health")
    def health():
        return jsonify({"status": "healthy", "service": "EcoPackAI"}), 200

    # Global error handler
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    print("🌱 Starting EcoPackAI on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)