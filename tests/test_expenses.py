def test_expenses_list(client, auth):
    """Test expenses list page."""
    auth.login()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Meal Expenses" in response.data


def test_add_expense(client, auth):
    """Test adding an expense."""
    auth.login()
    # Add a restaurant first
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
    response = client.post(
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
    assert response.status_code == 200
    assert b"Expense added successfully!" in response.data
    assert b"25.50" in response.data


def test_edit_expense(client, auth):
    """Test editing an expense."""
    auth.login()
    # Add a restaurant first
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

    # Edit the expense
    response = client.post(
        "/expenses/1/edit",
        data={
            "restaurant_id": 1,
            "date": "2024-02-21",
            "meal_type": "Dinner",
            "category": "Food",
            "amount": "35.50",
            "notes": "Updated expense",
        },
    )
    assert response.status_code == 200
    assert b"Expense updated successfully!" in response.data
    assert b"35.50" in response.data


def test_delete_expense(client, auth):
    """Test deleting an expense."""
    auth.login()
    # Add a restaurant first
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

    # Delete the expense
    response = client.post("/expenses/1/delete")
    assert response.status_code == 200
    assert b"Expense deleted successfully!" in response.data


def test_expense_filters(client, auth):
    """Test expense filtering."""
    auth.login()
    # Add a restaurant first
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

    # Add expenses with different meal types
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "category": "Food",
            "amount": "25.50",
            "notes": "Today's lunch",
        },
    )

    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Dinner",
            "category": "Food",
            "amount": "35.50",
            "notes": "Today's dinner",
        },
    )

    # Test filtering by meal type
    response = client.get("/?meal_type=Lunch")
    assert response.status_code == 200
    assert b"25.50" in response.data
    assert b"35.50" not in response.data

    # Test filtering by date
    response = client.get("/?start_date=2024-02-20")
    assert response.status_code == 200
    assert b"25.50" in response.data
    assert b"35.50" in response.data
