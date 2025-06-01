from app import db


class Restaurant(db.Model):
    __tablename__ = "restaurant"
    __table_args__ = (
        db.UniqueConstraint("name", "city", name="uix_restaurant_name_city"),
    )
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))
    description = db.Column(db.Text)
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    price_range = db.Column(db.String(10))
    cuisine = db.Column(db.String(100))
    website = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    expenses = db.relationship("Expense", backref="restaurant", lazy=True)

    @property
    def full_name(self):
        return f"{self.name} - {self.city}" if self.city else self.name

    @property
    def full_address(self):
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.zip_code:
            parts.append(self.zip_code)
        return ", ".join(parts) if parts else None

    @property
    def google_search(self):
        parts = []
        if self.name:
            parts.append(self.name)
        if self.full_address:
            parts.append(self.full_address)
        return ", ".join(parts) if parts else None

    def __repr__(self):
        return f"<Restaurant {self.name}>"
