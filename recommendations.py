from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db
from models import User, Material, Product, Recommendation

recommendations_bp = Blueprint("recommendations", __name__)


# ================= SCORING ALGORITHM ================= #
def calculate_material_score(material, product):
    """
    Calculate suitability score for a material (0-10)
    Higher score = better match for the product
    """
    # Base weights
    w_bio = 0.20      # Biodegradability importance
    w_recyc = 0.20    # Recyclability importance
    w_strength = 0.20 # Strength importance
    w_co2 = 0.20      # CO2 impact importance
    w_cost = 0.20     # Cost importance

    # Adjust weights based on product characteristics
    if product.fragility_level >= 7:  # Very fragile items
        w_strength = 0.40
        w_cost = 0.10
        w_co2 = 0.10
    elif product.fragility_level <= 3:  # Sturdy items
        w_strength = 0.10
        w_cost = 0.30
        w_co2 = 0.20

    if product.temperature_sensitive:
        w_strength += 0.10
        w_cost -= 0.05

    # Normalize scores (0-10 scale)
    s_bio = material.biodegradability_score  # Already 1-10
    s_recyc = material.recyclability_percent / 10.0  # Convert 0-100 to 0-10
    s_strength = material.strength_rating  # Already 1-10
    s_co2 = max(0, 10 - (material.co2_emission_score * 2))  # Lower CO2 = better
    s_cost = max(0, 10 - (material.cost_per_kg * 2))  # Lower cost = better

    # Calculate weighted score
    score = (
        s_bio * w_bio +
        s_recyc * w_recyc +
        s_strength * w_strength +
        s_co2 * w_co2 +
        s_cost * w_cost
    )

    return min(10, max(0, round(score, 2)))


def calculate_impact_metrics(material):
    """Calculate CO2 reduction and cost savings percentages"""
    # Baseline values (average traditional packaging)
    baseline_co2 = 3.0  # Average CO2 score
    baseline_cost = 3.5  # Average cost per kg

    co2_reduction = max(0, ((baseline_co2 - material.co2_emission_score) / baseline_co2) * 100)
    cost_savings = max(0, ((baseline_cost - material.cost_per_kg) / baseline_cost) * 100)

    return round(co2_reduction, 2), round(cost_savings, 2)


# ================= RECOMMEND MATERIALS ================= #
@recommendations_bp.route("/recommend", methods=["POST"])
@jwt_required()
def recommend_materials():
    try:
        user_id = int(get_jwt_identity())
        
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401

        data = request.get_json()
        
        # Validate required fields
        required_fields = ["product_name", "food_type", "weight_kg", "fragility_level"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        # Create product record
        product = Product(
            user_id=user_id,
            product_name=data["product_name"].strip(),
            food_type=data["food_type"].strip(),
            weight_kg=float(data["weight_kg"]),
            fragility_level=int(data["fragility_level"]),
            temperature_sensitive=bool(data.get("temperature_sensitive", False))
        )

        db.session.add(product)
        db.session.flush()  # Get product ID without committing

        # Get all materials and score them
        materials = Material.query.all()
        results = []

        for material in materials:
            score = calculate_material_score(material, product)
            co2_reduction, cost_savings = calculate_impact_metrics(material)
            
            results.append({
                "material_id": material.id,
                "material_name": material.material_name,
                "score": round(score / 10, 3),  # Normalize to 0-1
                "co2_reduction_percent": co2_reduction,
                "cost_savings_percent": cost_savings,
                "recyclability": material.recyclability_percent,
                "strength": material.strength_rating,
                "cost_per_kg": material.cost_per_kg,
                "biodegradability": material.biodegradability_score,
                "weight_capacity": material.weight_capacity_kg
            })

        # Sort by score (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Save top recommendation
        if results:
            top_recommendation = results[0]
            recommendation = Recommendation(
                user_id=user_id,
                product_id=product.id,
                material_id=top_recommendation["material_id"],
                recommendation_score=top_recommendation["score"],
                co2_reduction_percent=top_recommendation["co2_reduction_percent"],
                cost_savings_percent=top_recommendation["cost_savings_percent"]
            )
            db.session.add(recommendation)

        db.session.commit()

        return jsonify({
            "product_id": product.id,
            "product_name": product.product_name,
            "total_materials": len(results),
            "recommendations": results[:10]  # Return top 10
        }), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": f"Invalid input data: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"❌ Recommendation error: {str(e)}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


# ================= GET HISTORY ================= #
@recommendations_bp.route("/history", methods=["GET"])
@jwt_required()
def recommendation_history():
    try:
        user_id = int(get_jwt_identity())
        
        # Get user's recommendations
        recs = Recommendation.query.filter_by(
            user_id=user_id
        ).order_by(Recommendation.created_at.desc()).all()

        history = []
        for rec in recs:
            history.append({
                "id": rec.id,
                "material_name": rec.material.material_name if rec.material else "Unknown",
                "product_name": rec.product.product_name if rec.product else "Unknown",
                "recommendation_score": rec.recommendation_score,
                "co2_reduction_percent": rec.co2_reduction_percent,
                "cost_savings_percent": rec.cost_savings_percent,
                "created_at": rec.created_at.isoformat(),
                "material_details": {
                    "recyclability_percent": rec.material.recyclability_percent if rec.material else 0,
                    "strength_rating": rec.material.strength_rating if rec.material else 0,
                    "cost_per_kg": rec.material.cost_per_kg if rec.material else 0,
                    "biodegradability": rec.material.biodegradability_score if rec.material else 0
                }
            })

        return jsonify({
            "total": len(history),
            "recommendations": history
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch history: {str(e)}"}), 500


# ================= LIST MATERIALS ================= #
@recommendations_bp.route("/materials", methods=["GET"])
@jwt_required()
def list_materials():
    try:
        materials = Material.query.all()
        
        material_list = []
        for material in materials:
            material_list.append({
                "id": material.id,
                "material_name": material.material_name,
                "eco_score": material.calculate_eco_score(),
                "cost_per_kg": material.cost_per_kg,
                "recyclability": material.recyclability_percent,
                "strength": material.strength_rating,
                "co2_impact": material.co2_emission_score
            })

        return jsonify({
            "materials": material_list,
            "total": len(material_list)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch materials: {str(e)}"}), 500


# ================= SAVE SPECIFIC RECOMMENDATION ================= #
@recommendations_bp.route("/save", methods=["POST"])
@jwt_required()
def save_recommendation():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        product_id = data.get("product_id")
        material_id = data.get("material_id")
        
        if not product_id or not material_id:
            return jsonify({"error": "Missing product_id or material_id"}), 400
            
        # Check if product exists and belongs to user
        product = Product.query.filter_by(id=product_id, user_id=user_id).first()
        if not product:
            return jsonify({"error": "Product not found"}), 404
            
        # Check if material exists
        material = Material.query.get(material_id)
        if not material:
            return jsonify({"error": "Material not found"}), 404
            
        # Recalculate metrics for this pair
        from recommendations import calculate_material_score, calculate_impact_metrics
        score = calculate_material_score(material, product)
        co2_reduction, cost_savings = calculate_impact_metrics(material)
        
        # Check if already exists
        existing = Recommendation.query.filter_by(
            user_id=user_id, product_id=product_id, material_id=material_id
        ).first()
        if existing:
            return jsonify({"message": "Already saved", "id": existing.id}), 200
            
        new_rec = Recommendation(
            user_id=user_id,
            product_id=product_id,
            material_id=material_id,
            recommendation_score=round(score / 10, 3),
            co2_reduction_percent=co2_reduction,
            cost_savings_percent=cost_savings
        )
        db.session.add(new_rec)
        db.session.commit()
        return jsonify({"message": "Analysis saved!", "id": new_rec.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500