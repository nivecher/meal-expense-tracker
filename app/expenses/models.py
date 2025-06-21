from app import db
from datetime import datetime, UTC


class Expense(db.Model):
    __tablename__ = "expense"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    meal_type = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurant.id"))

    def __repr__(self):
        return f"<Expense {self.id}: {self.amount} on {self.date}>"
