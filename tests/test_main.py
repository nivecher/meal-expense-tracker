def test_index(client):
    """Test the index page."""
    response = client.get("/")
    assert response.status_code == 302  # Redirect to login
    assert "/auth/login" in response.headers["Location"]


def test_index_redirects_to_login(client):
    """Test that index page redirects to login when not authenticated."""
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_index_with_expenses(client, auth):
    """Test index page with expenses."""
    auth.login()
    # Add a restaurant and expense
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
    )

    # Add an expense
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "category": "Food",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # Check the index page
    response = client.get("/")
    assert response.status_code == 200
    assert b"Test Restaurant" in response.data


def test_index_sorting(client, auth):
    """Test index page sorting."""
    auth.login()
    # Add a restaurant and multiple expenses
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
    )

    # Add expenses with different amounts
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "category": "Food",
            "amount": "15.50",
            "notes": "Cheaper expense",
        },
    )

    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-21",
            "meal_type": "Dinner",
            "category": "Food",
            "amount": "35.50",
            "notes": "More expensive expense",
        },
    )

    # Test sorting by amount
    response = client.get("/?sort=amount&order=asc")
    assert response.status_code == 200
    assert b"15.50" in response.data
    assert b"35.50" in response.data


def test_index_search(client, auth):
    """Test index page search functionality."""
    auth.login()
    # Add a restaurant and expense
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
    )

    # Add an expense
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "category": "Food",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # Test search functionality
    response = client.get("/?search=Test")
    assert response.status_code == 200
    assert b"Test Restaurant" in response.data
