"""Message constants for the application."""


class FlashMessages:
    """Container for flash message constants."""

    # Authentication messages
    LOGIN_SUCCESS = "Login successful!"
    LOGIN_ERROR = "Invalid username or password"
    REGISTRATION_SUCCESS = "Congratulations, you are now a registered user!"
    PASSWORD_UPDATED = "Your password has been updated."  # nosec B105
    PASSWORD_ERROR = "Invalid password."  # nosec B105
    PROFILE_UPDATED = "Profile updated successfully!"
    PROFILE_UPDATE_ERROR = "Failed to update profile. Please try again."
    TIMEZONE_INVALID = "Invalid timezone, defaulted to UTC"
    PHONE_TOO_LONG = "Phone number is too long (max 20 characters)"
    BIO_TOO_LONG = "Bio is too long (max 500 characters)"
    AVATAR_URL_TOO_LONG = "Avatar URL is too long (max 255 characters)"

    # Expense messages
    EXPENSE_ADDED = "Expense added successfully!"
    EXPENSE_UPDATED = "Expense updated successfully!"
    EXPENSE_DELETED = "Expense deleted successfully."
    EXPENSE_NOT_FOUND = "Expense not found."
    EXPENSE_DELETE_ERROR = "An error occurred while deleting the expense."
    EXPENSE_IMPORT_SUCCESS = "Successfully imported {count} expenses."
    EXPENSE_IMPORT_WARNING = "{count} items were skipped (duplicates or restaurant warnings)."
    EXPENSE_IMPORT_ERROR = "An unexpected error occurred during import"
    EXPENSE_NO_FILE = "Please select a file to upload"
    EXPENSE_EXPORT_NO_DATA = "No expenses found to export"

    # Restaurant messages
    RESTAURANT_ADDED = "Restaurant added successfully!"
    RESTAURANT_UPDATED = "Restaurant updated successfully!"
    RESTAURANT_DELETED = "Restaurant deleted successfully."
    RESTAURANT_NOT_FOUND = "Restaurant not found."
    RESTAURANT_SAVE_ERROR = "Error saving restaurant"
    RESTAURANT_UPDATE_ERROR = "Error updating restaurant"
    RESTAURANT_IMPORT_SUCCESS = "Successfully imported {count} restaurants."
    RESTAURANT_IMPORT_WARNING = "{count} items were skipped (duplicates or validation warnings)."
    RESTAURANT_IMPORT_ERROR = "An unexpected error occurred during import"
    RESTAURANT_EXPORT_NO_DATA = "No restaurants found to export"

    # General messages
    SUCCESS = "Operation completed successfully."
    ERROR = "An error occurred. Please try again."
    WARNING = "Please check your input and try again."
    INFO = "Information updated."
