
import requests
import json
from app import create_app
from flask_login import login_user
from models import User

app = create_app()

with app.test_client() as client:
    with app.app_context():
        # Login
        user = User.query.first()
        if not user:
            print("No user")
            exit()
            
        # Get access token
        login_resp = client.post('/api/auth/login', json={
            "email": user.email,
            "password": "password123" # Assuming standard password, or I can just mock the token
        })
        
        # Since I don't know the password, I'll generate a token using create_access_token manually
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=str(user.id))
        
        print(f"Generated token for user {user.username}")
        
        # Test Dashboard Endpoint
        headers = {'Authorization': f'Bearer {token}'}
        resp = client.get('/api/analytics/dashboard', headers=headers)
        
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json
            print("Metrics:", json.dumps(data.get('metrics', {}), indent=2))
            print("Charts Keys:", list(data.get('charts', {}).keys()))
            
            charts = data.get('charts', {})
            if 'trend_chart' in charts:
                print("Trend Chart Data Points:", len(charts['trend_chart']['data'][0]['x']))
            else:
                print("Trend Chart missing!")
        else:
            print("Error Response:", resp.text)
