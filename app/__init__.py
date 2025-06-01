from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import click
from flask.cli import with_appcontext

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
