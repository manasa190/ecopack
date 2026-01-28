
from app import create_app
from flask_jwt_extended import create_access_token
from models import User

app = create_app()

with app.test_client() as client:
    with app.app_context():
        user = User.query.first()
        token = create_access_token(identity=str(user.id))
        headers = {'Authorization': f'Bearer {token}'}
        
        print("Testing Material Insights...")
        resp = client.get('/api/analytics/insights/materials', headers=headers)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json
            print(f"  Insights found: {len(data.get('insights', []))}")
            if data['insights']:
                print(f"  First Insight Material: {data['insights'][0]['material']}")
        else:
            print(f"  Error: {resp.text}")
