from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FileField,
    FloatField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    URL,
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


def validate_service_level(form, field):
    """Validate service level field."""
    if field.data and field.data not in ["", "fine_dining", "casual_dining", "fast_casual", "quick_service", "unknown"]:
        raise ValidationError("Invalid service level selected.")


class RestaurantForm(FlaskForm):
    # Basic Information
    name = StringField("Restaurant Name", validators=[DataRequired(), Length(max=100)])
    type = SelectField(
        "Type",
        choices=[
            ("restaurant", "Restaurant"),
            ("cafe", "Cafe"),
            ("bar", "Bar"),
            ("bakery", "Bakery"),
            ("other", "Other"),
        ],
        validators=[DataRequired()],
    )
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])

    # Contact Information
    address = StringField("Address Line 1", validators=[Optional(), Length(max=255)])
    address2 = StringField("Address Line 2", validators=[Optional(), Length(max=255)])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    state = StringField("State/Province", validators=[Optional(), Length(max=100)])
    postal_code = StringField("Postal Code", validators=[Optional(), Length(max=20)])
    country = StringField("Country", validators=[Optional(), Length(max=100)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    email = StringField("Email", validators=[Optional(), Length(max=120)])
    website = StringField("Website", validators=[Optional(), URL(), Length(max=255)])

    # Google Places Integration
    google_place_id = StringField("Google Place ID", validators=[Optional(), Length(max=255)])

    # Additional Information
    cuisine = StringField("Cuisine", validators=[Optional(), Length(max=100)])
    service_level = SelectField(
        "Service Level",
        choices=[
            ("", "Auto-detect (Google)"),
            ("fine_dining", "Fine Dining"),
            ("casual_dining", "Casual Dining"),
            ("fast_casual", "Fast Casual"),
            ("quick_service", "Quick Service"),
            ("unknown", "Unknown"),
        ],
        validators=[Optional(), validate_service_level],
        render_kw={
            "data-bs-toggle": "tooltip",
            "title": "Service level will be auto-detected from Google Places data if available",
        },
    )
    rating = FloatField(
        "Your Rating",
        validators=[Optional(), NumberRange(min=1.0, max=5.0)],
        render_kw={"step": "0.5", "min": "1.0", "max": "5.0", "placeholder": "Your personal rating (1.0 - 5.0)"},
    )
    price_level = SelectField(
        "Price Level",
        choices=[
            ("", "Auto-detect (Google)"),
            (0, "Free"),
            (1, "$ Budget ($1-10)"),
            (2, "$$ Moderate ($11-30)"),
            (3, "$$$ Expensive ($31-60)"),
            (4, "$$$$ Very Expensive ($61+)"),
        ],
        validators=[Optional()],
        coerce=lambda x: int(x) if x and x != "" else None,
        render_kw={
            "data-bs-toggle": "tooltip",
            "title": "Price level will be auto-detected from Google Places data if available",
        },
    )
    is_chain = BooleanField("Part of a chain", false_values=(False, "false", 0, "0"), default=False)
    notes = TextAreaField("Notes", validators=[Optional()])

    # Form submission
    submit = SubmitField("Save Restaurant")


class RestaurantSearchForm(FlaskForm):
    """Form for searching restaurants."""

    query = StringField("Search", validators=[Optional(), Length(max=100)])
    location = StringField("Location", validators=[Optional(), Length(max=100)])
    cuisine = StringField("Cuisine", validators=[Optional(), Length(max=50)])
    min_rating = FloatField(
        "Minimum Rating",
        validators=[Optional(), NumberRange(min=1.0, max=5.0)],
        render_kw={"step": "0.5", "min": "1.0", "max": "5.0", "placeholder": "Minimum user rating"},
    )
    submit = SubmitField("Search")


class RestaurantImportForm(FlaskForm):
    """Form for importing restaurants from CSV files."""

    file = FileField("CSV File", validators=[DataRequired()])
    submit = SubmitField("Import")
