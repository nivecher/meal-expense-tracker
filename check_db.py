"""Script to check database contents."""

from app import create_app
from app.expenses.models import Category
from app.restaurants.models import Restaurant


def check_database():
    """Check database contents and print summary."""
    app = create_app()
    with app.app_context():
        # Check restaurants
        restaurants = Restaurant.query.count()
        print(f"Total restaurants: {restaurants}")

        # Check categories
        categories = Category.query.count()
        print(f"Total categories: {categories}")

        # Print first few restaurants if they exist
        if restaurants > 0:
            print("\nSample restaurants:")
            for r in Restaurant.query.limit(5).all():
                print(f"- {r.name} (ID: {r.id})")

        # Print all categories
        if categories > 0:
            print("\nAll categories:")
            for cat in Category.query.order_by(Category.name).all():
                print(f"- {cat.name}")


if __name__ == "__main__":
    check_database()
