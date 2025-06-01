from flask import render_template, request
from flask_login import login_required, current_user
from app import db
from app.main import bp
from app.expenses.models import Expense
from app.restaurants.models import Restaurant
from datetime import datetime


@bp.route("/")
@login_required
def index():
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

    # Apply filters
    query = apply_filters(query, request.args)

    # Apply sorting
    query = apply_sorting(query, sort_by, sort_order)

    expenses = query.all()

    # Calculate total amount
    total_amount = sum(expense.amount for expense in expenses) if expenses else 0.0

    # Get unique meal types and categories for filter dropdowns
    meal_types = (
        db.session.query(Expense.meal_type)
        .distinct()
        .filter(Expense.meal_type != "")
        .all()
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
        "main/index.html",
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
    )


def apply_filters(query, request_args):
    search = request_args.get("search", "")
    meal_type = request_args.get("meal_type", "")
    category = request_args.get("category", "")
    start_date = request_args.get("start_date", "")
    end_date = request_args.get("end_date", "")

    if search:
        query = query.join(Restaurant).filter(
            db.or_(
                Restaurant.name.ilike(f"%{search}%"),
                Restaurant.address.ilike(f"%{search}%"),
                Expense.notes.ilike(f"%{search}%"),
            )
        )
    if meal_type:
        query = query.filter(Expense.meal_type == meal_type)
    if category:
        query = query.filter(Expense.category == category)
    if start_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        query = query.filter(Expense.date >= start_date_obj)
    if end_date:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        query = query.filter(Expense.date <= end_date_obj)
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
