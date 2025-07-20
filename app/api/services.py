"""API-specific service functions."""

from app.expenses.models import Category, Expense
from app.extensions import db
from app.restaurants.models import Restaurant


def get_expenses_for_user(user_id):
    """Get all expenses for a given user."""
    return Expense.query.filter_by(user_id=user_id).all()


def create_expense_for_user(user_id, data):
    """Create a new expense for a given user."""
    expense = Expense(user_id=user_id, **data)
    db.session.add(expense)
    db.session.commit()
    return expense


def get_expense_by_id_for_user(expense_id, user_id):
    """Get a single expense by ID for a given user."""
    return Expense.query.filter_by(id=expense_id, user_id=user_id).first_or_404()


def update_expense_for_user(expense, data):
    """Update an expense for a given user."""
    for key, value in data.items():
        setattr(expense, key, value)
    db.session.commit()
    return expense


def delete_expense_for_user(expense):
    """Delete an expense for a given user."""
    db.session.delete(expense)
    db.session.commit()


def get_restaurants_for_user(user_id):
    """Get all restaurants for a given user."""
    return Restaurant.query.filter_by(user_id=user_id).all()


def create_restaurant_for_user(user_id, data):
    """
    Create a new restaurant for a given user.

    Args:
        user_id: ID of the user creating the restaurant
        data: Dictionary containing restaurant data (may include form fields like 'submit')
    """
    # Get the column names from the Restaurant model
    model_columns = {column.name for column in Restaurant.__table__.columns}

    # Filter the data to only include valid model fields
    valid_data = {k: v for k, v in data.items() if k in model_columns}

    # Handle empty strings for numeric fields
    for field in ["latitude", "longitude"]:
        if field in valid_data and valid_data[field] == "":
            valid_data[field] = None

    # Create the restaurant with only valid fields
    restaurant = Restaurant(user_id=user_id, **valid_data)
    db.session.add(restaurant)
    db.session.commit()
    return restaurant


def update_restaurant_for_user(restaurant, data):
    """
    Update a restaurant for a given user.

    Args:
        restaurant: Restaurant instance to update
        data: Dictionary containing restaurant data to update
    """
    # Get the column names from the Restaurant model
    model_columns = {column.name for column in Restaurant.__table__.columns}

    # Update only valid model fields
    for key, value in data.items():
        if key in model_columns and key != "id":  # Don't update the ID
            # Handle empty strings for numeric fields
            if key in ["latitude", "longitude"] and value == "":
                setattr(restaurant, key, None)
            else:
                setattr(restaurant, key, value)

    db.session.commit()
    return restaurant


def delete_restaurant_for_user(restaurant):
    """Delete a restaurant for a given user."""
    db.session.delete(restaurant)
    db.session.commit()


def export_restaurants_for_user(user_id):
    """
    Export all restaurants for a given user as a list of dictionaries.

    Args:
        user_id: ID of the user whose restaurants to export

    Returns:
        List of dictionaries containing restaurant data
    """
    restaurants = get_restaurants_for_user(user_id)
    return [
        {
            "name": r.name,
            "type": r.type,
            "address": r.address,
            "city": r.city,
            "phone": r.phone,
            "website": r.website,
            "cuisine": r.cuisine,
            "price_range": r.price_range,
            "notes": r.notes,
        }
        for r in restaurants
    ]


def import_restaurants_for_user(user_id, restaurants_data):
    """
    Import restaurants for a given user from a list of dictionaries.

    Args:
        user_id: ID of the user to import restaurants for
        restaurants_data: List of dictionaries containing restaurant data

    Returns:
        Tuple of (success_count, error_count, errors)
    """
    success_count = 0
    error_count = 0
    errors = []

    for idx, data in enumerate(restaurants_data, 1):
        try:
            # Skip if required fields are missing
            if not data.get("name"):
                errors.append(f'Row {idx}: Missing required field "name"')
                error_count += 1
                continue

            # Create the restaurant
            restaurant = Restaurant(user_id=user_id, **data)
            db.session.add(restaurant)
            success_count += 1

        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")
            error_count += 1

    if success_count > 0:
        db.session.commit()

    return success_count, error_count, errors


def update_user_profile(user, data):
    """Update a user's profile."""
    for key, value in data.items():
        if key in ["username", "email"]:
            setattr(user, key, value)
    db.session.commit()
    return user


def change_user_password(user, old_password, new_password):
    """Change a user's password."""
    if not user.check_password(old_password):
        return False, "Invalid old password."
    user.set_password(new_password)
    db.session.commit()
    return True, "Password updated successfully."


def get_categories_for_user(user_id):
    """Get all categories for a given user."""
    return Category.query.filter_by(user_id=user_id).all()


def create_category_for_user(user_id, data):
    """Create a new category for a given user."""
    category = Category(user_id=user_id, **data)
    db.session.add(category)
    db.session.commit()
    return category


def get_category_by_id_for_user(category_id, user_id):
    """Get a single category by ID for a given user."""
    return Category.query.filter_by(id=category_id, user_id=user_id).first_or_404()


def update_category_for_user(category, data):
    """Update a category for a given user."""
    for key, value in data.items():
        setattr(category, key, value)
    db.session.commit()
    return category


def delete_category_for_user(category):
    """Delete a category for a given user."""
    db.session.delete(category)
    db.session.commit()
