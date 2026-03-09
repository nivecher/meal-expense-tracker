"""Tests for loyalty routes."""

from flask import url_for

from app.auth.models import User
from app.extensions import db
from app.loyalty.models import MerchantRewardsLink, RewardsProgram
from app.merchants.models import Merchant


def _enable_advanced_features(user: User) -> None:
    user.advanced_features_enabled = True
    db.session.add(user)
    db.session.commit()


def test_loyalty_list_requires_advanced_feature(client, auth, test_user) -> None:
    """Loyalty pages should be advanced-only."""
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("loyalty.list_rewards_programs"), follow_redirects=True)

    assert response.status_code == 200
    assert b"Loyalty is an advanced feature" in response.data


def test_loyalty_list_and_create_program(client, auth, test_user) -> None:
    """User should be able to create and view a rewards program."""
    _enable_advanced_features(test_user)
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("loyalty.new_rewards_program"),
        data={
            "name": "Starbucks Rewards",
            "website": "https://www.starbucks.com",
            "portal_url": "https://www.starbucks.com/account/signin",
            "membership_email": "testuser_1@example.com",
            "account_number": "ABC123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Starbucks Rewards" in response.data
    assert db.session.query(RewardsProgram).filter_by(name="Starbucks Rewards", user_id=test_user.id).count() == 1


def test_create_loyalty_from_merchant_prefills_website_and_links_merchant(client, auth, test_user) -> None:
    """Creating loyalty from a merchant should prefill website and link that merchant."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Starbucks", website="https://www.starbucks.com")
    db.session.add(merchant)
    db.session.commit()

    auth.login("testuser_1", "testpass")

    response = client.get(url_for("loyalty.new_rewards_program", merchant_id=merchant.id))
    assert response.status_code == 200
    assert b"https://www.starbucks.com" in response.data

    response = client.post(
        url_for("loyalty.new_rewards_program"),
        data={
            "name": "Starbucks Rewards",
            "website": "https://www.starbucks.com",
            "merchant_id": str(merchant.id),
            "membership_email": "testuser_1@example.com",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    program = db.session.query(RewardsProgram).filter_by(name="Starbucks Rewards", user_id=test_user.id).one()
    link = (
        db.session.query(MerchantRewardsLink)
        .filter_by(
            user_id=test_user.id,
            merchant_id=merchant.id,
            rewards_program_id=program.id,
        )
        .one_or_none()
    )
    assert link is not None


def test_merchant_detail_shows_rewards_link(client, auth, test_user) -> None:
    """Merchant detail should show linked rewards program for the current user."""
    _enable_advanced_features(test_user)
    program = RewardsProgram(user_id=test_user.id, name="Chipotle Rewards")
    merchant = Merchant(name="Chipotle Mexican Grill", short_name="Chipotle", category="fast_food_unit")
    db.session.add_all([program, merchant])
    db.session.commit()
    db.session.add(MerchantRewardsLink(user_id=test_user.id, merchant_id=merchant.id, rewards_program_id=program.id))
    db.session.commit()

    auth.login("testuser_1", "testpass")
    response = client.get(url_for("merchants.view_merchant", merchant_id=merchant.id))

    assert response.status_code == 200
    assert b"Chipotle Rewards" in response.data
    assert b"View Rewards" in response.data


def test_loyalty_detail_only_lists_unlinked_merchants_in_picker(client, auth, test_user) -> None:
    """Rewards detail merchant picker should exclude merchants already linked to any rewards program."""
    _enable_advanced_features(test_user)
    viewed_program = RewardsProgram(user_id=test_user.id, name="Viewed Program")
    other_program = RewardsProgram(user_id=test_user.id, name="Other Program")
    linked_merchant = Merchant(name="Linked Merchant")
    available_merchant = Merchant(name="Available Merchant")
    db.session.add_all([viewed_program, other_program, linked_merchant, available_merchant])
    db.session.commit()
    db.session.add(
        MerchantRewardsLink(
            user_id=test_user.id,
            merchant_id=linked_merchant.id,
            rewards_program_id=other_program.id,
        )
    )
    db.session.commit()

    auth.login("testuser_1", "testpass")
    response = client.get(url_for("loyalty.view_rewards_program", program_id=viewed_program.id))

    assert response.status_code == 200
    assert b"Available Merchant" in response.data
    assert b'<option value="%d">Linked Merchant</option>' % linked_merchant.id not in response.data
