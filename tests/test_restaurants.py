def test_restaurants_list(client, auth):
    """Test listing restaurants."""
    auth.login()
    response = client.get("/restaurants/")
    assert response.status_code == 200
    assert b"Restaurants" in response.data


def test_add_restaurant(client, auth):
    """Test adding a restaurant."""
    auth.login()
    response = client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Restaurant added successfully" in response.data


def test_edit_restaurant(client, auth):
    """Test editing a restaurant."""
    auth.login()
    # First add a restaurant
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

    # Edit the restaurant
    response = client.post(
        "/restaurants/1/edit",
        data={
            "name": "Updated Restaurant",
            "city": "Updated City",
            "address": "456 Updated St",
            "phone": "098-765-4321",
            "website": "http://updated.com",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Restaurant updated successfully" in response.data

    # Verify changes
    response = client.get("/restaurants/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated Restaurant" in response.data


def test_restaurant_details(client, auth):
    """Test viewing restaurant details."""
    auth.login()
    # First add a restaurant
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

    # View restaurant details
    response = client.get("/restaurants/1/details")
    assert response.status_code == 200
    assert b"Test Restaurant" in response.data
    assert b"Test City" in response.data
    assert b"123 Test St" in response.data


def test_delete_restaurant(client, auth):
    """Test deleting a restaurant."""
    auth.login()
    # First add a restaurant
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

    # Delete the restaurant
    response = client.post("/restaurants/1/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Restaurant deleted successfully" in response.data

    # Verify restaurant is deleted
    response = client.get("/restaurants/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Test Restaurant" not in response.data
