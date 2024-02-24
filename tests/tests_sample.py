# test_sample.py
from your_flask_app import app

def test_homepage():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome to My Flask App' in response.data
