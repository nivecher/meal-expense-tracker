"""Forms for merchant import workflows."""

from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired


class MerchantImportForm(FlaskForm):
    """Form for importing merchants from CSV or JSON files."""

    file = FileField("Import File", validators=[DataRequired()])
    submit = SubmitField("Import")
