from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    SelectField,
    StringField,
    TelField,
    TextAreaField,
    URLField,
)
from wtforms.validators import URL, InputRequired, Length, Optional


class RestaurantForm(FlaskForm):
    """Form for adding/editing restaurant information."""

    name = StringField(
        "Name",
        validators=[InputRequired(), Length(min=1, max=100)],
        render_kw={"class": "form-control", "placeholder": "Restaurant name"},
    )

    type = SelectField(
        "Type",
        choices=[
            ("", "Select type..."),
            ("restaurant", "Restaurant"),
            ("cafe", "Cafe"),
            ("bar", "Bar"),
            ("bakery", "Bakery"),
            ("other", "Other"),
        ],
        validators=[InputRequired()],
        render_kw={"class": "form-select"},
    )

    cuisine_type = SelectField(
        "Cuisine Type",
        choices=[
            ("", "Select cuisine..."),
            ("american", "American"),
            ("chinese", "Chinese"),
            ("mexican", "Mexican"),
            ("italian", "Italian"),
            ("japanese", "Japanese"),
            ("indian", "Indian"),
            ("thai", "Thai"),
            ("french", "French"),
            ("mediterranean", "Mediterranean"),
            ("other", "Other"),
        ],
        validators=[Optional()],
        render_kw={"class": "form-select"},
    )

    description = TextAreaField(
        "Description",
        validators=[Optional(), Length(max=500)],
        render_kw={"class": "form-control", "rows": 3, "placeholder": "Brief description"},
    )

    address = StringField(
        "Address",
        validators=[Optional(), Length(max=200)],
        render_kw={"class": "form-control", "placeholder": "Street address"},
    )

    city = StringField(
        "City", validators=[Optional(), Length(max=100)], render_kw={"class": "form-control", "placeholder": "City"}
    )

    state_province = StringField(
        "State/Province",
        validators=[Optional(), Length(max=50)],
        render_kw={"class": "form-control", "placeholder": "State/Province"},
    )

    postal_code = StringField(
        "ZIP/Postal Code",
        validators=[Optional(), Length(max=20)],
        render_kw={"class": "form-control", "placeholder": "ZIP/Postal code"},
    )

    country = StringField(
        "Country",
        validators=[Optional(), Length(max=100)],
        render_kw={"class": "form-control", "placeholder": "Country"},
    )

    price_range = SelectField(
        "Price Range",
        choices=[
            ("", "Select price range..."),
            ("$", "$ - Inexpensive"),
            ("$$", "$$ - Moderate"),
            ("$$$", "$$$ - Expensive"),
            ("$$$$", "$$$$ - Very Expensive"),
        ],
        validators=[Optional()],
        render_kw={"class": "form-select"},
    )

    cuisine = StringField(
        "Cuisine Type",
        validators=[Optional(), Length(max=100)],
        render_kw={"class": "form-control", "placeholder": "e.g., Italian, Chinese, Mexican"},
    )

    website = URLField(
        "Website",
        validators=[Optional(), URL(), Length(max=200)],
        render_kw={"class": "form-control", "placeholder": "https://example.com"},
    )

    phone = TelField(
        "Phone Number",
        validators=[Optional(), Length(max=20)],
        render_kw={"class": "form-control", "placeholder": "+1 (123) 456-7890"},
    )

    notes = TextAreaField(
        "Notes",
        validators=[Optional()],
        render_kw={"class": "form-control", "rows": 3, "placeholder": "Any additional notes about this restaurant"},
    )

    is_chain = BooleanField(
        "Is this a chain restaurant?", validators=[Optional()], render_kw={"class": "form-check-input"}, default=False
    )
    # Hidden fields for Google Places data
    google_place_id = StringField(
        "Google Place ID",
        validators=[Optional()],
        render_kw={"type": "hidden"},
    )
    place_name = StringField(
        "Official Place Name",
        validators=[Optional()],
        render_kw={"type": "hidden"},
    )
    latitude = StringField(
        "Latitude",
        validators=[Optional()],
        render_kw={"type": "hidden"},
    )
    longitude = StringField(
        "Longitude",
        validators=[Optional()],
        render_kw={"type": "hidden"},
    )


class RestaurantImportForm(FlaskForm):
    """Form for importing restaurants from CSV."""

    csv_file = FileField(
        "CSV File",
        validators=[FileRequired("Please select a file to upload"), FileAllowed(["csv"], "Only CSV files are allowed")],
        description="CSV file containing restaurant data",
        render_kw={"accept": ".csv", "class": "form-control", "aria-label": "Select CSV file to import"},
    )

    on_duplicate = SelectField(
        "If restaurant exists",
        choices=[
            ("skip", "Skip (keep existing)"),
            ("update", "Update with new data"),
            ("create_new", "Create new entry"),
        ],
        default="skip",
        description="How to handle duplicate restaurants",
        validators=[InputRequired()],
        render_kw={"class": "form-select", "aria-label": "Action to take when a duplicate restaurant is found"},
    )

    skip_header = BooleanField(
        "Skip first row (header)",
        default=True,
        description="Check if the first row contains column headers",
        render_kw={
            "class": "form-check-input",
            "role": "switch",
            "aria-label": "Skip first row if it contains headers",
        },
    )


class RestaurantSearchForm(FlaskForm):
    """Form for searching restaurants using Google Places API."""

    keyword = StringField("Search Term", validators=[Optional()])
    radius = SelectField(
        "Search Radius",
        choices=[(500, "500 meters"), (1000, "1 km"), (2000, "2 km"), (5000, "5 km")],
        default=1000,
        coerce=int,
        validators=[Optional()],
    )
    sort_by = SelectField(
        "Sort By",
        choices=[("prominence", "Best Match"), ("distance", "Distance"), ("rating", "Rating")],
        default="prominence",
        validators=[Optional()],
    )
