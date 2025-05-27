import pytest
from app import db, User
from werkzeug.security import check_password_hash

def test_user_registration_and_login(client):
    """Test user registration and login flow."""
    # Register a new user
    registration_data = {
        'username': 'newuser',
        'password': 'newpass123',
        'password2': 'newpass123'
    }
    
    response = client.post('/register', data=registration_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Registration successful' in response.data
    
    # Verify user in database
    with client.application.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert check_password_hash(user.password_hash, 'newpass123')
    
    # Log in with new user
    login_data = {
        'username': 'newuser',
        'password': 'newpass123'
    }
    
    response = client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome' in response.data

def test_user_password_change(auth_client):
    """Test changing user password."""
    # Change password
    password_data = {
        'old_password': 'testpass',
        'new_password': 'newtestpass123',
        'new_password2': 'newtestpass123'
    }
    
    response = auth_client.post('/change_password', data=password_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Password changed successfully' in response.data
    
    # Verify new password in database
    with auth_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert check_password_hash(user.password_hash, 'newtestpass123')
    
    # Log out
    response = auth_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'You have been logged out' in response.data
    
    # Try logging in with new password
    login_data = {
        'username': 'testuser',
        'password': 'newtestpass123'
    }
    
    response = auth_client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome' in response.data

def test_invalid_registration(client):
    """Test registration with invalid data."""
    # Try registering with mismatched passwords
    registration_data = {
        'username': 'testuser2',
        'password': 'pass123',
        'password2': 'pass456'
    }
    
    response = client.post('/register', data=registration_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Passwords do not match' in response.data
    
    # Try registering with existing username
    registration_data = {
        'username': 'testuser',
        'password': 'pass123',
        'password2': 'pass123'
    }
    
    response = client.post('/register', data=registration_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Username already exists' in response.data

def test_invalid_login(client):
    """Test login with invalid credentials."""
    # Try logging in with wrong password
    login_data = {
        'username': 'testuser',
        'password': 'wrongpass'
    }
    
    response = client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data
    
    # Try logging in with non-existent user
    login_data = {
        'username': 'nonexistent',
        'password': 'pass123'
    }
    
    response = client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data 