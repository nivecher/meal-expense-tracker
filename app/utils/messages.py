"""Message constants for the application."""


class FlashMessages:
    """Container for flash message constants."""

    # Expense messages
    EXPENSE_ADDED = "Expense added successfully!"
    EXPENSE_ADD_ERROR = "An error occurred while adding the expense."
    EXPENSE_UPDATED = "Expense updated successfully!"
    EXPENSE_UPDATE_ERROR = "An error occurred while updating the expense."
    EXPENSE_DELETED = "Expense deleted successfully."
    EXPENSE_DELETE_ERROR = "An error occurred while deleting the expense."
    EXPENSE_FORM_INVALID = "Please correct the errors in the form."

    # Restaurant messages
    RESTAURANT_ADDED = "Restaurant added successfully!"
    RESTAURANT_ADD_ERROR = "An error occurred while adding the restaurant."
    RESTAURANT_UPDATED = "Restaurant updated successfully!"
    RESTAURANT_UPDATE_ERROR = "An error occurred while updating the restaurant."
    RESTAURANT_DELETED = "Restaurant deleted successfully."
    RESTAURANT_DELETE_ERROR = "An error occurred while deleting the restaurant."

    # Category messages
    CATEGORY_ADDED = "Category added successfully!"
    CATEGORY_ADD_ERROR = "An error occurred while adding the category."
    CATEGORY_UPDATED = "Category updated successfully!"
    CATEGORY_UPDATE_ERROR = "An error occurred while updating the category."
    CATEGORY_DELETED = "Category deleted successfully."
    CATEGORY_DELETE_ERROR = "An error occurred while deleting the category."

    # User messages
    PASSWORD_UPDATED = (
        "Your password has been updated successfully!"  # nosec B105 - User-facing message, not a password
    )
    PASSWORD_UPDATE_ERROR = (
        "An error occurred while updating your password."  # nosec B105 - User-facing message, not a password
    )
    PROFILE_UPDATED = "Your profile has been updated successfully!"
    PROFILE_UPDATE_ERROR = "An error occurred while updating your profile."

    # Authentication messages
    LOGIN_REQUIRED = "Please log in to access this page."
    INVALID_CREDENTIALS = "Invalid email or password."
    ACCOUNT_CREATED = "Your account has been created! You can now log in."
    ACCOUNT_CREATE_ERROR = "An error occurred while creating your account."
    REGISTRATION_SUCCESS = "Registration successful! You can now log in."
    REGISTRATION_ERROR = "An error occurred during registration. Please try again."
    EMAIL_ALREADY_EXISTS = "An account with this email already exists."
    INVALID_TOKEN = "Invalid or expired token."  # nosec B105 - User-facing message, not a password
    PASSWORD_RESET_SENT = "If an account exists with this email, password reset instructions have been sent."  # nosec B105 - User-facing message, not a password
    PASSWORD_RESET = "Your password has been successfully reset. Please log in with your new credentials."  # nosec B105 - User-facing message, not a password

    # Additional messages for test compatibility
    FIELDS_REQUIRED = "Please fill out all fields."
    USERNAME_EXISTS = "Username already exists"
    WELCOME_BACK = "Welcome back!"
    ADD_EXPENSE = "Add Expense"
    ERROR_CREATING_USER = "Error creating user:"
    PASSWORDS_DONT_MATCH = "Passwords do not match."
    CANNOT_DELETE_WITH_EXPENSES = "Cannot delete a restaurant with associated expenses."
