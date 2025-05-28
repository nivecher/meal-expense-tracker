import pytest
from app import db, User
from werkzeug.security import check_password_hash
from tests.factories import UserFactory

def test_user_registration_and_login(client, app_context):
    """Test user registration and login flow."""
    # Register a new user
    registration_data = {
        'username': 'newuser',
        'password': 'testpass123',
        'password2': 'testpass123'
    }
    response = client.post('/register', data=registration_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Registration successful' in response.data

    # Try to login with the new user
    login_data = {
        'username': 'newuser',
        'password': 'testpass123'
    }
    response = client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Logged in successfully' in response.data

def test_user_password_change(auth_client, app_context):
    """Test changing user password."""
    # Change password
    new_password_data = {
        'current_password': 'testpass',
        'new_password': 'newpass123',
        'new_password2': 'newpass123'
    }
    response = auth_client.post('/change_password', data=new_password_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Password changed successfully' in response.data

    # Try logging in with new password
    login_data = {
        'username': 'testuser',
        'password': 'newpass123'
    }
    response = auth_client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Logged in successfully' in response.data

def test_invalid_registration(client, app_context):
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

def test_invalid_login(client, app_context):
    """Test login with invalid credentials."""
    # Try logging in with non-existent user
    login_data = {
        'username': 'nonexistent',
        'password': 'wrongpass'
    }
    response = client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data 