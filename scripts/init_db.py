"""Initialize the database with required tables."""

from pathlib import Path
import sys

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def init_db() -> None:
    """Initialize the database by creating all tables."""
    from app import create_app
    from app.extensions import db

    # Create the Flask app
    app = create_app("development")

    # Create all database tables within the app context
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
