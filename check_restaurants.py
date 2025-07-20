"""Script to check restaurant count in the database."""

from app import create_app
from app.extensions import db
from app.restaurants.models import Restaurant


def main():
    """Print the number of restaurants in the database."""
    app = create_app()
    with app.app_context():
        count = db.session.query(Restaurant).count()
        print(f"Total restaurants: {count}")


if __name__ == "__main__":
    main()
