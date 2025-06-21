from datetime import datetime, timedelta
import csv
import logging
from io import StringIO
from typing import Optional

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    Response,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.expenses import bp
from app.expenses.models import Expense
from app.restaurants.models import Restaurant

# Set up logging
logger = logging.getLogger(__name__)


def apply_filters(
    query,
    search: Optional[str] = None,
    meal_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Apply filters to the expense query.

    Args:
        query: The base query to apply filters to
        search: Search term to filter by
        meal_type: Filter by meal type
        category: Filter by category
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Query: The filtered query
    """
    try:
        if search:
            search = f"%{search}%"
            query = query.join(Restaurant).filter(
                db.or_(
                    Restaurant.name.ilike(search),
                    Restaurant.city.ilike(search),
                    Restaurant.cuisine.ilike(search),
                    Restaurant.type.ilike(search),
                    Expense.notes.ilike(search),
                    Expense.category.ilike(search),
                    Expense.meal_type.ilike(search),
                )
            )
        if meal_type:
            query = query.filter(Expense.meal_type == meal_type)
        if category:
            query = query.filter(Expense.category == category)
        if start_date:
            query = query.filter(
                Expense.date >= datetime.strptime(start_date, "%Y-%m-%d").date()
            )
        if end_date:
            query = query.filter(
                Expense.date <= datetime.strptime(end_date, "%Y-%m-%d").date()
            )
        return query
    except Exception as e:
        logger.error(f"Error applying filters: {str(e)}")
        raise


def apply_sorting(query, sort_by, sort_order):
    """Apply sorting to the expense query."""
    if sort_by == "date":
        query = query.order_by(
            Expense.date.desc() if sort_order == "desc" else Expense.date.asc()
        )
    elif sort_by == "amount":
        query = query.order_by(
            Expense.amount.desc() if sort_order == "desc" else Expense.amount.asc()
        )
    elif sort_by == "meal_type":
        query = query.order_by(
            Expense.meal_type.desc()
            if sort_order == "desc"
            else Expense.meal_type.asc()
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


def get_main_index_context():
    """Get the context for the main index page."""
    # Get filter parameters
    search = request.args.get("search", "")
    meal_type = request.args.get("meal_type", "")
    category = request.args.get("category", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    sort_by = request.args.get("sort", "date")
    sort_order = request.args.get("order", "desc")

    # Base query
    query = Expense.query.filter_by(user_id=current_user.id)

    # Apply filters and sorting
    query = apply_filters(query, search, meal_type, category, start_date, end_date)
    query = apply_sorting(query, sort_by, sort_order)

    # Get results
    expenses = query.all()
    total_amount = sum(expense.amount for expense in expenses) if expenses else 0.0

    # Get unique meal types and categories for filter dropdowns
    meal_types = (
        db.session.query(Expense.meal_type)
        .distinct()
        .filter(Expense.meal_type != "")
        .all()
    )
    meal_types = sorted([meal[0] for meal in meal_types])
    categories = (
        db.session.query(Expense.category)
        .distinct()
        .filter(Expense.category != "")
        .all()
    )
    categories = sorted([category[0] for category in categories])

    # Add restaurant_expense_counts for use in the template
    restaurant_ids = [e.restaurant_id for e in expenses if e.restaurant_id]
    restaurant_expense_counts = {}
    if restaurant_ids:
        counts = (
            db.session.query(Expense.restaurant_id, db.func.count(Expense.id))
            .filter(
                Expense.user_id == current_user.id,
                Expense.restaurant_id.in_(restaurant_ids),
            )
            .group_by(Expense.restaurant_id)
            .all()
        )
        restaurant_expense_counts = {rid: count for rid, count in counts}

    return dict(
        expenses=expenses,
        search=search,
        meal_type=meal_type,
        category=category,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
        meal_types=meal_types,
        categories=categories,
        total_amount=total_amount,
        restaurant_expense_counts=restaurant_expense_counts,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_expense():
    restaurant_id = request.args.get("restaurant_id")
    restaurant = None
    if restaurant_id:
        restaurant = db.session.get(Restaurant, restaurant_id)
        if not restaurant:
            flash("Restaurant not found.", "error")
            return redirect(url_for("main.index"))

    if request.method == "POST":
        date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        restaurant_id = request.form.get("restaurant_id")
        restaurant_type = None
        if restaurant_id:
            restaurant = db.session.get(Restaurant, restaurant_id)
            if restaurant:
                restaurant_type = restaurant.type
        type_to_category = {
            "restaurant": "Dining",
            "cafe": "Coffee",
            "bar": "Drinks",
            "fast_food": "Fast Food",
            "food_truck": "Street Food",
            "bakery": "Bakery",
            "grocery": "Groceries",
        }
        category = type_to_category.get(
            restaurant_type, request.form.get("category", "")
        )
        expense = Expense(
            date=date,
            amount=float(request.form["amount"]),
            category=category,
            meal_type=request.form["meal_type"],
            notes=request.form["notes"],
            user_id=current_user.id,
            restaurant_id=restaurant_id,
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense added successfully!", "success")
        if restaurant_id:
            return redirect(
                url_for("restaurants.restaurant_details", restaurant_id=restaurant_id)
            )
        return redirect(url_for("main.index"))

    # Get all restaurants for the dropdown
    restaurants = Restaurant.query.order_by(Restaurant.name).all()
    today = datetime.now().date()
    min_date = today - timedelta(days=365)  # Allow expenses up to 1 year in the past

    return render_template(
        "expenses/add_expense.html",
        restaurant=restaurant,
        restaurants=restaurants,
        today=today.strftime("%Y-%m-%d"),
        min_date=min_date.strftime("%Y-%m-%d"),
    )


@bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    # Use db.session.get() directly with explicit 404 handling
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        abort(404)

    if expense.user_id != current_user.id:
        flash("You do not have permission to edit this expense.", "error")
        return redirect(url_for("main.index"))

    # Get all restaurants for the dropdown
    restaurants = Restaurant.query.order_by(Restaurant.name).all()
    today = datetime.now().date()
    min_date = today - timedelta(days=365)  # Allow expenses up to 1 year in the past

    if request.method == "POST":
        try:
            expense.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format.", "error")
            return (
                render_template(
                    "expenses/edit_expense.html",
                    expense=expense,
                    restaurants=restaurants,
                    today=today.strftime("%Y-%m-%d"),
                    min_date=min_date.strftime("%Y-%m-%d"),
                ),
                400,
            )

        try:
            expense.amount = float(request.form["amount"])
        except ValueError:
            flash("Invalid amount format.", "error")
            return (
                render_template(
                    "expenses/edit_expense.html",
                    expense=expense,
                    restaurants=restaurants,
                    today=today.strftime("%Y-%m-%d"),
                    min_date=min_date.strftime("%Y-%m-%d"),
                ),
                400,
            )

        # Set category based on restaurant type
        restaurant_id = request.form.get("restaurant_id")
        restaurant_type = None
        if restaurant_id:
            restaurant = db.session.get(Restaurant, restaurant_id)
            if restaurant:
                restaurant_type = restaurant.type
        type_to_category = {
            "restaurant": "Dining",
            "cafe": "Coffee",
            "bar": "Drinks",
            "fast_food": "Fast Food",
            "food_truck": "Street Food",
            "bakery": "Bakery",
            "grocery": "Groceries",
        }
        expense.category = type_to_category.get(
            restaurant_type, request.form.get("category", "")
        )
        expense.meal_type = request.form["meal_type"]
        expense.notes = request.form.get("notes", "")
        expense.restaurant_id = restaurant_id
        db.session.commit()
        flash("Expense updated successfully!", "success")
        return redirect(url_for("main.index"))

    return render_template(
        "expenses/edit_expense.html",
        expense=expense,
        restaurants=restaurants,
        today=today.strftime("%Y-%m-%d"),
        min_date=min_date.strftime("%Y-%m-%d"),
    )


@bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense(expense_id: int):
    """Delete an expense.

    Args:
        expense_id: The ID of the expense to delete

    Returns:
        Redirect to main index
    """
    try:
        expense = db.session.get(Expense, expense_id)
        if expense is None:
            logger.warning(f"Expense {expense_id} not found")
            abort(404)

        if expense.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to delete expense {expense_id} "
                f"owned by user {expense.user_id}"
            )
            flash("You do not have permission to delete this expense.", "error")
            return redirect(url_for("main.index"))

        db.session.delete(expense)
        db.session.commit()
        logger.info(
            f"Expense {expense_id} deleted successfully by user {current_user.id}"
        )
        flash("Expense deleted successfully!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(
            f"Database error deleting expense {expense_id}: {str(e)}", exc_info=True
        )
        flash(
            "An error occurred while deleting the expense. Please try again.", "error"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error deleting expense {expense_id}: {str(e)}", exc_info=True
        )
        flash("An unexpected error occurred. Please try again later.", "error")

    return redirect(url_for("main.index"))


@bp.route("/stats")
@login_required
def expense_stats():
    # Get date range from request or default to last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= end_date,
    ).all()
    total_amount = sum(expense.amount for expense in expenses)
    category_totals = {}
    meal_type_totals = {}
    for expense in expenses:
        category_totals[expense.category] = (
            category_totals.get(expense.category, 0) + expense.amount
        )
        meal_type_totals[expense.meal_type] = (
            meal_type_totals.get(expense.meal_type, 0) + expense.amount
        )
    return render_template(
        "expenses/stats.html",
        total_amount=total_amount,
        category_totals=category_totals,
        meal_type_totals=meal_type_totals,
        start_date=start_date,
        end_date=end_date,
    )


@bp.route("/<int:expense_id>")
@login_required
def expense_details(expense_id: int):
    """Display details of a specific expense.

    Args:
        expense_id: The ID of the expense to display

    Returns:
        Rendered template with expense details or redirect
    """
    try:
        expense = db.session.get(Expense, expense_id)
        if expense is None:
            logger.warning(f"Expense {expense_id} not found")
            abort(404)

        if expense.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to view expense {expense_id} "
                f"owned by user {expense.user_id}"
            )
            flash("You do not have permission to view this expense.", "error")
            return redirect(url_for("main.index"))

        return render_template("expenses/expense_detail.html", expense=expense)

    except SQLAlchemyError as e:
        logger.error(
            f"Database error fetching expense {expense_id}: {str(e)}", exc_info=True
        )
        flash("An error occurred while fetching the expense details.", "error")
        return redirect(url_for("main.index"))
    except Exception as e:
        logger.error(f"Unexpected error in expense_details: {str(e)}", exc_info=True)
        flash("An unexpected error occurred.", "error")
        return redirect(url_for("main.index"))


@bp.route("/export")
@login_required
def export_expenses():
    """Export expenses to CSV."""
    try:
        expenses = (
            Expense.query.filter_by(user_id=current_user.id)
            .order_by(Expense.date.desc())
            .all()
        )

        output = StringIO()
        writer = csv.writer(output)

        # Write header with restaurant information
        writer.writerow(
            [
                "Date",
                "Restaurant",
                "Meal Type",
                "Amount",
                "Notes",
                "Restaurant Type",
                "Cuisine",
                "Price Range",
                "Location",
            ]
        )

        # Write expense data with restaurant information
        for expense in expenses:
            restaurant = expense.restaurant
            location = f"{restaurant.city}, {restaurant.state}" if restaurant else ""
            writer.writerow(
                [
                    expense.date.strftime("%Y-%m-%d"),
                    restaurant.name if restaurant else "Unknown",
                    expense.meal_type or "",
                    f"${expense.amount:.2f}",
                    expense.notes or "",
                    restaurant.type if restaurant else "",
                    restaurant.cuisine if restaurant else "",
                    restaurant.price_range if restaurant else "",
                    location,
                ]
            )

        output.seek(0)
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=expenses.csv"},
        )
    except Exception as e:
        flash(f"Error exporting expenses: {str(e)}", "error")
        return redirect(url_for("main.index"))
