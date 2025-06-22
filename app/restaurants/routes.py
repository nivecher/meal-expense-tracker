# Standard library imports
import csv
from datetime import datetime
from io import StringIO, BytesIO

# Third-party imports
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import login_required
from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError

# Local application imports
from app.extensions import db
from app.expenses.models import Expense
from app.restaurants import bp
from app.restaurants.models import Restaurant

# Display names for restaurant types and cuisines
RESTAURANT_TYPE_DISPLAY_NAMES = {
    "sit_down": "Sit-down Restaurant",
    "fast_food": "Fast Food",
    "cafe": "Café",
    "diner": "Diner",
    "food_truck": "Food Truck",
    "buffet": "Buffet",
    "bar": "Bar/Pub",
    "pub": "Bar/Pub",
    "food_stand": "Food Stand",
    "other": "Other",
}

CUISINE_DISPLAY_NAMES = {
    "american": "American",
    "mexican": "Mexican",
    "italian": "Italian",
    "chinese": "Chinese",
    "japanese": "Japanese",
    "indian": "Indian",
    "mediterranean": "Mediterranean",
    "thai": "Thai",
    "vietnamese": "Vietnamese",
    "greek": "Greek",
    "korean": "Korean",
    "french": "French",
    "spanish": "Spanish",
    "middle_eastern": "Middle Eastern",
    "caribbean": "Caribbean",
    "african": "African",
    "latin_american": "Latin American",
    "asian": "Asian",
    "other": "Other",
}


def get_type_display_name(type_code):
    """Get the display name for a restaurant type code."""
    # Convert underscores to spaces and capitalize
    formatted_code = type_code.replace("_", " ").title()
    # Handle special cases
    if type_code.lower() == "cafe":
        return "Café"
    return RESTAURANT_TYPE_DISPLAY_NAMES.get(type_code.lower(), formatted_code)


def get_cuisine_display_name(cuisine_code):
    """Get the display name for a cuisine code."""
    return CUISINE_DISPLAY_NAMES.get(cuisine_code.lower(), cuisine_code.title())


@bp.route("/")
@login_required
def list_restaurants():
    # Get filter and sort parameters from query string
    search = request.args.get("search", "")
    cuisine = request.args.get("cuisine", "")
    city = request.args.get("city", "")
    type_ = request.args.get("type", "")
    price_range = request.args.get("price_range", "")
    sort_by = request.args.get("sort_by", "name")
    sort_order = request.args.get("sort_order", "asc")

    # Start query
    stmt = select(Restaurant)

    # Apply filters
    if search:
        stmt = stmt.where(Restaurant.name.ilike(f"%{search}%"))
    if cuisine:
        stmt = stmt.where(Restaurant.cuisine == cuisine)
    if city:
        stmt = stmt.where(Restaurant.city == city)
    if type_:
        stmt = stmt.where(Restaurant.type == type_)
    if price_range:
        stmt = stmt.where(Restaurant.price_range == price_range)

    # Apply sorting
    sort_column = getattr(Restaurant, sort_by, Restaurant.name)
    stmt = stmt.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())

    # Execute query
    restaurants = db.session.scalars(stmt).all()

    # For filter dropdowns
    def get_distinct_values(column):
        stmt = select(column).distinct().where(column.isnot(None))
        results = db.session.scalars(stmt).all()
        # Convert scalar results to a list directly
        return list(results)

    cuisines = get_distinct_values(Restaurant.cuisine)
    cities = get_distinct_values(Restaurant.city)
    types = get_distinct_values(Restaurant.type)
    price_ranges = get_distinct_values(Restaurant.price_range)

    return render_template(
        "restaurants/list_restaurants.html",
        restaurants=restaurants,
        search=search,
        cuisine=cuisine,
        city=city,
        type_=type_,
        price_range=price_range,
        sort_by=sort_by,
        sort_order=sort_order,
        cuisines=cuisines,
        cities=cities,
        types=types,
        price_ranges=price_ranges,
        get_cuisine_display_name=get_cuisine_display_name,
        get_type_display_name=get_type_display_name,
    )


@bp.route("/<int:restaurant_id>/details")
@login_required
def restaurant_details(restaurant_id):
    """Display details for a specific restaurant.

    Args:
        restaurant_id: The ID of the restaurant to display

    Returns:
        Rendered template with restaurant details and expenses
    """
    try:
        # First, get the restaurant
        restaurant = db.session.get(Restaurant, restaurant_id)
        if not restaurant:
            abort(404)

        # Then get its expenses
        stmt = (
            select(Expense)
            .where(Expense.restaurant_id == restaurant_id)
            .order_by(Expense.date.desc() if Expense.date is not None else None)
        )
        expenses = db.session.scalars(stmt).all()

        # Get restaurant type and cuisine display names
        type_display = get_type_display_name(restaurant.type)
        cuisine_display = get_cuisine_display_name(restaurant.cuisine) if restaurant.cuisine else ""

        return render_template(
            "restaurants/restaurant_details.html",
            restaurant=restaurant,
            expenses=expenses,
            type_display=type_display,
            cuisine_display=cuisine_display,
        )

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in restaurant_details: {str(e)}", exc_info=True)
        flash("Error loading restaurant details. Please try again.", "error")
        abort(500)


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_restaurant():
    """Add a new restaurant to the database.

    Handles both GET (display form) and POST (process form) requests.
    """
    if request.method == "POST":
        try:
            # Validate required fields
            required_fields = ["name", "address", "city"]
            for field in required_fields:
                if not request.form.get(field):
                    flash(f"{field.title()} is required", "error")
                    return render_template("restaurants/add_restaurant.html")

            # Check for duplicate restaurant using SQLAlchemy 2.0 style
            stmt = select(Restaurant).where(
                db.func.lower(Restaurant.name) == request.form["name"].lower(),
                db.func.lower(Restaurant.city) == request.form["city"].lower(),
            )
            existing_restaurant = db.session.scalars(stmt).first()

            if existing_restaurant:
                flash("A restaurant with this name already exists in this city.", "error")
                return render_template("restaurants/add_restaurant.html")

            # Create new restaurant
            restaurant = Restaurant(
                name=request.form["name"].strip(),
                type=request.form.get("type", "restaurant"),
                description=request.form.get("description", "").strip(),
                address=request.form["address"].strip(),
                city=request.form["city"].strip(),
                state=request.form.get("state", "").strip(),
                zip_code=request.form.get("zip_code", "").strip(),
                price_range=request.form.get("price_range", "").strip(),
                cuisine=request.form.get("cuisine", "").strip(),
                website=request.form.get("website", "").strip(),
                phone=request.form.get("phone", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            db.session.add(restaurant)
            db.session.commit()

            # Verify restaurant was created successfully
            stmt = select(Restaurant).where(Restaurant.name == request.form["name"].strip())
            created_restaurant = db.session.scalars(stmt).first()
            if not created_restaurant:
                raise SQLAlchemyError("Restaurant was not created successfully")

            flash("Restaurant added successfully!", "success")
            return redirect(url_for("restaurants.list_restaurants"))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error adding restaurant: {str(e)}", "error")
            return render_template("restaurants/add_restaurant.html")
    return render_template("restaurants/add_restaurant.html")


@bp.route("/<int:restaurant_id>/edit", methods=["GET", "POST"])
@login_required
def edit_restaurant(restaurant_id):
    """Edit an existing restaurant.

    Args:
        restaurant_id: The ID of the restaurant to edit

    Returns:
        Rendered template with edit form (GET) or redirects to restaurant details (POST)
    """
    # Get restaurant using SQLAlchemy 2.0 style
    restaurant = db.session.get(Restaurant, restaurant_id)
    if restaurant is None:
        abort(404)

    if request.method == "POST":
        try:
            # Check for duplicate restaurant (excluding current one)
            stmt = select(Restaurant).where(
                db.func.lower(Restaurant.name) == request.form["name"].lower(),
                db.func.lower(Restaurant.city) == request.form["city"].lower(),
                Restaurant.id != restaurant_id,
            )
            existing_restaurant = db.session.scalars(stmt).first()

            if existing_restaurant:
                flash("A restaurant with this name already exists in this city.", "error")
                return render_template("restaurants/edit_restaurant.html", restaurant=restaurant)

            # Update restaurant fields
            restaurant.name = request.form["name"].strip()
            restaurant.type = request.form.get("type", "restaurant").strip()
            restaurant.description = request.form.get("description", "").strip()
            restaurant.address = request.form["address"].strip()
            restaurant.city = request.form["city"].strip()
            restaurant.state = request.form.get("state", "").strip()
            restaurant.zip_code = request.form.get("zip_code", "").strip()
            restaurant.price_range = request.form.get("price_range", "").strip()
            restaurant.cuisine = request.form.get("cuisine", "").strip()
            restaurant.website = request.form.get("website", "").strip()
            restaurant.phone = request.form.get("phone", "").strip()
            restaurant.notes = request.form.get("notes", "").strip()

            db.session.commit()
            flash("Restaurant updated successfully.", "success")
            return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))

        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating restaurant: {str(e)}", exc_info=True)
            flash("An error occurred while updating the restaurant.", "error")

    return render_template("restaurants/edit_restaurant.html", restaurant=restaurant)


@bp.route("/<int:restaurant_id>/delete", methods=["POST"])
@login_required
def delete_restaurant(restaurant_id):
    """Delete a restaurant and all its associated expenses.

    Args:
        restaurant_id: The ID of the restaurant to delete

    Returns:
        Redirects to the restaurants list with a status message
    """
    try:
        # Get restaurant using SQLAlchemy 2.0 style
        restaurant = db.session.get(Restaurant, restaurant_id)
        if restaurant is None:
            flash("Restaurant not found.", "error")
            return redirect(url_for("restaurants.list_restaurants"))

        # Delete the restaurant (expenses are handled by cascade delete in the model)
        db.session.delete(restaurant)
        db.session.commit()

        flash("Restaurant and all associated expenses have been deleted.", "success")
        return redirect(url_for("restaurants.list_restaurants"))

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting restaurant {restaurant_id}: {str(e)}", exc_info=True)
        flash("An error occurred while deleting the restaurant.", "error")
        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant_id))


@bp.route("/search")
@login_required
def search_restaurants():
    """Search for restaurants based on a query string.

    Searches in restaurant name, city, and cuisine fields.

    Returns:
        Rendered template with search results or redirects to restaurants list
    """
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("restaurants.list_restaurants"))

    try:
        # Build the search query using SQLAlchemy 2.0 style
        stmt = (
            select(Restaurant)
            .where(
                or_(
                    db.func.lower(Restaurant.name).like(f"%{query.lower()}%"),
                    db.func.lower(Restaurant.city).like(f"%{query.lower()}%"),
                    db.func.lower(Restaurant.cuisine).like(f"%{query.lower()}%"),
                )
            )
            .order_by(Restaurant.name)
        )

        restaurants = db.session.scalars(stmt).all()

        return render_template(
            "restaurants/search_results.html",
            restaurants=restaurants,
            query=query,
            get_type_display_name=get_type_display_name,
            get_cuisine_display_name=get_cuisine_display_name,
        )

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error searching restaurants: {str(e)}", exc_info=True)
        flash("An error occurred during the search. Please try again.", "error")
        return redirect(url_for("restaurants.list_restaurants"))


@bp.route("/export")
@login_required
def export_restaurants():
    """Export all restaurants to a CSV file.

    Returns:
        CSV file download of all restaurants
    """
    try:
        # Get all restaurants using SQLAlchemy 2.0 style
        stmt = select(Restaurant).order_by(Restaurant.name)
        restaurants = db.session.scalars(stmt).all()

        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Name",
                "Type",
                "Description",
                "Address",
                "City",
                "State",
                "Zip Code",
                "Price Range",
                "Cuisine",
                "Website",
                "Phone",
                "Notes",
            ]
        )

        # Write data rows
        for restaurant in restaurants:
            writer.writerow(
                [
                    restaurant.name or "",
                    restaurant.type or "",
                    restaurant.description or "",
                    restaurant.address or "",
                    restaurant.city or "",
                    restaurant.state or "",
                    restaurant.zip_code or "",
                    restaurant.price_range or "",
                    restaurant.cuisine or "",
                    restaurant.website or "",
                    restaurant.phone or "",
                    restaurant.notes or "",
                ]
            )

        # Convert to bytes for download
        mem = BytesIO()
        mem.write(output.getvalue().encode("utf-8"))
        mem.seek(0)
        output.close()

        return send_file(
            mem,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"restaurants_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error exporting restaurants: {str(e)}", exc_info=True)
        flash("An error occurred while exporting restaurants. Please try again.", "error")
        return redirect(url_for("restaurants.list_restaurants"))


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_restaurants():
    """Display the import form or process uploaded CSV file."""
    if request.method == "GET":
        return render_template("restaurants/import_restaurants.html")
    return _process_restaurant_import()


def _process_restaurant_import():
    """Process the uploaded CSV file and import restaurants."""
    file = _get_uploaded_file()
    if not file:
        return redirect(request.url)

    try:
        csv_input = _read_csv_file(file)
        required_fields = ["Name", "Address", "City"]

        if not _validate_csv_headers(csv_input, required_fields):
            return redirect(request.url)

        imported, errors = _process_csv_rows(csv_input, required_fields)
        _show_import_results(imported, errors)

        return redirect(url_for("restaurants.list_restaurants"))

    except UnicodeDecodeError:
        _handle_import_error("Invalid file encoding. Please use UTF-8 encoding.")
    except csv.Error as e:
        _handle_import_error(f"Error parsing CSV file: {str(e)}")
    except SQLAlchemyError as e:
        _handle_import_error("A database error occurred during import. Please try again.", e)
    except Exception as e:
        _handle_import_error("An unexpected error occurred during import. Please try again.", e)

    return redirect(request.url)


def _get_uploaded_file():
    """Get and validate the uploaded file."""
    if "file" not in request.files:
        flash("No file selected", "error")
        return None

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected", "error")
        return None

    if not file.filename.lower().endswith(".csv"):
        flash("Please upload a CSV file", "error")
        return None

    return file


def _read_csv_file(file):
    """Read and parse the uploaded CSV file."""
    stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
    return csv.DictReader(stream)


def _validate_csv_headers(csv_input, required_fields):
    """Validate that the CSV contains all required fields."""
    for field in required_fields:
        if field not in csv_input.fieldnames:
            flash(f"Missing required field in CSV: {field}", "error")
            return False
    return True


def _process_csv_rows(csv_input, required_fields):
    """Process each row in the CSV and import restaurants."""
    imported = 0
    errors = []

    for i, row in enumerate(csv_input, 1):
        try:
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

            if not _validate_required_fields(row, required_fields, i, errors):
                continue

            if _is_duplicate_restaurant(row, i, errors):
                continue

            _create_restaurant(row)
            imported += 1

            if imported % 50 == 0:
                db.session.commit()

        except Exception as e:
            db.session.rollback()
            errors.append(f"Row {i}: {str(e)}")

    if imported % 50 != 0:
        db.session.commit()

    return imported, errors


def _validate_required_fields(row, required_fields, row_num, errors):
    """Validate that all required fields are present in the row."""
    missing_fields = [field for field in required_fields if not row.get(field)]
    if missing_fields:
        errors.append(f"Row {row_num}: Missing required fields: {', '.join(missing_fields)}")
        return False
    return True


def _is_duplicate_restaurant(row, row_num, errors):
    """Check if a restaurant with the same name and city already exists."""
    stmt = select(Restaurant).where(
        db.func.lower(Restaurant.name) == row["Name"].lower(), db.func.lower(Restaurant.city) == row["City"].lower()
    )
    existing = db.session.scalars(stmt).first()

    if existing:
        errors.append(f"Row {row_num}: Restaurant already exists: {row['Name']} in {row['City']}")
        return True
    return False


def _create_restaurant(row):
    """Create a new restaurant from a CSV row."""
    restaurant = Restaurant(
        name=row["Name"],
        type=row.get("Type", "restaurant"),
        description=row.get("Description", ""),
        address=row["Address"],
        city=row["City"],
        state=row.get("State", ""),
        zip_code=row.get("Zip Code", ""),
        price_range=row.get("Price Range", ""),
        cuisine=row.get("Cuisine", ""),
        website=row.get("Website", ""),
        phone=row.get("Phone", ""),
        notes=row.get("Notes", ""),
    )
    db.session.add(restaurant)


def _show_import_results(imported, errors):
    """Show the results of the import operation."""
    if errors:
        error_msg = f"Imported {imported} restaurants with {len(errors)} errors."
        if len(errors) > 5:
            error_msg += f" First 5 errors: {'; '.join(errors[:5])}..."
        else:
            error_msg += f" Errors: {'; '.join(errors)}"
        flash(error_msg, "warning" if imported > 0 else "error")
    else:
        flash(f"Successfully imported {imported} restaurants", "success")


def _handle_import_error(message, error=None):
    """Handle import errors consistently."""
    db.session.rollback()
    if error:
        current_app.logger.error(f"{message}: {str(error)}", exc_info=True)
    else:
        current_app.logger.error(message)
    flash(message, "error")
