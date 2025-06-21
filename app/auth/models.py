from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    expenses = db.relationship("Expense", backref="user", lazy="dynamic")

    def set_password(self, password):
        # Use the default hashing method (pbkdf2:sha256) with a reasonable work factor
        # This is the most reliable approach across different Werkzeug versions
        self.password_hash = generate_password_hash(
            password, method="pbkdf2:sha256", salt_length=16
        )

    def check_password(self, password):
        # Verify the password against the stored hash
        # This will work with any hash format that Werkzeug supports
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


def init_login_manager(login_manager_instance):
    """Initialize the login manager with the user loader.

    This function should be called during application initialization.
    """

    @login_manager_instance.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
