import os
import json
import logging
import boto3
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
from flask.cli import with_appcontext
import click

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Version information - will be set by setuptools-scm
try:
    from ._version import __version__
except ImportError:
    # Fallback if _version.py doesn't exist yet
    __version__ = "0.0.0"
    __version__ = "development"

version = {"app": __version__}

# Load environment variables
try:
    load_dotenv()
    logger.info("Environment variables loaded successfully")
except Exception as e:
    logger.error(f"Failed to load environment variables: {str(e)}")
    raise

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app(config_class=None):
    logger.info("Creating Flask application...")

    # Configure instance path for AWS Lambda
    instance_path = None
    if os.environ.get("AWS_EXECUTION_ENV"):
        import tempfile

        instance_path = os.path.join(tempfile.gettempdir(), "meal_expense_instance")
        os.makedirs(instance_path, exist_ok=True)
        logger.info(f"Created temporary instance directory at {instance_path}")

    app = Flask(__name__, instance_path=instance_path)

    # Configure the app
    if config_class:
        logger.info(f"Using config class: {config_class.__name__}")
        app.config.from_object(config_class)
    else:
        logger.info("Using default configuration")
        app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())

        # Use DATABASE_URL if set, otherwise fall back to SQLite
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            # Ensure proper PostgreSQL URL format
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            app.config["SQLALCHEMY_DATABASE_URI"] = db_url
            logger.info(f"Using PostgreSQL database: {db_url.split('@')[-1]}")
        else:
            # Use SQLite for local development
            os.makedirs(app.instance_path, exist_ok=True)
            db_path = os.path.join(app.instance_path, "meal_expenses.db")
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
            logger.info(f"Using SQLite database at {db_path}")

        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["GOOGLE_MAPS_API_KEY"] = os.getenv("GOOGLE_MAPS_API_KEY")
        app.config["SERVER_NAME"] = "localhost:5001"
        logger.info(
            f"Google Maps API Key: "
            f"{'set' if app.config['GOOGLE_MAPS_API_KEY'] else 'not set'}"
        )
        logger.info("Server name: localhost:5001")

    # Initialize extensions with app
    logger.info("Initializing extensions...")
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Import models after extensions are initialized

    # Register blueprints
    from app.auth import bp as auth_bp
    from app.health import bp as health_bp
    from app.restaurants import bp as restaurants_bp
    from app.expenses import bp as expenses_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(health_bp)
    app.register_blueprint(restaurants_bp, url_prefix="/restaurants")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")

    # Register main routes
    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    @click.command("init-db")
    @with_appcontext
    def init_db_command():
        """Clear the existing data and create new tables."""
        db.drop_all()
        db.create_all()
        click.echo("Initialized the database.")

    # Register the command with your Flask app
    app.cli.add_command(init_db_command)

    return app


def get_db_credentials():
    if os.getenv("FLASK_ENV") in ["development", "testing"]:
        return {
            "username": "sqlite_user",
            "password": "sqlite_password",
            "database_url": "sqlite:///instance/meal_expenses.db",
        }

    secrets_manager = boto3.client(
        "secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    secret_arn = os.getenv("DB_SECRET_ARN")

    response = secrets_manager.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])

    return {
        "username": secret["username"],
        "password": secret["password"],
        "database_url": (
            f"postgresql://{secret['username']}:{secret['password']}@"
            f"{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
        ),
    }
