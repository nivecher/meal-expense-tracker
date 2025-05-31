def test_app_health(client):
    """Test that the application is running and responding."""
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data  # Verify we're on the login page
