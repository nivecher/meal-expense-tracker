from flask import url_for

from app.expenses.models import Category


def test_create_category(client, test_user) -> None:
    """Test creating a category via API."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    response = client.post(
        url_for("api.create_category"),
        json={"name": "Test Category", "description": "A test category"},
    )
    assert response.status_code == 201
    assert response.json["data"]["name"] == "Test Category"


def test_create_category_invalid_data(client, test_user) -> None:
    """Test creating a category with invalid data."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    response = client.post(url_for("api.create_category"), json={"description": "This should fail"})
    assert response.status_code == 400


def test_get_categories(client, test_user, session) -> None:
    """Test getting categories via API."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    # Create a category
    category = Category(name="Test Category", user_id=test_user.id)
    session.add(category)
    session.commit()

    response = client.get(url_for("api.get_categories"))
    assert response.status_code == 200
    assert len(response.json["data"]) == 1


def test_get_category(client, test_user, session) -> None:
    """Test getting a specific category via API."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    # Create a category
    category = Category(name="Test Category", user_id=test_user.id)
    session.add(category)
    session.commit()

    response = client.get(url_for("api.get_category", category_id=category.id))
    assert response.status_code == 200
    assert response.json["data"]["name"] == "Test Category"


def test_update_category(client, test_user, session) -> None:
    """Test updating a category via API."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    # Create a category
    category = Category(name="Test Category", user_id=test_user.id)
    session.add(category)
    session.commit()

    response = client.put(
        url_for("api.update_category", category_id=category.id),
        json={"name": "Updated Category", "description": "An updated category"},
    )
    assert response.status_code == 200
    assert response.json["data"]["name"] == "Updated Category"


def test_delete_category(client, test_user, session) -> None:
    """Test deleting a category via API."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    # Create a category
    category = Category(name="Test Category", user_id=test_user.id)
    session.add(category)
    session.commit()

    response = client.delete(url_for("api.delete_category", category_id=category.id))
    assert response.status_code == 204

    # Verify the category is deleted
    response = client.get(url_for("api.get_category", category_id=category.id))
    assert response.status_code == 500  # API returns 500 for missing categories


def test_access_other_user_category(client, test_user, test_user2, session) -> None:
    """Test that users cannot access other users' categories."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    # Create a category for the other user
    category = Category(name="Other Users Category", user_id=test_user2.id)
    session.add(category)
    session.commit()

    # Try to access the category as the original user
    response = client.get(url_for("api.get_category", category_id=category.id))
    assert response.status_code == 500  # API returns 500 for missing categories
