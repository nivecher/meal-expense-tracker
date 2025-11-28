"""
Forms for the main blueprint.
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length


class ContactForm(FlaskForm):
    """Contact form for the contact page."""

    # Form fields
    name = StringField(
        "Name",
        validators=[
            DataRequired(message="Please enter your name"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
        ],
        render_kw={"placeholder": "Your name"},
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Please enter your email"),
            Email(message="Please enter a valid email address"),
            Length(max=120, message="Email must be less than 120 characters"),
        ],
        render_kw={"placeholder": "your.email@example.com"},
    )

    subject = SelectField(
        "Subject",
        choices=[
            ("", "Select a subject"),
            ("support", "Support Request"),
            ("feature", "Feature Request"),
            ("bug", "Report a Bug"),
            ("feedback", "General Feedback"),
            ("other", "Other"),
        ],
        validators=[DataRequired(message="Please select a subject")],
        default="",
    )

    message = TextAreaField(
        "Message",
        validators=[
            DataRequired(message="Please enter your message"),
            Length(min=10, max=2000, message="Message must be between 10 and 2000 characters"),
        ],
        render_kw={"rows": 5, "placeholder": "Your message..."},
    )

    submit = SubmitField("Send Message")

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the form."""
        super().__init__(*args, **kwargs)
        # Set the submit button class
        self.submit.render_kw = {"class": "btn btn-primary w-100"}
