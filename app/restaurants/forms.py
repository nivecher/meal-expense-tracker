from typing import Any

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

from app.constants.cuisines import get_cuisine_names
from app.constants.restaurant_types import get_restaurant_type_form_choices


def validate_service_level(form: Any, field: Any) -> None:
    """Validate service level field."""
    field_data = getattr(field, "data", None)
    if field_data and field_data not in [
        "",
        "fine_dining",
        "casual_dining",
        "fast_casual",
        "quick_service",
        "unknown",
    ]:
        raise ValidationError("Invalid service level selected.")


class RestaurantForm(FlaskForm):
    # Basic Information
    name = StringField("Restaurant Name", validators=[DataRequired(), Length(max=100)])
    type = SelectField(
        "Type",
        choices=get_restaurant_type_form_choices(),
        validators=[DataRequired()],
    )
    located_within = StringField("Location Within", validators=[Optional(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])

    # Contact Information
    address_line_1 = StringField("Address Line 1", validators=[Optional(), Length(max=255)])
    address_line_2 = StringField("Address Line 2", validators=[Optional(), Length(max=255)])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    state = StringField("State/Province", validators=[Optional(), Length(max=100)])
    postal_code = StringField("Postal Code", validators=[Optional(), Length(max=20)])
    country = StringField("Country", validators=[Optional(), Length(max=100)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    email = StringField("Email", validators=[Optional(), Length(max=120)])
    website = StringField("Website", validators=[Optional(), URL(), Length(max=255)])

    # Google Places Integration
    google_place_id = StringField("Google Place ID", validators=[Optional(), Length(max=255)])
    latitude = FloatField(
        "Latitude",
        validators=[Optional()],
        render_kw={"type": "hidden", "id": "latitude", "step": "any"},
    )
    longitude = FloatField(
        "Longitude",
        validators=[Optional()],
        render_kw={"type": "hidden", "id": "longitude", "step": "any"},
    )

    # Additional Information
    cuisine = SelectField(
        "Cuisine",
        choices=[("", "Select Cuisine (Optional)")] + [(name, name) for name in get_cuisine_names()],
        validators=[Optional()],
    )
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
        render_kw={
            "step": "0.5",
            "min": "1.0",
            "max": "5.0",
            "placeholder": "Your personal rating (1.0 - 5.0)",
        },
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
