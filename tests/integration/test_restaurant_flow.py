import pytest
from app import db, Restaurant
import csv
from io import StringIO

def test_restaurant_creation_and_export(auth_client):
    """Test the complete flow of creating restaurants and exporting them."""
    # Create multiple restaurants
    restaurants = [
        {
            'name': 'Test Restaurant 1',
            'address': '123 Test St',
            'category': 'restaurant',
            'chain': 'Test Chain',
            'description': 'A test restaurant'
        },
        {
            'name': 'Test Restaurant 2',
            'address': '456 Test Ave',
            'category': 'cafe',
            'chain': 'Test Chain',
            'description': 'Another test restaurant'
        }
    ]
    
    # Add restaurants
    for restaurant in restaurants:
        response = auth_client.post('/add_restaurant', data=restaurant, follow_redirects=True)
        assert response.status_code == 200
        assert b'Restaurant added successfully' in response.data
    
    # Export restaurants
    response = auth_client.get('/export_restaurants')
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    
    # Parse CSV and verify content
    csv_data = response.data.decode('utf-8')
    csv_reader = csv.DictReader(StringIO(csv_data))
    exported_restaurants = list(csv_reader)
    
    assert len(exported_restaurants) == 2
    for restaurant in restaurants:
        assert any(r['Name'] == restaurant['name'] for r in exported_restaurants)

def test_restaurant_import_and_verification(auth_client):
    """Test importing restaurants and verifying they are stored correctly."""
    # Create CSV data
    csv_data = '''Name,Address,Category,Chain,Description
Test Restaurant 3,789 Test Blvd,restaurant,Test Chain,A test restaurant
Test Restaurant 4,321 Test Rd,cafe,Test Chain,Another test restaurant'''
    
    # Import restaurants
    response = auth_client.post('/import_restaurants', 
                              data={'file': (StringIO(csv_data), 'restaurants.csv')},
                              follow_redirects=True)
    assert response.status_code == 200
    assert b'Restaurants imported successfully' in response.data
    
    # Verify restaurants in database
    with auth_client.application.app_context():
        restaurants = Restaurant.query.all()
        assert len(restaurants) == 2
        assert any(r.name == 'Test Restaurant 3' for r in restaurants)
        assert any(r.name == 'Test Restaurant 4' for r in restaurants)

def test_restaurant_edit_flow(auth_client):
    """Test the complete flow of creating, editing, and verifying a restaurant."""
    # Create a restaurant
    restaurant_data = {
        'name': 'Original Restaurant',
        'address': '123 Original St',
        'category': 'restaurant',
        'chain': 'Original Chain',
        'description': 'Original description'
    }
    
    response = auth_client.post('/add_restaurant', data=restaurant_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Restaurant added successfully' in response.data
    
    # Get the restaurant ID
    with auth_client.application.app_context():
        restaurant = Restaurant.query.filter_by(name='Original Restaurant').first()
        assert restaurant is not None
        restaurant_id = restaurant.id
    
    # Edit the restaurant
    updated_data = {
        'name': 'Updated Restaurant',
        'address': '456 Updated St',
        'category': 'cafe',
        'chain': 'Updated Chain',
        'description': 'Updated description'
    }
    
    response = auth_client.post(f'/edit_restaurant/{restaurant_id}', 
                              data=updated_data,
                              follow_redirects=True)
    assert response.status_code == 200
    assert b'Restaurant updated successfully' in response.data
    
    # Verify the update
    with auth_client.application.app_context():
        updated_restaurant = Restaurant.query.get(restaurant_id)
        assert updated_restaurant.name == 'Updated Restaurant'
        assert updated_restaurant.address == '456 Updated St'
        assert updated_restaurant.category == 'cafe'
        assert updated_restaurant.chain == 'Updated Chain'
        assert updated_restaurant.description == 'Updated description' 