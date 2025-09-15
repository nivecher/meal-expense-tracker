from flask import url_for


def test_get_profile(client, test_user):
    """Test getting user profile page."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    response = client.get(url_for("auth.profile"))
    assert response.status_code == 200
    # Profile endpoint returns HTML, not JSON
    assert test_user.username.encode() in response.data


def test_update_profile(client, test_user):
    """Test updating user profile via form submission."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    response = client.post(
        url_for("auth.profile"),
        data={"username": "newusername", "email": "newemail@example.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Check that the new username appears in the response
    assert b"newusername" in response.data


def test_change_password(client, test_user):
    """Test changing user password via form submission."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    response = client.post(
        url_for("auth.change_password"),
        data={"old_password": "testpass", "new_password": "newpassword"},
        follow_redirects=True,
    )
    assert response.status_code == 200
