import pytest
from app import db, Restaurant, Expense
from datetime import datetime

def test_expense_creation_and_listing(auth_client):
    """Test creating expenses and listing them."""
    # First create a restaurant
    restaurant_data = {
        'name': 'Test Restaurant',
        'address': '123 Test St',
        'category': 'restaurant',
        'chain': 'Test Chain',
        'description': 'A test restaurant'
    }
    
    response = auth_client.post('/add_restaurant', data=restaurant_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Get the restaurant ID
    with auth_client.application.app_context():
        restaurant = Restaurant.query.filter_by(name='Test Restaurant').first()
        assert restaurant is not None
        restaurant_id = restaurant.id
    
    # Create multiple expenses
    expenses = [
        {
            'restaurant_id': restaurant_id,
            'amount': '25.50',
            'date': '2024-03-15',
            'description': 'Lunch'
        },
        {
            'restaurant_id': restaurant_id,
            'amount': '45.75',
            'date': '2024-03-16',
            'description': 'Dinner'
        }
    ]
    
    # Add expenses
    for expense in expenses:
        response = auth_client.post('/add_expense', data=expense, follow_redirects=True)
        assert response.status_code == 200
        assert b'Expense added successfully' in response.data
    
    # View expenses
    response = auth_client.get('/expenses')
    assert response.status_code == 200
    
    # Verify expenses in database
    with auth_client.application.app_context():
        stored_expenses = Expense.query.all()
        assert len(stored_expenses) == 2
        assert any(e.amount == 25.50 and e.description == 'Lunch' for e in stored_expenses)
        assert any(e.amount == 45.75 and e.description == 'Dinner' for e in stored_expenses)

def test_expense_edit_flow(auth_client):
    """Test the complete flow of creating, editing, and verifying an expense."""
    # Create a restaurant
    restaurant_data = {
        'name': 'Edit Test Restaurant',
        'address': '123 Edit St',
        'category': 'restaurant',
        'chain': 'Edit Chain',
        'description': 'For editing test'
    }
    
    response = auth_client.post('/add_restaurant', data=restaurant_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Get the restaurant ID
    with auth_client.application.app_context():
        restaurant = Restaurant.query.filter_by(name='Edit Test Restaurant').first()
        assert restaurant is not None
        restaurant_id = restaurant.id
    
    # Create an expense
    expense_data = {
        'restaurant_id': restaurant_id,
        'amount': '30.00',
        'date': '2024-03-17',
        'description': 'Original expense'
    }
    
    response = auth_client.post('/add_expense', data=expense_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Get the expense ID
    with auth_client.application.app_context():
        expense = Expense.query.filter_by(description='Original expense').first()
        assert expense is not None
        expense_id = expense.id
    
    # Edit the expense
    updated_data = {
        'restaurant_id': restaurant_id,
        'amount': '35.50',
        'date': '2024-03-18',
        'description': 'Updated expense'
    }
    
    response = auth_client.post(f'/edit_expense/{expense_id}', 
                              data=updated_data,
                              follow_redirects=True)
    assert response.status_code == 200
    assert b'Expense updated successfully' in response.data
    
    # Verify the update
    with auth_client.application.app_context():
        updated_expense = Expense.query.get(expense_id)
        assert updated_expense.amount == 35.50
        assert updated_expense.description == 'Updated expense'
        assert updated_expense.date.strftime('%Y-%m-%d') == '2024-03-18'

def test_expense_deletion(auth_client):
    """Test creating and deleting an expense."""
    # Create a restaurant
    restaurant_data = {
        'name': 'Delete Test Restaurant',
        'address': '123 Delete St',
        'category': 'restaurant',
        'chain': 'Delete Chain',
        'description': 'For deletion test'
    }
    
    response = auth_client.post('/add_restaurant', data=restaurant_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Get the restaurant ID
    with auth_client.application.app_context():
        restaurant = Restaurant.query.filter_by(name='Delete Test Restaurant').first()
        assert restaurant is not None
        restaurant_id = restaurant.id
    
    # Create an expense
    expense_data = {
        'restaurant_id': restaurant_id,
        'amount': '40.00',
        'date': '2024-03-19',
        'description': 'To be deleted'
    }
    
    response = auth_client.post('/add_expense', data=expense_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Get the expense ID
    with auth_client.application.app_context():
        expense = Expense.query.filter_by(description='To be deleted').first()
        assert expense is not None
        expense_id = expense.id
    
    # Delete the expense
    response = auth_client.post(f'/delete_expense/{expense_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Expense deleted successfully' in response.data
    
    # Verify deletion
    with auth_client.application.app_context():
        deleted_expense = Expense.query.get(expense_id)
        assert deleted_expense is None 