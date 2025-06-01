from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required
from app import db
from app.restaurants import bp
from app.restaurants.models import Restaurant
from app.expenses.models import Expense
from sqlalchemy.exc import SQLAlchemyError
import csv
from io import StringIO, BytesIO


@bp.route("/")
@login_required
def list_restaurants():
    try:
        restaurants = Restaurant.query.order_by(Restaurant.name).all()
        return render_template(
            "restaurants/list_restaurants.html", restaurants=restaurants
        )
    except SQLAlchemyError:
        db.session.rollback()
        flash("Error loading restaurants. Please try again.", "error")
        return redirect(url_for("main.index"))


@bp.route("/<int:restaurant_id>/details")
@login_required
def restaurant_details(restaurant_id):
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        expenses = (
            Expense.query.filter_by(restaurant_id=restaurant.id)
            .order_by(Expense.date.desc())
            .all()
        )
        return render_template(
            "restaurants/restaurant_details.html",
            restaurant=restaurant,
            expenses=expenses,
        )
    except SQLAlchemyError:
        db.session.rollback()
        flash("Error loading restaurant details. Please try again.", "error")
        return render_template(
            "restaurants/restaurant_details.html", restaurant=None, expenses=[]
        )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_restaurant():
    if request.method == "POST":
        try:
            # Validate required fields
            required_fields = ["name", "address", "city"]
            for field in required_fields:
                if not request.form.get(field):
                    flash(f"{field.title()} is required", "error")
                    return render_template("restaurants/add_restaurant.html")

            # Check for duplicate restaurant
            existing_restaurant = Restaurant.query.filter_by(
                name=request.form["name"], city=request.form["city"]
            ).first()
            if existing_restaurant:
                flash(
                    "A restaurant with this name already exists in this city.", "error"
                )
                return render_template("restaurants/add_restaurant.html")

            restaurant = Restaurant(
                name=request.form["name"],
                type=request.form.get("type", "restaurant"),
                description=request.form.get("description", ""),
                address=request.form["address"],
                city=request.form["city"],
                state=request.form.get("state", ""),
                zip_code=request.form.get("zip_code", ""),
                price_range=request.form.get("price_range", ""),
                cuisine=request.form.get("cuisine", ""),
                website=request.form.get("website", ""),
                phone=request.form.get("phone", ""),
                notes=request.form.get("notes", ""),
            )
            db.session.add(restaurant)
            db.session.commit()

            # Verify the restaurant was created
            created_restaurant = Restaurant.query.filter_by(
                name=request.form["name"]
            ).first()
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
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        if request.method == "POST":
            try:
                restaurant.name = request.form["name"]
                restaurant.type = request.form.get("type", "restaurant")
                restaurant.description = request.form.get("description", "")
                restaurant.address = request.form["address"]
                restaurant.city = request.form["city"]
                restaurant.state = request.form.get("state", "")
                restaurant.zip_code = request.form.get("zip_code", "")
                restaurant.price_range = request.form.get("price_range", "")
                restaurant.cuisine = request.form.get("cuisine", "")
                restaurant.website = request.form.get("website", "")
                restaurant.phone = request.form.get("phone", "")
                restaurant.notes = request.form.get("notes", "")
                db.session.commit()
                flash("Restaurant updated successfully!", "success")
                return redirect(url_for("restaurants.list_restaurants"))
            except SQLAlchemyError:
                db.session.rollback()
                flash("Error updating restaurant. Please try again.", "error")
        return render_template(
            "restaurants/edit_restaurant.html", restaurant=restaurant
        )
    except SQLAlchemyError:
        db.session.rollback()
        flash("Error loading restaurant. Please try again.", "error")
        return redirect(url_for("restaurants.list_restaurants"))


@bp.route("/<int:restaurant_id>/delete", methods=["POST"])
@login_required
def delete_restaurant(restaurant_id):
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        if restaurant.expenses:
            flash("Cannot delete restaurant with associated expenses.", "error")
            return redirect(url_for("restaurants.list_restaurants"))
        db.session.delete(restaurant)
        db.session.commit()
        flash("Restaurant deleted successfully!", "success")
        return redirect(url_for("restaurants.list_restaurants"))
    except SQLAlchemyError:
        db.session.rollback()
        flash("Error deleting restaurant. Please try again.", "error")
        return redirect(url_for("restaurants.list_restaurants"))


@bp.route("/search")
@login_required
def search_restaurants():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])

    try:
        restaurants = (
            Restaurant.query.filter(
                (Restaurant.name.ilike(f"%{query}%"))
                | (Restaurant.city.ilike(f"%{query}%"))
            )
            .limit(10)
            .all()
        )

        return jsonify(
            [
                {
                    "id": r.id,
                    "name": r.full_name,
                    "type": r.type,
                    "address": r.full_address,
                }
                for r in restaurants
            ]
        )
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "Error searching restaurants"}), 500


@bp.route("/export", methods=["GET"])
@login_required
def export_restaurants():
    try:
        restaurants = Restaurant.query.order_by(Restaurant.name).all()
        output = StringIO()
        writer = csv.writer(output)
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
        for restaurant in restaurants:
            writer.writerow(
                [
                    restaurant.name,
                    restaurant.type,
                    restaurant.description,
                    restaurant.address,
                    restaurant.city,
                    restaurant.state,
                    restaurant.zip_code,
                    restaurant.price_range,
                    restaurant.cuisine,
                    restaurant.website,
                    restaurant.phone,
                    restaurant.notes,
                ]
            )
        # Convert StringIO to BytesIO for send_file
        mem = BytesIO()
        mem.write(output.getvalue().encode("utf-8"))
        mem.seek(0)
        output.close()
        return send_file(
            mem,
            mimetype="text/csv",
            as_attachment=True,
            download_name="restaurants.csv",
        )
    except SQLAlchemyError:
        db.session.rollback()
        flash("Error exporting restaurants. Please try again.", "error")
        return redirect(url_for("restaurants.list_restaurants"))


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_restaurants():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part", "error")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No selected file", "error")
            return redirect(request.url)
        if file:
            try:
                stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                for row in csv_input:
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
                db.session.commit()
                flash("Restaurants imported successfully!", "success")
                return redirect(url_for("restaurants.list_restaurants"))
            except SQLAlchemyError:
                db.session.rollback()
                flash("Error importing restaurants. Please try again.", "error")
    return render_template("restaurants/import_restaurants.html")
