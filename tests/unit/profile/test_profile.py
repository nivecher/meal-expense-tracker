from flask import url_for
from flask.testing import FlaskClient

from app.auth.models import User


def test_get_profile(client: FlaskClient, test_user: User) -> None:
    """Test getting user profile page."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    response = client.get(url_for("auth.profile"))
    assert response.status_code == 200
    # Profile endpoint returns HTML, not JSON
    assert test_user.username.encode() in response.data


def test_update_profile(client: FlaskClient, test_user: User) -> None:
    """Test updating user profile via form submission."""
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)

    response = client.post(
        url_for("auth.profile"),
        data={
            "first_name": "NewFirstName",
            "last_name": "NewLastName",
            "display_name": "NewDisplayName",
            "bio": "New bio text",
            "phone": "123-456-7890",
            "timezone": "America/New_York",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Check that the new display name appears in the response
    assert b"NewDisplayName" in response.data


def test_change_password(client: FlaskClient, test_user: User) -> None:
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
