"""Service layer functions for restaurant operations."""

import csv
import logging
from io import StringIO
from typing import Dict, Optional, Tuple

from flask import Response, abort
from flask_wtf import FlaskForm
from sqlalchemy import and_, exists, select

from app import db
from app.restaurants.models import Restaurant

logger = logging.getLogger(__name__)


def get_restaurant(restaurant_id: int) -> Restaurant:
    """Get and validate a restaurant.

    Args:
        restaurant_id: ID of the restaurant to retrieve

    Returns:
        Restaurant: The restaurant object

    Raises:
        404: If the restaurant is not found
    """
    restaurant = db.session.get(Restaurant, restaurant_id)
    if not restaurant:
        abort(404, "Restaurant not found")
    return restaurant


def process_restaurant_form(restaurant: Restaurant, form: FlaskForm) -> Tuple[bool, str]:
    """Process the restaurant form data.

    Args:
        restaurant: The restaurant model instance to update
        form: The form containing the data to process

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Update restaurant fields from form data
        for field in form:
            if hasattr(restaurant, field.name) and field.data is not None:
                # Handle special cases if needed
                if field.type == "StringField":
                    setattr(restaurant, field.name, field.data.strip() if field.data else "")
                else:
                    setattr(restaurant, field.name, field.data)

        db.session.commit()
        return True, "Restaurant updated successfully!"

    except Exception as e:
        db.session.rollback()
        logger.error("Error updating restaurant: %s", str(e))
        return False, f"Error updating restaurant: {str(e)}"


def _process_restaurant_row(row: Dict[str, str], user_id: int) -> Optional[Restaurant]:
    """Process a single row of restaurant data."""
    name = (row.get("name") or "").strip()
    if not name:
        return None

    city = (row.get("city") or "").strip()

    # Check for duplicates
    conditions = [Restaurant.name == name, Restaurant.user_id == user_id]
    if city:
        conditions.append(Restaurant.city == city)

    exists_query = select(exists().where(and_(*conditions)))
    if db.session.execute(exists_query).scalar():
        logger.info("Skipping duplicate restaurant: %s in %s", name, city)
        return None

    return Restaurant(
        name=name,
        type=(row.get("type") or "").strip(),
        description=(row.get("description") or "").strip(),
        address=(row.get("address") or "").strip(),
        city=city,
        state=(row.get("state") or "").strip(),
        zip_code=(row.get("zip_code") or "").strip(),
        phone=(row.get("phone") or "").strip(),
        website=(row.get("website") or "").strip(),
        price_range=row.get("price_range") or None,
        cuisine=(row.get("cuisine") or "").strip(),
        notes=(row.get("notes") or "").strip(),
        user_id=user_id,
    )


def import_restaurants_from_csv(file_stream, user) -> Tuple[bool, str]:
    """Import restaurants from a CSV file.

    Args:
        file_stream: The file stream containing the CSV data
        user: The current user object (not just the ID)

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Read and decode the file
        try:
            content = file_stream.read().decode("utf-8")
            reader = csv.DictReader(StringIO(content))
        except UnicodeDecodeError:
            return False, "Invalid file encoding. Please use UTF-8 encoded CSV files."

        # Check for required columns
        if "name" not in (reader.fieldnames or []):
            return False, "Missing required column: 'name'"

        imported = 0
        skipped = 0

        for row_num, row in enumerate(reader, 2):  # Start at 2 for 1-based row numbers
            try:
                if not any(row.values()):
                    skipped += 1
                    continue

                restaurant = _process_restaurant_row(row, user.id)
                if not restaurant:
                    skipped += 1
                    continue

                db.session.add(restaurant)
                imported += 1

                # Commit in batches
                if imported % 50 == 0:
                    db.session.commit()

            except Exception as e:
                db.session.rollback()
                logger.error("Error processing row %d: %s", row_num, str(e))
                skipped += 1
                continue

        db.session.commit()

        # Prepare result message
        result_msg = f"Successfully imported {imported} restaurants"
        if skipped > 0:
            result_msg += f", skipped {skipped} rows (duplicates or invalid data)"

        return True, result_msg

    except Exception as e:
        db.session.rollback()
        logger.error("Error importing restaurants: %s", str(e), exc_info=True)
        return False, f"Error importing restaurants: {str(e)}"


def export_restaurants_to_csv(user_id) -> Response:
    """Export restaurants to a CSV file.

    Args:
        user_id: ID of the user whose restaurants to export

    Returns:
        Response: Flask response with CSV data
    """
    try:
        restaurants = db.session.scalars(
            select(Restaurant).filter(Restaurant.user_id == user_id).order_by(Restaurant.name)
        ).all()

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "name",
                "type",
                "description",
                "address",
                "city",
                "state",
                "zip_code",
                "phone",
                "website",
                "price_range",
                "cuisine",
                "notes",
            ]
        )

        # Write data rows
        for restaurant in restaurants:
            writer.writerow(
                [
                    restaurant.name,
                    restaurant.type or "",
                    restaurant.description or "",
                    restaurant.address or "",
                    restaurant.city or "",
                    restaurant.state or "",
                    restaurant.zip_code or "",
                    restaurant.phone or "",
                    restaurant.website or "",
                    restaurant.price_range or "",
                    restaurant.cuisine or "",
                    restaurant.notes or "",
                ]
            )

        # Create response with CSV data
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment;filename=restaurants_export.csv",
                "Content-type": "text/csv; charset=utf-8",
            },
        )

    except Exception as e:
        logger.error("Error exporting restaurants: %s", str(e), exc_info=True)
        raise


# Add type hints for better IDE support
__all__ = ["get_restaurant", "process_restaurant_form", "import_restaurants_from_csv", "export_restaurants_to_csv"]
