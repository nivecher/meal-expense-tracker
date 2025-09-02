"""Forms for the expenses blueprint."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    ValidationError,
)
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
            ("brunch", "Brunch"),
            ("lunch", "Lunch"),
            ("dinner", "Dinner"),
            ("snacks", "Snacks"),
            ("drinks", "Drinks"),
            ("dessert", "Dessert"),
            ("late night", "Late Night"),
            ("groceries", "Groceries"),
            ("other", "Other"),
        ],
        validators=[Optional()],
    )
    order_type = SelectField(
        "Order Type",
        choices=[
            ("", "Select an order type (optional)"),
            ("dine_in", "Dine-In"),
            ("takeout", "Takeout"),
            ("delivery", "Delivery"),
            ("drive_thru", "Drive-Thru"),
            ("catering", "Catering"),
            ("other", "Other"),
        ],
        validators=[Optional()],
        render_kw={"class": "form-select"},
    )
    party_size = IntegerField(
        "Party Size",
        validators=[
            Optional(),
            NumberRange(min=1, max=50, message="Party size must be between 1 and 50"),
        ],
        render_kw={"class": "form-control", "min": "1", "max": "50"},
    )
    notes = TextAreaField("Notes", validators=[Optional()], render_kw={"rows": 3})

    # Tags field for custom labels
    tags = StringField(
        "Tags",
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "placeholder": "Enter tags separated by commas (e.g., business, travel, urgent)",
            "data-tags-input": "true",
        },
    )


class ExpenseImportForm(FlaskForm):
    """Form for importing expenses from CSV or JSON files."""

    file = FileField("CSV or JSON File", validators=[DataRequired()])
    submit = SubmitField("Import")
