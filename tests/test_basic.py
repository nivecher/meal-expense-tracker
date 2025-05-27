import pytest
from app import app, db, User, Restaurant
from io import BytesIO

def test_index_page(client):
    """Test that the index page redirects to login when not authenticated."""
    response = client.get('/')
    assert response.status_code == 302
    assert '/login' in response.location

def test_login_page(client):
    """Test that the login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_login_functionality(auth_client):
    """Test that login works correctly."""
    response = auth_client.get('/')
    assert response.status_code == 200
    assert b'Expenses' in response.data

def test_restaurant_creation(auth_client):
    """Test that restaurants can be created."""
    response = auth_client.post('/add_restaurant', data={
        'name': 'Test Restaurant',
        'address': '123 Test St',
        'category': 'restaurant',
        'chain': 'Test Chain',
        'description': 'A test restaurant'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Restaurant added successfully' in response.data

def test_restaurant_export(auth_client):
    """Test that restaurant export works."""
    response = auth_client.get('/export_restaurants')
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert b'Name,Address,Category,Chain,Description' in response.data

def test_restaurant_import(auth_client):
    """Test that restaurant import works."""
    csv_data = 'Name,Address,Category,Chain,Description\nTest Restaurant,123 Test St,restaurant,Test Chain,A test restaurant'
    response = auth_client.post('/import_restaurants', data={
        'file': (BytesIO(csv_data.encode()), 'restaurants.csv')
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Restaurants imported successfully' in response.data 