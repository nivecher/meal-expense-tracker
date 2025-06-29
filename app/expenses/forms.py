"""Forms for the expenses blueprint."""

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional


class ExpenseForm(FlaskForm):
    """Form for adding and editing expenses."""

    # Basic Information
    amount = DecimalField(
        "Amount",
        validators=[
            DataRequired(message="Amount is required"),
            NumberRange(min=0.01, message="Amount must be greater than 0"),
        ],
        places=2,
    )
    date = DateField("Date", validators=[DataRequired(message="Date is required")], format="%Y-%m-%d")
    notes = TextAreaField("Notes", validators=[DataRequired(message="Notes are required")], render_kw={"rows": 3})
    # Category and Restaurant
    category_id = SelectField(
        "Category", coerce=lambda x: int(x) if x else None, validators=[DataRequired(message="Category is required")]
    )
    restaurant_id = SelectField("Restaurant", coerce=lambda x: int(x) if x else None, validators=[Optional()])
    # Optional Fields
    meal_type = SelectField(
        "Meal Type",
        choices=[
            ("", "Select a meal type (optional)"),
            ("Breakfast", "Breakfast"),
            ("Lunch", "Lunch"),
            ("Dinner", "Dinner"),
            ("Snacks", "Snacks"),
            ("Groceries", "Groceries"),
            ("Other", "Other"),
        ],
        validators=[Optional()],
    )
    notes = TextAreaField("Notes", validators=[Optional()], render_kw={"rows": 3})
