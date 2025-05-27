import os
import sys
import pytest
from pathlib import Path

# Add the application root directory to the Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app import app, db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

@pytest.fixture
def auth_client(client):
    # Create a test user
    from app import User
    user = User(username='testuser')
    user.set_password('testpass')
    db.session.add(user)
    db.session.commit()
    
    # Login
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    return client 