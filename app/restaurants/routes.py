"""Restaurant-related routes for the application."""

import csv
import io
import json

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload

# Import Expense model here to avoid circular imports
from app.extensions import db
from app.restaurants import bp, services
from app.restaurants.exceptions import (
    DuplicateGooglePlaceIdError,
    DuplicateRestaurantError,
)
from app.restaurants.forms import RestaurantForm
from app.restaurants.models import Restaurant
from app.restaurants.services import calculate_expense_stats
from app.utils.decorators import admin_required

# Constants
PER_PAGE = 10  # Number of restaurants per page
SHOW_ALL = -1  # Special value to show all restaurants


@bp.route("/")
@login_required
def list_restaurants():
    """Show a list of all restaurants with pagination."""
    # Get pagination parameters with type hints
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", PER_PAGE, type=int)

    # Get all restaurants and stats
    restaurants, stats = services.get_restaurants_with_stats(current_user.id, request.args)

    # Handle pagination or show all
    total_restaurants = len(restaurants)
    if per_page == SHOW_ALL:
        # Show all restaurants without pagination
        paginated_restaurants = restaurants
        total_pages = 1
        page = 1
    else:
        # Calculate pagination with bounds checking
        total_pages = max(1, (total_restaurants + per_page - 1) // per_page) if total_restaurants else 1
        page = max(1, min(page, total_pages))  # Ensure page is within bounds
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_restaurants = restaurants[start_idx:end_idx]

    # Get filter options for the filter form
    filter_options = services.get_filter_options(current_user.id)

    # Extract current filter values
    filters = services.get_restaurant_filters(request.args)

    return render_template(
        "restaurants/list.html",
        restaurants=paginated_restaurants,
        total_spent=stats.get("total_spent", 0),
        avg_price_per_person=stats.get("avg_price_per_person", 0),
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_restaurants=total_restaurants,
        search=filters["search"],
        cuisine=filters["cuisine"],
        service_level=filters["service_level"],
        city=filters["city"],
        is_chain=filters["is_chain"],
        rating_min=filters["rating_min"],
        rating_max=filters["rating_max"],
        **filter_options,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_restaurant():
    """Add a new restaurant or redirect to existing one.

    If a restaurant with the same name and city already exists for the user,
    redirects to the existing restaurant's page instead of creating a duplicate.
    Handles both regular form submissions and AJAX requests.
    """
    form = RestaurantForm()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if form.validate_on_submit():
        try:
            restaurant, is_new = services.create_restaurant(current_user.id, form)
            if is_ajax:
                if is_new:
                    return (
                        jsonify(
                            {
                                "status": "success",
                                "message": "Restaurant added successfully!",
                                "redirect_url": url_for("restaurants.list_restaurants"),
                            }
                        ),
                        200,
                    )
                return (
                    jsonify(
                        {
                            "status": "info",
                            "message": (
                                f"A restaurant with the name '{restaurant.name}' in "
                                f"'{restaurant.city or 'unknown location'}' already exists."
                            ),
                            "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=restaurant.id),
                        }
                    ),
                    200,
                )

            # Regular form submission handling - redirect without flash messages
            # Success/error feedback should be handled by the destination page
            if is_new:
                return redirect(url_for("restaurants.list_restaurants"))
            else:
                return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))

        except Exception as e:
            if is_ajax:
                return jsonify({"status": "error", "message": f"Error saving restaurant: {str(e)}"}), 400
            flash(f"Error saving restaurant: {str(e)}", "error")

    # Handle form validation errors
    if request.method == "POST" and is_ajax:
        return jsonify({"status": "error", "message": "Form validation failed", "errors": form.errors}), 400

    return render_template("restaurants/form.html", form=form, is_edit=False)


@bp.route("/<int:restaurant_id>", methods=["GET", "POST"])
@login_required
def restaurant_details(restaurant_id):
    """View and update restaurant details with expenses.

    GET: Display restaurant details with expenses
    POST: Update restaurant details
    """
    # Get the restaurant with its expenses relationship loaded
    stmt = (
        select(Restaurant)
        .options(joinedload(Restaurant.expenses))
        .where(Restaurant.id == restaurant_id, Restaurant.user_id == current_user.id)
    )
    restaurant = db.session.scalar(stmt)

    if not restaurant:
        abort(404, "Restaurant not found")

    # Handle form submission
    if request.method == "POST":
        form = RestaurantForm()
        if form.validate_on_submit():
            try:
                # Update restaurant with form data
                services.update_restaurant(restaurant.id, current_user.id, form)
                flash("Restaurant updated successfully!", "success")
                return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))
            except Exception as e:
                flash(f"Error updating restaurant: {str(e)}", "danger")
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{getattr(form, field).label.text}: {error}", "danger")

            # Pre-populate form with submitted data
            form = RestaurantForm(data=request.form)
            return render_template(
                "restaurants/detail.html",
                restaurant=restaurant,
                expenses=sorted(restaurant.expenses, key=lambda x: x.date, reverse=True),
                form=form,
                is_edit=True,
            )

    # Load expenses for the restaurant
    expenses = sorted(restaurant.expenses, key=lambda x: x.date, reverse=True)

    # Calculate expense statistics
    expense_stats = calculate_expense_stats(restaurant_id, current_user.id)

    return render_template(
        "restaurants/detail.html",
        restaurant=restaurant,
        expenses=expenses,
        expense_stats=expense_stats,
        form=RestaurantForm(obj=restaurant),
    )


@bp.route("/<int:restaurant_id>/edit", methods=["GET", "POST"])
@login_required
def edit_restaurant(restaurant_id):
    """Edit restaurant details using the same form as add_restaurant.

    GET: Display form pre-populated with restaurant data
    POST: Update restaurant with form data
    """
    # Get the restaurant
    restaurant = db.session.scalar(
        select(Restaurant).where(Restaurant.id == restaurant_id, Restaurant.user_id == current_user.id)
    )

    if not restaurant:
        abort(404, "Restaurant not found")

    form = RestaurantForm()

    if form.validate_on_submit():
        try:
            # Update restaurant with form data
            services.update_restaurant(restaurant.id, current_user.id, form)
            # Redirect without flash message - success feedback handled by destination page
            return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))
        except Exception as e:
            flash(f"Error updating restaurant: {str(e)}", "danger")
    elif request.method == "GET":
        # Pre-populate form with existing data
        form = RestaurantForm(obj=restaurant)

    return render_template("restaurants/form.html", form=form, is_edit=True, restaurant=restaurant)


@bp.route("/delete/<int:restaurant_id>", methods=["POST"])
@login_required
def delete_restaurant(restaurant_id):
    """Delete a restaurant.

    This endpoint handles both HTML form submissions and JSON API requests.
    For HTML, it redirects to the restaurant list with a flash message.
    For JSON, it returns a JSON response with the result.
    """
    try:
        success, message = services.delete_restaurant_by_id(restaurant_id, current_user.id)

        if request.is_json or request.content_type == "application/json":
            if success:
                return jsonify(
                    {"success": True, "message": str(message), "redirect": url_for("restaurants.list_restaurants")}
                )
            else:
                return jsonify({"success": False, "error": str(message)}), 400

        # For HTML form submissions
        flash(message, "success" if success else "error")
        return redirect(url_for("restaurants.list_restaurants"))

    except Exception as e:
        current_app.logger.error(f"Error deleting restaurant {restaurant_id}: {str(e)}")
        if request.is_json or request.content_type == "application/json":
            return jsonify({"success": False, "error": "An error occurred while deleting the restaurant"}), 500

        flash("An error occurred while deleting the restaurant", "error")
        return redirect(url_for("restaurants.list_restaurants"))


@bp.route("/clear-place-id/<int:restaurant_id>", methods=["POST"])
@login_required
@admin_required
def clear_place_id(restaurant_id):
    """Clear the Google Place ID for a restaurant (admin only).

    This endpoint allows admin users to remove the Google Place ID association
    from a restaurant, which will disable Google Maps integration.
    """
    try:
        # Get the restaurant and verify it belongs to the user or user is admin
        restaurant = services.get_restaurant_for_user(restaurant_id, current_user.id)
        if not restaurant and not current_user.is_admin:
            flash("Restaurant not found.", "error")
            return redirect(url_for("restaurants.list_restaurants"))

        # If not found by user_id, try to find it as admin
        if not restaurant and current_user.is_admin:
            restaurant = db.session.get(Restaurant, restaurant_id)
            if not restaurant:
                flash("Restaurant not found.", "error")
                return redirect(url_for("restaurants.list_restaurants"))

        # Clear the Google Place ID
        old_place_id = restaurant.google_place_id
        restaurant.google_place_id = None
        db.session.commit()

        flash(f"Google Place ID cleared successfully for {restaurant.name}.", "success")
        current_app.logger.info(
            f"Admin {current_user.username} cleared Google Place ID {old_place_id} for restaurant {restaurant.name} (ID: {restaurant_id})"
        )

        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing Google Place ID for restaurant {restaurant_id}: {str(e)}")
        flash("An error occurred while clearing the Google Place ID.", "error")
        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant_id))


@bp.route("/export")
@login_required
def export_restaurants():
    """Export restaurants as CSV or JSON."""
    format_type = request.args.get("format", "csv").lower()

    # Get the data from the service
    restaurants = services.export_restaurants_for_user(current_user.id)

    if not restaurants:
        flash("No restaurants found to export", "warning")
        return redirect(url_for("restaurants.list_restaurants"))

    if format_type == "json":
        response = make_response(json.dumps(restaurants, indent=2))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = "attachment; filename=restaurants.json"
        return response

    # Default to CSV format
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=restaurants[0].keys() if restaurants else [], quoting=csv.QUOTE_NONNUMERIC
    )
    writer.writeheader()
    writer.writerows(restaurants)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=restaurants.csv"
    return response


def _validate_import_file(file):
    """Validate the uploaded file for restaurant import.

    Args:
        file: Uploaded file object

    Returns:
        bool: True if file is valid, False otherwise
    """
    if not file or file.filename == "":
        flash("No file selected", "error")
        return False

    if not file.filename.lower().endswith((".csv", ".json")):
        flash("Unsupported file type. Please upload a CSV or JSON file.", "error")
        return False
    return True


def _parse_import_file(file):
    """Parse the uploaded file and return the data."""
    try:
        if file.filename.lower().endswith(".json"):
            # Reset file pointer to beginning
            file.seek(0)
            data = json.load(file)
            if not isinstance(data, list):
                flash("Invalid JSON format. Expected an array of restaurants.", "error")
                return None
            return data

        # Parse CSV file
        # Reset file pointer to beginning
        file.seek(0)
        csv_data = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_data))
        return list(reader)
    except UnicodeDecodeError:
        flash(
            "Error decoding the file. Please ensure it's a valid CSV or JSON file.",
            "error",
        )
        return None
    except Exception as e:
        flash(f"Error parsing file: {str(e)}", "error")
        return None


def _process_import_file(file, user_id):
    """Process the uploaded file and return import results.

    Args:
        file: Uploaded file object
        user_id: Current user ID

    Returns:
        tuple: (success, result_data) indicating outcome
    """
    current_app.logger.info("Validating file...")
    if not _validate_import_file(file):
        current_app.logger.warning("File validation failed")
        return False, {"message": "File validation failed"}

    current_app.logger.info("File validation passed")

    # Process and save restaurants
    current_app.logger.info("Processing restaurants...")
    success, result_data = services.import_restaurants_from_csv(file, user_id)
    current_app.logger.info(f"Import result: success={success}, data={result_data}")

    return success, result_data


def _handle_import_success(result_data):
    """Handle successful import results and show appropriate messages.

    Args:
        result_data: Dictionary containing import results

    Returns:
        Flask redirect response
    """
    # Show success message for imported restaurants
    if result_data.get("success_count", 0) > 0:
        flash(f"Successfully imported {result_data['success_count']} restaurants.", "success")

    # Show warning toast for skipped duplicates
    if result_data.get("has_warnings", False):
        flash(f"{result_data['skipped_count']} duplicate restaurants were skipped.", "warning")

    return redirect(url_for("restaurants.list_restaurants"))


def _handle_import_error(result_data):
    """Handle import errors and log details.

    Args:
        result_data: Dictionary containing error information
    """
    error_message = result_data.get("message", "Import failed")
    flash(error_message, "danger")

    # Log detailed errors for debugging
    if result_data.get("error_details"):
        current_app.logger.error(f"Import errors: {result_data['error_details']}")


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_restaurants():
    """Handle restaurant import from file upload."""
    from app.restaurants.forms import RestaurantImportForm

    form = RestaurantImportForm()

    if request.method == "POST" and form.validate_on_submit():
        file = form.file.data
        current_app.logger.info(f"Import request received for file: {file.filename if file else 'None'}")

        if file and file.filename:
            try:
                success, result_data = _process_import_file(file, current_user.id)

                if success:
                    return _handle_import_success(result_data)
                else:
                    _handle_import_error(result_data)

            except ValueError as e:
                current_app.logger.error("ValueError during import: %s", str(e))
                flash(str(e), "danger")
            except Exception as e:
                current_app.logger.error("Error importing restaurants: %s", str(e), exc_info=True)
                flash("An error occurred while importing restaurants.", "danger")
        else:
            current_app.logger.warning("No file selected for import")
            flash("No file selected", "danger")

    return render_template("restaurants/import.html", form=form)


@bp.route("/find-places", methods=["GET", "POST"])
@login_required
def find_places():
    """Search for restaurants using Google Places API.

    This route renders a page where users can search for restaurants
    using Google Places API and add them to their list.

    Returns:
        Rendered template with the Google Places search interface
    """
    # Check if Google Maps API key is configured
    google_maps_api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not google_maps_api_key:
        current_app.logger.warning("Google Maps API key is not configured")
        flash("Google Maps integration is not properly configured. Please contact support.", "warning")

    # Render the Google Places search template
    return render_template("restaurants/places_search.html", google_maps_api_key=google_maps_api_key or "")


def _validate_google_places_request():
    """Validate the incoming Google Places request and return the JSON data.

    Returns:
        tuple: (data, error_response) where error_response is None if validation passes.
              data is a dictionary containing the parsed JSON and CSRF token.
    """
    current_app.logger.info("Validating Google Places request")

    if not request.is_json:
        error_msg = f"Invalid content type: {request.content_type}. Expected application/json"
        current_app.logger.warning(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 400)

    try:
        data = request.get_json()
        current_app.logger.debug(f"Received data: {data}")
    except Exception as e:
        error_msg = f"Failed to parse JSON data: {str(e)}"
        current_app.logger.error(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 400)

    if not data:
        error_msg = "No data provided in request"
        current_app.logger.warning(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 400)

    csrf_token = request.headers.get("X-CSRFToken")
    current_app.logger.debug(f"CSRF Token from headers: {csrf_token}")

    if not csrf_token:
        error_msg = "CSRF token is missing from request headers"
        current_app.logger.warning(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 403)

    # Return both the data and CSRF token as a dictionary
    return {"data": data, "csrf_token": csrf_token}, None

    return (data, csrf_token), None


def _prepare_restaurant_form(data, csrf_token):
    """Prepare and validate the restaurant form with the provided data.

    Args:
        data: Dictionary containing restaurant data
        csrf_token: CSRF token for form validation

    Returns:
        tuple: (form, error_response) where error_response is None if validation passes
    """
    from app.restaurants.forms import RestaurantForm

    # Ensure data is a dictionary
    if not isinstance(data, dict):
        error_msg = "Invalid data format. Expected a dictionary."
        current_app.logger.error(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 400)

    # Detect service level from Google Places data if available
    service_level = None
    if any(key in data for key in ["price_level", "types", "rating", "user_ratings_total"]):
        from app.restaurants.services import detect_service_level_from_google_data

        google_places_data = {
            "price_level": data.get("price_level"),
            "types": data.get("types", []),
            "rating": data.get("rating"),
            "user_ratings_total": data.get("user_ratings_total"),
        }

        detected_level, confidence = detect_service_level_from_google_data(google_places_data)
        if confidence > 0.3:  # Only use if confidence is reasonable
            service_level = detected_level

    form_data = {
        "name": data.get("name", ""),
        "address": data.get("formatted_address") or data.get("address", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "postal_code": data.get("postal_code", ""),
        "country": data.get("country", ""),
        "phone": data.get("formatted_phone_number") or data.get("phone", ""),
        "website": data.get("website", ""),
        "google_place_id": data.get("place_id") or data.get("google_place_id", ""),
        "service_level": service_level,
        # Note: coordinates would be looked up dynamically from Google Places API
        "csrf_token": csrf_token,
    }

    current_app.logger.debug(f"Form data prepared: {form_data}")

    form = RestaurantForm(data=form_data)
    current_app.logger.debug("Form created. Validating...")

    if not form.validate():
        errors = {field: errors[0] for field, errors in form.errors.items()}
        current_app.logger.warning(f"Form validation failed: {errors}")
        return None, (jsonify({"success": False, "message": "Validation failed", "errors": errors}), 400)

    return form, None


def _create_restaurant_from_form(form):
    """Create or update a restaurant from the validated form.

    Args:
        form: Validated RestaurantForm instance

    Returns:
        tuple: (restaurant, is_new) if successful, (None, error_response) if failed
    """
    from app.restaurants.services import create_restaurant

    try:
        current_app.logger.debug("Creating restaurant...")
        restaurant, is_new = create_restaurant(current_user.id, form)
        current_app.logger.info(f"Restaurant {'created' if is_new else 'updated'}: {restaurant.id}")
        return (restaurant, is_new), None
    except DuplicateGooglePlaceIdError as e:
        current_app.logger.warning(f"Duplicate Google Place ID: {e.google_place_id}")
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": e.to_dict(),
                    "message": e.message,
                    "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=e.existing_restaurant.id),
                }
            ),
            409,
        )
    except DuplicateRestaurantError as e:
        current_app.logger.warning(f"Duplicate restaurant: {e.name} in {e.city}")
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": e.to_dict(),
                    "message": e.message,
                    "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=e.existing_restaurant.id),
                }
            ),
            409,
        )
    except Exception as e:
        current_app.logger.error(f"Error creating restaurant: {str(e)}", exc_info=True)
        return None, (jsonify({"success": False, "message": "An error occurred while creating the restaurant"}), 500)


@bp.route("/check-restaurant-exists", methods=["POST"])
@login_required
def check_restaurant_exists():
    """Check if a restaurant with the given Google Place ID already exists.

    Expected JSON payload:
    {
        "google_place_id": "ChIJ..."
    }

    Returns:
        JSON response with exists (bool) and restaurant_id (int) if exists
    """
    data = request.get_json()
    if not data or "google_place_id" not in data:
        return jsonify({"success": False, "message": "Missing google_place_id"}), 400

    # Check if a restaurant with this Google Place ID already exists for the current user
    restaurant = Restaurant.query.filter_by(google_place_id=data["google_place_id"], user_id=current_user.id).first()

    return jsonify(
        {
            "success": True,
            "exists": restaurant is not None,
            "restaurant_id": restaurant.id if restaurant else None,
            "restaurant_name": restaurant.name if restaurant else None,
        }
    )


@bp.route("/add-from-google-places", methods=["POST"])
@login_required
def add_from_google_places():
    """Add a new restaurant from Google Places data.

    This endpoint is called via AJAX when a user selects a restaurant
    from the Google Places search results.

    Expected JSON payload:
    {
        "name": "Restaurant Name",
        "address": "123 Main St",
        "city": "City",
        "state": "State",
        "postal_code": "12345",
        "country": "Country",
        "phone": "+1234567890",
        "website": "https://example.com",
        "google_place_id": "ChIJ...",
        # Note: coordinates would be looked up dynamically from Google Places API
    }

    Returns:
        JSON response with success status and redirect URL
    """
    # Validate the request
    validation_result, error_response = _validate_google_places_request()
    if error_response:
        return error_response

    # Extract data and CSRF token from validation result
    data = validation_result["data"]
    csrf_token = validation_result["csrf_token"]

    # Check if restaurant already exists by google_place_id using enhanced error handling
    if "google_place_id" in data and data["google_place_id"]:
        existing_restaurant = Restaurant.query.filter_by(
            google_place_id=data["google_place_id"], user_id=current_user.id
        ).first()

        if existing_restaurant:
            # Return error response to trigger enhanced frontend handling
            error = DuplicateGooglePlaceIdError(data["google_place_id"], existing_restaurant)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": error.to_dict(),
                        "message": error.message,
                        "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=existing_restaurant.id),
                    }
                ),
                409,
            )

    # Prepare the form data
    form, error_response = _prepare_restaurant_form(data, csrf_token)
    if error_response:
        return error_response

    # Create the restaurant
    result, error_response = _create_restaurant_from_form(form)
    if error_response:
        return error_response

    restaurant, is_new = result

    try:
        # Update with Google Places data
        restaurant.update_from_google_places(data)
        db.session.commit()

        # Return success response with message for client-side handling
        message = "Restaurant added successfully!" if is_new else "Restaurant updated with the latest information."

        return jsonify(
            {
                "success": True,
                "is_new": is_new,
                "exists": False,
                "restaurant_id": restaurant.id,
                "message": message,
                "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=restaurant.id),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in add_from_google_places: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@bp.route("/search", methods=["GET"])
@login_required
def search_restaurants():
    """Search for restaurants by name, cuisine, or location.

    Query Parameters:
        q: Search query string
        page: Page number for pagination
        per_page: Number of results per page
        sort: Field to sort by (name, city, cuisine, etc.)
        order: Sort order (asc or desc)

    Returns:
        Rendered template with search results
    """
    query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    sort = request.args.get("sort", "name")
    order = request.args.get("order", "asc")

    # Validate sort field
    valid_sort_fields = ["name", "city", "cuisine", "created_at", "updated_at"]
    if sort not in valid_sort_fields:
        sort = "name"

    # Validate order
    order = order.lower()
    if order not in ["asc", "desc"]:
        order = "asc"

    # Build base query
    stmt = select(Restaurant).filter(Restaurant.user_id == current_user.id)

    # Apply search filters
    if query:
        search = f"%{query}%"
        stmt = stmt.filter(
            (Restaurant.name.ilike(search))
            | (Restaurant.city.ilike(search))
            | (Restaurant.cuisine.ilike(search))
            | (Restaurant.address.ilike(search))
        )

    # Import Type for type casting
    from typing import cast

    from sqlalchemy.sql.elements import ColumnElement

    # Apply sorting with proper type checking
    sort_field = getattr(Restaurant, sort, None) if sort else None

    # Ensure we have a valid sort field
    if sort_field is None or not hasattr(sort_field, "desc"):
        sort_field = Restaurant.name

    # Cast to ColumnElement to help mypy understand the type
    sort_field = cast(ColumnElement, sort_field)

    # Apply sort direction with type checking
    sort_expr = sort_field.desc() if order == "desc" else sort_field.asc()
    stmt = stmt.order_by(sort_expr)

    # Paginate results
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    restaurants = pagination.items

    return render_template(
        "restaurants/search.html",
        restaurants=restaurants,
        query=query,
        pagination=pagination,
        sort=sort,
        order=order,
        per_page=per_page,
        google_maps_api_key=current_app.config.get("GOOGLE_MAPS_API_KEY"),
    )


@bp.route("/find-by-google-place", methods=["GET"])
@login_required
def find_by_google_place():
    """Find restaurant details by Google Place ID.

    Query Parameters:
        place_id: Google Place ID to look up

    Returns:
        JSON response with restaurant details or error message
    """
    place_id = request.args.get("place_id")
    if not place_id:
        return jsonify({"error": "Missing place_id parameter"}), 400

    try:
        # Initialize Google Places client
        import googlemaps
        from flask import current_app

        gmaps = googlemaps.Client(key=current_app.config["GOOGLE_MAPS_API_KEY"])

        # Get place details
        place = gmaps.place(
            place_id=place_id,
            fields=[
                "name",
                "formatted_address",
                "formatted_phone_number",
                "website",
                "geometry",
                "opening_hours",
                "priceLevel",
                "rating",
                "userRatingsTotal",
                "photos",
                "types",
                "url",
                "address_components",
            ],
        )

        if not place or "result" not in place:
            return jsonify({"error": "Place not found"}), 404

        # Format the response
        result = place["result"]
        address_components = {
            "street_number": "",
            "route": "",
            "locality": "",
            "administrative_area_level_1": "",
            "postal_code": "",
            "country": "",
        }

        # Parse address components if available
        if "address_components" in result:
            for component in result["address_components"]:
                for address_type in component["types"]:
                    if address_type in address_components:
                        address_components[address_type] = component["long_name"]

        # Detect service level from Google Places data
        from app.restaurants.services import (
            detect_service_level_from_google_data,
            get_service_level_display_info,
        )

        google_places_data = {
            "price_level": result.get("priceLevel"),
            "types": result.get("types", []),
            "rating": result.get("rating"),
            "user_ratings_total": result.get("userRatingsTotal"),
        }

        service_level, confidence = detect_service_level_from_google_data(google_places_data)

        # Build the response
        response = {
            "name": result.get("name", ""),
            "address": f"{address_components['street_number']} {address_components['route']}".strip(),
            "city": address_components["locality"],
            "state": address_components["administrative_area_level_1"],
            "postal_code": address_components["postal_code"],
            "country": address_components["country"],
            "phone": result.get("formatted_phone_number", ""),
            "website": result.get("website", ""),
            "google_place_id": place_id,
            "rating": result.get("rating"),
            "price_level": result.get("priceLevel"),
            "types": result.get("types", []),
            "service_level": service_level,
            "service_level_display": get_service_level_display_info(service_level)["display_name"],
            "service_level_description": get_service_level_display_info(service_level)["description"],
            "service_level_confidence": round(confidence, 2),
        }

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Error fetching Google Place details: {str(e)}")
        return jsonify({"error": "Failed to fetch place details"}), 500
