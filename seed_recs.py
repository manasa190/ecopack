
from app import create_app, db
from models import User, Product, Material, Recommendation
import random
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    print("🌱 Seeding dummy analytics data...")
    
    # Get first user or create one
    user = User.query.first()
    if not user:
        print("❌ No user found. Create an account first.")
        exit()
        
    print(f"👤 Seeding for user: {user.username}")
    
    # Get materials
    materials = Material.query.all()
    if not materials:
        print("❌ No materials found.")
        exit()
        
    # Create products
    products = []
    for i in range(5):
        p = Product(
            user_id=user.id,
            product_name=f"Test Product {i+1}",
            food_type="Dry",
            weight_kg=0.5,
            fragility_level=5
        )
        db.session.add(p)
        products.append(p)
    db.session.commit()
    
    # Create recommendations
    base_date = datetime.now() - timedelta(days=180)
    
    for i in range(20):
        # random date in last 6 months
        created_at = base_date + timedelta(days=random.randint(0, 180))
        
        product = random.choice(products)
        material = random.choice(materials)
        
        rec = Recommendation(
            user_id=user.id,
            product_id=product.id,
            material_id=material.id,
            recommendation_score=random.uniform(0.7, 0.99),
            co2_reduction_percent=random.uniform(10, 80),
            cost_savings_percent=random.uniform(5, 40),
            created_at=created_at
        )
        db.session.add(rec)
        
    db.session.commit()
    print("✅ Successfully seeded 20 recommendations!")
