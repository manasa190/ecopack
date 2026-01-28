
from app import create_app
from models import Recommendation, Material, User

app = create_app()

with app.app_context():
    recs = Recommendation.query.all()
    materials = Material.query.all()
    users = User.query.all()
    
    print(f"Users: {len(users)}")
    print(f"Materials: {len(materials)}")
    print(f"Recommendations: {len(recs)}")
    
    for r in recs[:5]:
        print(f"Rec ID: {r.id}, User ID: {r.user_id}, Material ID: {r.material_id}, Material Object: {r.material}")
        if r.material:
            print(f"  Material Name: {r.material.material_name}")
