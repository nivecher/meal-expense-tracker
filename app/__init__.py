from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import click
from flask.cli import with_appcontext
import boto3
import json

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app(config_class=None):
    app = Flask(__name__)

    # Configure the app
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config["SECRET_KEY"] = os.urandom(24)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meal_expenses.db"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["GOOGLE_MAPS_API_KEY"] = os.getenv("GOOGLE_MAPS_API_KEY")

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Import models after extensions are initialized
    from app.auth import models as auth_models
    from app.restaurants import models as restaurant_models
    from app.expenses import models as expense_models

    # Register blueprints
    from app.auth import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.restaurants import bp as restaurants_bp

    app.register_blueprint(restaurants_bp, url_prefix="/restaurants")

    from app.expenses import bp as expenses_bp

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
