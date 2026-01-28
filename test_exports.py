
from app import create_app
from flask_jwt_extended import create_access_token
from models import User

app = create_app()

with app.test_client() as client:
    with app.app_context():
        user = User.query.first()
        token = create_access_token(identity=str(user.id))
        headers = {'Authorization': f'Bearer {token}'}
        
        for fmt in ['pdf', 'excel', 'csv']:
            print(f"Testing {fmt} export...")
            resp = client.get(f'/api/analytics/export/{fmt}', headers=headers)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"  Content-Type: {resp.mimetype}")
                print(f"  Content-Length: {len(resp.data)}")
            else:
                print(f"  Error: {resp.text}")
