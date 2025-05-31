from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    Response,
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import (  # type: ignore
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
import click
from dotenv import load_dotenv
import csv
import io

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meal_expenses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["GOOGLE_MAPS_API_KEY"] = os.getenv("GOOGLE_MAPS_API_KEY")

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)


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

    def __repr__(self):
        return f"<Restaurant {self.name}>"


class User(UserMixin, db.Model):  # type: ignore
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    expenses = db.relationship("Expense", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Expense(db.Model):  # type: ignore
    __tablename__ = "expense"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    meal = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurant.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@app.cli.command("init-db")
def init_db_command():
    """Initialize the database."""
    db.create_all()
    click.echo("Initialized the database.")


# Initialize database on startup
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def apply_filters(query, request_args):
    search = request_args.get("search", "")
    meal = request_args.get("meal", "")
    category = request_args.get("category", "")
    start_date = request_args.get("start_date", "")
    end_date = request_args.get("end_date", "")

    if search:
        query = query.join(Restaurant).filter(
            db.or_(
                Restaurant.name.ilike(f"%{search}%"),
                Restaurant.address.ilike(f"%{search}%"),
                Expense.description.ilike(f"%{search}%"),
            )
        )
    if meal:
        query = query.filter(Expense.meal == meal)
    if category:
        query = query.filter(Expense.category == category)
    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, "%Y-%m-%d"))
    return query


def apply_sorting(query, sort_by, sort_order):
    if sort_by == "date":
        query = query.order_by(
            Expense.date.desc() if sort_order == "desc" else Expense.date.asc()
        )
    elif sort_by == "amount":
        query = query.order_by(
            Expense.amount.desc() if sort_order == "desc" else Expense.amount.asc()
        )
    elif sort_by == "meal":
        query = query.order_by(
            Expense.meal.desc() if sort_order == "desc" else Expense.meal.asc()
        )
    elif sort_by == "category":
        query = query.order_by(
            Expense.category.desc() if sort_order == "desc" else Expense.category.asc()
        )
    elif sort_by == "restaurant":
        query = query.join(Restaurant).order_by(
            Restaurant.name.desc() if sort_order == "desc" else Restaurant.name.asc()
        )
    return query


@app.route("/")
@login_required
def index():
    # Get filter parameters
    search = request.args.get("search", "")
    meal = request.args.get("meal", "")
    category = request.args.get("category", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    sort_by = request.args.get("sort", "date")
    sort_order = request.args.get("order", "desc")

    # Base query
    query = Expense.query.filter_by(user_id=current_user.id)

    # Apply filters
    query = apply_filters(query, request.args)

    # Apply sorting
    query = apply_sorting(query, sort_by, sort_order)

    expenses = query.all()

    # Calculate total amount
    total_amount = sum(expense.amount for expense in expenses) if expenses else 0.0

    # Get unique meal types and categories for filter dropdowns
    meal_types = (
        db.session.query(Expense.meal).distinct().filter(Expense.meal != "").all()
    )
    meal_types = [meal[0] for meal in meal_types]
    categories = (
        db.session.query(Expense.category)
        .distinct()
        .filter(Expense.category != "")
        .all()
    )
    categories = [category[0] for category in categories]

    return render_template(
        "index.html",
        expenses=expenses,
        search=search,
        meal=meal,
        category=category,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
        meal_types=meal_types,
        categories=categories,
        total_amount=total_amount,
    )


@app.route("/restaurants")
@login_required
def restaurants():
    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.address).all()
    return render_template("restaurants.html", restaurants=restaurants)


@app.route("/add_restaurant", methods=["GET", "POST"])
@login_required
def add_restaurant():
    if request.method == "POST":
        name = request.form.get("name")
        type = request.form.get("type")
        description = request.form.get("description")
        address = request.form.get("address")
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip_code")
        price_range = request.form.get("price_range")
        cuisine = request.form.get("cuisine")
        website = request.form.get("website")
        phone = request.form.get("phone")
        notes = request.form.get("notes")

        # Check if restaurant with same name and city already exists
        existing_restaurant = Restaurant.query.filter_by(name=name, city=city).first()
        if existing_restaurant:
            flash("A restaurant with this name already exists in this city.", "danger")
            return redirect(url_for("add_restaurant"))

        restaurant = Restaurant(
            name=name,
            type=type,
            description=description,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            price_range=price_range,
            cuisine=cuisine,
            website=website,
            phone=phone,
            notes=notes,
        )
        db.session.add(restaurant)
        db.session.commit()
        flash("Restaurant added successfully!", "success")
        return redirect(url_for("restaurants"))
    return render_template("add_restaurant.html")


@app.route("/edit_restaurant/<int:restaurant_id>", methods=["GET", "POST"])
@login_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    if request.method == "POST":
        name = request.form.get("name")
        type = request.form.get("type")
        description = request.form.get("description")
        address = request.form.get("address")
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip_code")
        price_range = request.form.get("price_range")
        cuisine = request.form.get("cuisine")
        website = request.form.get("website")
        phone = request.form.get("phone")
        notes = request.form.get("notes")

        # Check if another restaurant with same name and city exists
        existing_restaurant = Restaurant.query.filter(
            Restaurant.name == name,
            Restaurant.city == city,
            Restaurant.id != restaurant_id,
        ).first()
        if existing_restaurant:
            flash(
                "Another restaurant with this name already exists in this city.",
                "danger",
            )
            return redirect(url_for("edit_restaurant", restaurant_id=restaurant_id))

        restaurant.name = name
        restaurant.type = type
        restaurant.description = description
        restaurant.address = address
        restaurant.city = city
        restaurant.state = state
        restaurant.zip_code = zip_code
        restaurant.price_range = price_range
        restaurant.cuisine = cuisine
        restaurant.website = website
        restaurant.phone = phone
        restaurant.notes = notes

        db.session.commit()
        flash("Restaurant updated successfully!", "success")
        return redirect(url_for("restaurant_details", restaurant_id=restaurant.id))
    return render_template("edit_restaurant.html", restaurant=restaurant)


@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            if amount <= 0:
                flash("Amount must be greater than 0", "danger")
                return redirect(url_for("add_expense"))

            description = request.form.get("description", "").strip()
            meal = request.form.get("meal", "")
            category = request.form.get("category", "")
            restaurant_id = request.form.get("restaurant_id", type=int)

            if not restaurant_id:
                flash("Restaurant is required", "danger")
                return redirect(url_for("add_expense"))

            # Get restaurant's type if no category is specified
            if not category:
                restaurant = Restaurant.query.get(restaurant_id)
                if restaurant and restaurant.type:
                    # Map restaurant type to expense category
                    type_to_category = {
                        "restaurant": "Dining Out",
                        "cafe": "Coffee",
                        "bar": "Dining Out",
                        "meal_delivery": "Takeout",
                        "meal_takeaway": "Takeout",
                        "supermarket": "Groceries",
                        "grocery_or_supermarket": "Groceries",
                        "convenience_store": "Groceries",
                        "coffee_shop": "Coffee",
                        "bakery": "Snacks",
                        "dessert_shop": "Snacks",
                        "ice_cream_shop": "Snacks",
                        "other": "Other",
                    }
                    category = type_to_category.get(restaurant.type, "")

            date_str = request.form["date"]
            date = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now().date()
            min_date = today - timedelta(days=365)  # 1 year ago

            if date.date() > today:
                flash("Date cannot be in the future", "danger")
                return redirect(url_for("add_expense"))

            if date.date() < min_date:
                flash("Date cannot be more than 1 year ago", "danger")
                return redirect(url_for("add_expense"))

            expense = Expense(
                amount=amount,
                description=description,
                meal=meal,
                category=category,
                restaurant_id=restaurant_id,
                date=date,
                user_id=current_user.id,
            )

            db.session.add(expense)
            db.session.commit()
            flash("Expense added successfully!", "success")
            return redirect(url_for("index"))

        except ValueError:
            flash("Invalid input data", "danger")
            return redirect(url_for("add_expense"))

    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.address).all()
    today = datetime.now().strftime("%Y-%m-%d")
    min_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")  # 1 year ago
    default_restaurant_id = request.args.get("restaurant_id", type=int)
    return render_template(
        "add_expense.html",
        today=today,
        min_date=min_date,
        restaurants=restaurants,
        default_restaurant_id=default_restaurant_id,
    )


@app.route("/edit_expense/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        expense.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        expense.amount = float(request.form["amount"])
        expense.meal = request.form["meal"]
        expense.category = request.form["category"]
        expense.restaurant_id = int(request.form["restaurant_id"])
        expense.description = request.form["description"]

        db.session.commit()
        flash("Expense updated successfully!", "success")
        return redirect(url_for("index"))

    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.address).all()
    return render_template(
        "edit_expense.html", expense=expense, restaurants=restaurants
    )


@app.route("/delete_expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)

    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted successfully!", "success")
    return redirect(url_for("index"))


@app.route("/delete_restaurant/<int:restaurant_id>", methods=["POST"])
@login_required
def delete_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    # Check if restaurant has any expenses
    if Expense.query.filter_by(restaurant_id=restaurant.id).first():
        flash("Cannot delete restaurant with existing expenses!", "danger")
        return redirect(url_for("restaurants"))

    db.session.delete(restaurant)
    db.session.commit()
    flash("Restaurant deleted successfully!", "success")
    return redirect(url_for("restaurants"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("register"))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/restaurant/<int:restaurant_id>")
@login_required
def restaurant_details(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    # Get all expenses for this restaurant
    expenses = (
        Expense.query.filter_by(restaurant_id=restaurant_id, user_id=current_user.id)
        .order_by(Expense.date.desc())
        .all()
    )

    # Calculate summary statistics
    total_expenses = len(expenses)
    total_amount = sum(expense.amount for expense in expenses)
    avg_amount = total_amount / total_expenses if total_expenses > 0 else 0

    # Group expenses by meal type
    meal_stats = {}
    for expense in expenses:
        if expense.meal not in meal_stats:
            meal_stats[expense.meal] = {"count": 0, "amount": 0}
        meal_stats[expense.meal]["count"] += 1
        meal_stats[expense.meal]["amount"] += expense.amount

    return render_template(
        "restaurant_details.html",
        restaurant=restaurant,
        expenses=expenses,
        total_expenses=total_expenses,
        total_amount=total_amount,
        avg_amount=avg_amount,
        meal_stats=meal_stats,
    )


@app.route("/restaurants/export")
def export_restaurants():
    restaurants = Restaurant.query.all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "Name",
            "Address",
            "City",
            "State",
            "Zip Code",
            "Type",
            "Price Range",
            "Cuisine",
            "Website",
            "Phone",
            "Description",
            "Notes",
        ]
    )

    # Write data
    for restaurant in restaurants:
        writer.writerow(
            [
                restaurant.name,
                restaurant.address,
                restaurant.city,
                restaurant.state,
                restaurant.zip_code,
                restaurant.type,
                restaurant.price_range,
                restaurant.cuisine,
                restaurant.website,
                restaurant.phone,
                restaurant.description,
                restaurant.notes,
            ]
        )

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=restaurants.csv"},
    )


@app.route("/restaurants/import", methods=["GET", "POST"])
def import_restaurants():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file uploaded", "danger")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "danger")
            return redirect(request.url)

        if not file.filename.endswith(".csv"):
            flash("Please upload a CSV file", "danger")
            return redirect(request.url)

        try:
            return process_csv_import(file)
        except Exception as e:
            flash(f"Error importing restaurants: {str(e)}", "danger")
            return redirect(request.url)

    return render_template("import_restaurants.html")


def process_csv_import(file):
    """Process the CSV file and import restaurants."""
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    reader = csv.DictReader(stream)

    required_fields = ["Name", "Address", "City", "State", "Zip Code"]
    optional_fields = [
        "Type",
        "Price Range",
        "Cuisine",
        "Website",
        "Phone",
        "Description",
        "Notes",
    ]

    # Validate required fields
    for field in required_fields:
        if field not in reader.fieldnames:
            flash(f"Missing required field: {field}", "danger")
            return redirect(url_for("import_restaurants"))

    restaurants_added = 0
    for row in reader:
        if not is_restaurant_exists(row):
            add_restaurant_from_row(row)
            restaurants_added += 1

    db.session.commit()
    flash(f"Successfully imported {restaurants_added} restaurants", "success")
    return redirect(url_for("restaurants"))


def is_restaurant_exists(row):
    """Check if a restaurant with the same details already exists."""
    return (
        Restaurant.query.filter_by(
            name=row["Name"],
            address=row["Address"],
            city=row["City"],
            state=row["State"],
            zip_code=row["Zip Code"],
        ).first()
        is not None
    )


def add_restaurant_from_row(row):
    """Create and add a new restaurant from a CSV row."""
    restaurant = Restaurant(
        name=row["Name"],
        address=row["Address"],
        city=row["City"],
        state=row["State"],
        zip_code=row["Zip Code"],
        type=row.get("Type"),
        price_range=row.get("Price Range"),
        cuisine=row.get("Cuisine"),
        website=row.get("Website"),
        phone=row.get("Phone"),
        description=row.get("Description"),
        notes=row.get("Notes"),
    )
    db.session.add(restaurant)


if __name__ == "__main__":
    app.run(debug=True)
