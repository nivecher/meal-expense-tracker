"""Forms for loyalty import workflows."""

from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired


class LoyaltyImportForm(FlaskForm):
    """Form for importing loyalty programs from CSV or JSON files."""

    file = FileField("Import File", validators=[DataRequired()])
    submit = SubmitField("Import")
