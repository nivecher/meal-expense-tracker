"""Forms for the expenses blueprint."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, NumberRange, Optional


class ExpenseForm(FlaskForm):
    """Form for adding and editing expenses.

    Args:
        category_choices: List of tuples for category select field (id, name)
        restaurant_choices: List of tuples for restaurant select field (id, name)
    """

    def __init__(self, *args, **kwargs):
        # Pop custom kwargs before calling parent __init__
        category_choices = kwargs.pop("category_choices", [(None, "Select a category (optional)")])
        restaurant_choices = kwargs.pop("restaurant_choices", [(None, "Select a restaurant")])
        restaurant_id = kwargs.pop("restaurant_id", None)

        super().__init__(*args, **kwargs)

        # Set default restaurant if provided
        if restaurant_id is not None:
            try:
                self.restaurant_id.data = int(restaurant_id)
            except (ValueError, TypeError):
                self.restaurant_id.data = None

        # Set choices for the select fields
        self.category_id.choices = category_choices
        self.restaurant_id.choices = restaurant_choices

    # Basic Information
    amount = DecimalField(
        "Amount",
        validators=[
            DataRequired(message="Amount is required"),
            NumberRange(min=0.01, message="Amount must be greater than 0"),
        ],
        places=2,
    )

    def validate_amount(self, field):
        """Validate and convert amount to Decimal."""
        if not field.data:
            return

        try:
            # Convert string to Decimal if it's a string
            if isinstance(field.data, str):
                # Remove any non-numeric characters except decimal point and negative sign
                clean_value = "".join(c for c in field.data if c.isdigit() or c in ".-")
                field.data = Decimal(clean_value)
            elif not isinstance(field.data, Decimal):
                field.data = Decimal(str(field.data))

            # Ensure we have exactly 2 decimal places
            field.data = field.data.quantize(Decimal("0.01"))

        except (ValueError, InvalidOperation) as e:
            current_app.logger.error(f"Error converting amount to Decimal: {e}")
            raise ValidationError("Please enter a valid amount")

    date = DateField(
        "Date", validators=[DataRequired(message="Date is required")], format="%Y-%m-%d", default=datetime.now().date()
    )
    # Category and Restaurant
    category_id = SelectField(
        "Category",
        coerce=lambda x: int(x) if x not in (None, "") and str(x).isdigit() else None,
        validators=[Optional()],
        render_kw={"class": "form-select"},
    )
    restaurant_id = SelectField(
        "Restaurant",
        coerce=lambda x: int(x) if x not in (None, "") and str(x).isdigit() else None,
        validators=[Optional()],
        render_kw={"class": "form-select"},
    )
    # Optional Fields
    meal_type = SelectField(
        "Meal Type",
        choices=[
            ("", "Select a meal type (optional)"),
            ("breakfast", "Breakfast"),
            ("lunch", "Lunch"),
            ("dinner", "Dinner"),
            ("snacks", "Snacks"),
            ("groceries", "Groceries"),
            ("other", "Other"),
        ],
        validators=[Optional()],
    )
    notes = TextAreaField("Notes", validators=[Optional()], render_kw={"rows": 3})
