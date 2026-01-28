from flask_login import UserMixin
from database import db
from datetime import datetime

# ================= USER MODEL ================= #
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    products = db.relationship("Product", backref="user", lazy=True, cascade="all, delete-orphan")
    recommendations = db.relationship("Recommendation", backref="user", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"


# ================= MATERIAL MODEL ================= #
class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    material_name = db.Column(db.String(150), nullable=False, unique=True)
    strength_rating = db.Column(db.Integer, nullable=False)
    weight_capacity_kg = db.Column(db.Float, nullable=False)
    biodegradability_score = db.Column(db.Integer, nullable=False)
    recyclability_percent = db.Column(db.Float, nullable=False)
    co2_emission_score = db.Column(db.Float, nullable=False)
    cost_per_kg = db.Column(db.Float, nullable=False)

    # Relationships
    recommendations = db.relationship("Recommendation", backref="material", lazy=True)

    def calculate_eco_score(self):
        """Calculate overall eco-friendliness score (0-10)"""
        bio = (self.biodegradability_score / 10) * 4  # 40% weight
        recycle = (self.recyclability_percent / 100) * 3  # 30% weight
        co2 = max(0, 10 - (self.co2_emission_score * 2)) * 0.3  # 30% weight (lower CO2 = better)
        return round(bio + recycle + co2, 2)

    def __repr__(self):
        return f"<Material {self.material_name}>"


# ================= PRODUCT MODEL ================= #
class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    product_name = db.Column(db.String(150), nullable=False)
    food_type = db.Column(db.String(100), nullable=False)  # Dry, Fresh, Frozen, Liquid, etc.
    weight_kg = db.Column(db.Float, nullable=False)
    fragility_level = db.Column(db.Integer, nullable=False)  # 1-10 scale
    temperature_sensitive = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    recommendations = db.relationship("Recommendation", backref="product", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product {self.product_name} ({self.food_type})>"


# ================= RECOMMENDATION MODEL ================= #
class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    
    recommendation_score = db.Column(db.Float, nullable=False)
    co2_reduction_percent = db.Column(db.Float, nullable=False)
    cost_savings_percent = db.Column(db.Float, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Recommendation score={self.recommendation_score}>"