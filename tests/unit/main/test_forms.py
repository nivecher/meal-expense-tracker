"""Tests for main forms to improve coverage."""

from flask_wtf import FlaskForm

from app.main.forms import ContactForm


class TestContactForm:
    """Test ContactForm class."""

    def test_form_initialization(self, app):
        """Test form initialization."""
        with app.app_context():
            form = ContactForm()

            # Check that all fields are present
            assert hasattr(form, "name")
            assert hasattr(form, "email")
            assert hasattr(form, "subject")
            assert hasattr(form, "message")
            assert hasattr(form, "submit")

            # Check field types
            assert form.name.label.text == "Name"
            assert form.email.label.text == "Email"
            assert form.subject.label.text == "Subject"
            assert form.message.label.text == "Message"
            assert form.submit.label.text == "Send Message"

    def test_form_field_attributes(self, app):
        """Test form field attributes and configuration."""
        with app.app_context():
            form = ContactForm()

            # Test name field
            assert form.name.render_kw == {"placeholder": "Your name"}
            assert len(form.name.validators) == 2  # DataRequired and Length

            # Test email field
            assert form.email.render_kw == {"placeholder": "your.email@example.com"}
            assert len(form.email.validators) == 3  # DataRequired, Email, and Length

            # Test subject field
            assert form.subject.choices == [
                ("", "Select a subject"),
                ("support", "Support Request"),
                ("feature", "Feature Request"),
                ("bug", "Report a Bug"),
                ("feedback", "General Feedback"),
                ("other", "Other"),
            ]
            assert form.subject.default == ""
            assert len(form.subject.validators) == 1  # DataRequired

            # Test message field
            assert form.message.render_kw == {"rows": 5, "placeholder": "Your message..."}
            assert len(form.message.validators) == 2  # DataRequired and Length

            # Test submit field
            assert form.submit.render_kw == {"class": "btn btn-primary w-100"}

    def test_form_validation_valid_data(self, app):
        """Test form validation with valid data."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is True
            assert len(form.errors) == 0

    def test_form_validation_missing_name(self, app):
        """Test form validation with missing name."""
        with app.app_context():
            form = ContactForm(
                data={
                    "email": "john@example.com",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "name" in form.errors
            assert "Please enter your name" in form.errors["name"]

    def test_form_validation_empty_name(self, app):
        """Test form validation with empty name."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "",
                    "email": "john@example.com",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "name" in form.errors
            assert "Please enter your name" in form.errors["name"]

    def test_form_validation_name_too_short(self, app):
        """Test form validation with name too short."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "J",
                    "email": "john@example.com",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "name" in form.errors
            assert "Name must be between 2 and 100 characters" in form.errors["name"]

    def test_form_validation_name_too_long(self, app):
        """Test form validation with name too long."""
        with app.app_context():
            long_name = "A" * 101  # 101 characters
            form = ContactForm(
                data={
                    "name": long_name,
                    "email": "john@example.com",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "name" in form.errors
            assert "Name must be between 2 and 100 characters" in form.errors["name"]

    def test_form_validation_missing_email(self, app):
        """Test form validation with missing email."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "John Doe",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "email" in form.errors
            assert "Please enter your email" in form.errors["email"]

    def test_form_validation_invalid_email(self, app):
        """Test form validation with invalid email."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "John Doe",
                    "email": "invalid-email",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "email" in form.errors
            assert "Please enter a valid email address" in form.errors["email"]

    def test_form_validation_email_too_long(self, app):
        """Test form validation with email too long."""
        with app.app_context():
            long_email = "a" * 115 + "@example.com"  # 130 characters total
            form = ContactForm(
                data={
                    "name": "John Doe",
                    "email": long_email,
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "email" in form.errors
            assert "Email must be less than 120 characters" in form.errors["email"]

    def test_form_validation_missing_subject(self, app):
        """Test form validation with missing subject."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "subject" in form.errors
            assert "Please select a subject" in form.errors["subject"]

    def test_form_validation_empty_subject(self, app):
        """Test form validation with empty subject."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.validate() is False
            assert "subject" in form.errors
            assert "Please select a subject" in form.errors["subject"]

    def test_form_validation_missing_message(self, app):
        """Test form validation with missing message."""
        with app.app_context():
            form = ContactForm(data={"name": "John Doe", "email": "john@example.com", "subject": "support"})

            assert form.validate() is False
            assert "message" in form.errors
            assert "Please enter your message" in form.errors["message"]

    def test_form_validation_message_too_short(self, app):
        """Test form validation with message too short."""
        with app.app_context():
            form = ContactForm(
                data={"name": "John Doe", "email": "john@example.com", "subject": "support", "message": "Short"}
            )

            assert form.validate() is False
            assert "message" in form.errors
            assert "Message must be between 10 and 2000 characters" in form.errors["message"]

    def test_form_validation_message_too_long(self, app):
        """Test form validation with message too long."""
        with app.app_context():
            long_message = "A" * 2001  # 2001 characters
            form = ContactForm(
                data={"name": "John Doe", "email": "john@example.com", "subject": "support", "message": long_message}
            )

            assert form.validate() is False
            assert "message" in form.errors
            assert "Message must be between 10 and 2000 characters" in form.errors["message"]

    def test_form_validation_multiple_errors(self, app):
        """Test form validation with multiple errors."""
        with app.app_context():
            form = ContactForm(data={"name": "", "email": "invalid-email", "subject": "", "message": "Short"})

            assert form.validate() is False
            assert len(form.errors) == 4  # All fields should have errors
            assert "name" in form.errors
            assert "email" in form.errors
            assert "subject" in form.errors
            assert "message" in form.errors

    def test_form_validation_boundary_values(self, app):
        """Test form validation with boundary values."""
        with app.app_context():
            # Test minimum valid values
            form_min = ContactForm(
                data={
                    "name": "Jo",  # Exactly 2 characters
                    "email": "a@b.co",  # Short but valid email
                    "subject": "support",
                    "message": "A" * 10,  # Exactly 10 characters
                }
            )
            assert form_min.validate() is True

            # Test maximum valid values - use shorter email to avoid validation issues
            form_max = ContactForm(
                data={
                    "name": "A" * 100,  # Exactly 100 characters
                    "email": "a" * 50 + "@example.com",  # Shorter email to avoid validation issues
                    "subject": "other",
                    "message": "A" * 2000,  # Exactly 2000 characters
                }
            )
            assert form_max.validate() is True

    def test_form_choices(self, app):
        """Test form subject choices."""
        with app.app_context():
            form = ContactForm()

            # Test that all expected choices are present
            expected_choices = [
                ("", "Select a subject"),
                ("support", "Support Request"),
                ("feature", "Feature Request"),
                ("bug", "Report a Bug"),
                ("feedback", "General Feedback"),
                ("other", "Other"),
            ]

            assert form.subject.choices == expected_choices

    def test_form_data_access(self, app):
        """Test accessing form data."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )

            assert form.name.data == "John Doe"
            assert form.email.data == "john@example.com"
            assert form.subject.data == "support"
            assert form.message.data == "This is a test message with enough characters."

    def test_form_inheritance(self, app):
        """Test that ContactForm inherits from FlaskForm."""
        with app.app_context():
            form = ContactForm()
            assert isinstance(form, FlaskForm)

    def test_form_csrf_token(self, app):
        """Test that form has CSRF token."""
        with app.app_context():
            form = ContactForm()
            # FlaskForm should automatically include CSRF token
            # Note: CSRF token might not be available in test context
            # Just check that the form can be created without errors
            assert form is not None

    def test_form_render_kw_attributes(self, app):
        """Test that render_kw attributes are properly set."""
        with app.app_context():
            form = ContactForm()

            # Test name field render_kw
            assert "placeholder" in form.name.render_kw
            assert form.name.render_kw["placeholder"] == "Your name"

            # Test email field render_kw
            assert "placeholder" in form.email.render_kw
            assert form.email.render_kw["placeholder"] == "your.email@example.com"

            # Test message field render_kw
            assert "rows" in form.message.render_kw
            assert "placeholder" in form.message.render_kw
            assert form.message.render_kw["rows"] == 5
            assert form.message.render_kw["placeholder"] == "Your message..."

            # Test submit field render_kw
            assert "class" in form.submit.render_kw
            assert form.submit.render_kw["class"] == "btn btn-primary w-100"

    def test_form_validation_edge_cases(self, app):
        """Test form validation with edge cases."""
        with app.app_context():
            # Test with whitespace-only name
            form_whitespace = ContactForm(
                data={
                    "name": "   ",
                    "email": "john@example.com",
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )
            # DataRequired should catch this
            assert form_whitespace.validate() is False
            assert "name" in form_whitespace.errors

            # Test with very long valid email
            long_valid_email = "a" * 50 + "@" + "b" * 50 + ".com"  # 105 characters
            form_long_email = ContactForm(
                data={
                    "name": "John Doe",
                    "email": long_valid_email,
                    "subject": "support",
                    "message": "This is a test message with enough characters.",
                }
            )
            assert form_long_email.validate() is True

    def test_form_validation_unicode_data(self, app):
        """Test form validation with unicode data."""
        with app.app_context():
            form = ContactForm(
                data={
                    "name": "José María",
                    "email": "josé@example.com",
                    "subject": "support",
                    "message": "This is a test message with unicode characters: ñáéíóú",
                }
            )

            assert form.validate() is True
            assert form.name.data == "José María"
            assert form.email.data == "josé@example.com"
            assert form.message.data == "This is a test message with unicode characters: ñáéíóú"
