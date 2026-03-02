"""Merchant-related routes."""

import csv
import io
import json
from typing import Any

from flask import Response, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.api import validate_api_csrf
from app.merchants import bp, services as merchant_services


def _check_merchant_access() -> bool:
    """Check if current user has access to merchant features.

    Returns:
        True if user has advanced features or is admin, False otherwise
    """
    return bool(current_user.has_advanced_features or current_user.is_admin)


def _require_merchant_access() -> Any | None:
    """Require merchant access, abort if not authorized."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))
    return None


@bp.route("/")
@login_required
def list_merchants() -> Any:
    """Show list of merchants for the current user."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

    filters = {
        "search": request.args.get("q", "").strip(),
        "category": request.args.get("category", "").strip(),
    }

    merchants, data = merchant_services.get_merchants_with_stats(current_user.id, filters)

    return render_template(
        "merchants/list.html",
        merchants=merchants,
        merchant_data=data.get("merchant_data", {}),
        stats=data.get("stats", {}),
        filters=filters,
        categories=merchant_services.get_merchant_categories(),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_merchant() -> Any:
    """Create a new merchant."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        short_name = request.form.get("short_name", "").strip()
        website = request.form.get("website", "").strip()
        category = request.form.get("category", "").strip() or None

        if not name:
            flash("Merchant name is required", "error")
            return redirect(url_for("merchants.new_merchant"))

        existing = merchant_services.get_merchant_by_name(name)
        if existing:
            flash(f"Merchant '{name}' already exists", "error")
            return redirect(url_for("merchants.new_merchant"))

        merchant = merchant_services.create_merchant(
            current_user.id,
            {
                "name": name,
                "short_name": short_name,
                "website": website,
                "category": category,
            },
        )
        flash(f"Merchant '{merchant.name}' created successfully", "success")

        redirect_to = request.form.get("redirect_to", "")
        if redirect_to:
            return redirect(f"{redirect_to}?merchant_id={merchant.id}")

        return redirect(url_for("merchants.list_merchants"))

    redirect_to = request.args.get("redirect_to", "")

    return render_template(
        "merchants/form.html",
        merchant=None,
        categories=merchant_services.get_merchant_categories(),
        redirect_to=redirect_to,
    )


@bp.route("/<int:merchant_id>")
@login_required
def view_merchant(merchant_id: int) -> Any:
    """View a merchant."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

    merchant = merchant_services.get_merchant(merchant_id)
    if not merchant:
        abort(404, description="Merchant not found")

    restaurants = merchant_services.get_restaurants_for_merchant(current_user.id, merchant.id)

    return render_template("merchants/detail.html", merchant=merchant, restaurants=restaurants)


@bp.route("/<int:merchant_id>/edit", methods=["GET", "POST"])
@login_required
def edit_merchant(merchant_id: int) -> Any:
    """Edit a merchant."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

    merchant = merchant_services.get_merchant(merchant_id)
    if not merchant:
        abort(404, description="Merchant not found")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        short_name = request.form.get("short_name", "").strip()
        website = request.form.get("website", "").strip()
        category = request.form.get("category", "").strip() or None

        if not name:
            flash("Merchant name is required", "error")
            return redirect(url_for("merchants.edit_merchant", merchant_id=merchant_id))

        existing = merchant_services.get_merchant_by_name(name)
        if existing and existing.id != merchant_id:
            flash(f"Merchant '{name}' already exists", "error")
            return redirect(url_for("merchants.edit_merchant", merchant_id=merchant_id))

        merchant_services.update_merchant(
            merchant_id,
            {
                "name": name,
                "short_name": short_name,
                "website": website,
                "category": category,
            },
        )
        flash(f"Merchant '{name}' updated successfully", "success")
        return redirect(url_for("merchants.list_merchants"))

    return render_template(
        "merchants/form.html",
        merchant=merchant,
        categories=merchant_services.get_merchant_categories(),
    )


@bp.route("/<int:merchant_id>/delete", methods=["POST"])
@login_required
def delete_merchant(merchant_id: int) -> Any:
    """Delete a merchant."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"), code=302)

    merchant = merchant_services.get_merchant(merchant_id)
    if not merchant:
        abort(404, description="Merchant not found")

    success = merchant_services.delete_merchant(merchant_id)
    if success:
        return jsonify({"status": "success", "message": f"Merchant '{merchant.name}' deleted"}), 200
    return jsonify({"status": "error", "message": "Failed to delete merchant"}), 500


def _parse_export_ids(raw_ids: list[str]) -> list[int]:
    """Parse and sanitize export ID list."""
    ids: list[int] = []
    for raw_id in raw_ids:
        for part in raw_id.split(","):
            value = part.strip()
            if not value or not value.isdigit():
                continue
            ids.append(int(value))
    return list(dict.fromkeys(ids))


@bp.route("/export")
@login_required
def export_merchants() -> Response:
    """Export merchants as CSV or JSON."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))  # type: ignore[return-value]

    format_type = request.args.get("format", "csv").lower()
    is_sample = request.args.get("sample", "false").lower() == "true"
    raw_ids = request.args.getlist("ids")
    merchant_ids = _parse_export_ids(raw_ids)

    if is_sample:
        sample_data = [
            {
                "name": "Acme Coffee",
                "short_name": "Acme",
                "website": "https://acmecoffee.example",
                "category": "coffee_shop",
                "restaurant_count": 3,
            },
            {
                "name": "Sunset Grill Group",
                "short_name": "Sunset",
                "website": "",
                "category": "casual_dining",
                "restaurant_count": 1,
            },
        ]

        if format_type == "json":
            response = make_response(json.dumps(sample_data, indent=2))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Disposition"] = "attachment; filename=sample_merchants.json"
            return response

        output = io.StringIO()
        fieldnames = ["name", "short_name", "website", "category", "restaurant_count"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        writer.writerows(sample_data)

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv"
        response.headers["Content-Disposition"] = "attachment; filename=sample_merchants.csv"
        return response

    if raw_ids and not merchant_ids:
        flash("No valid merchants selected for export", "warning")
        return redirect(url_for("merchants.list_merchants"))  # type: ignore[return-value]

    merchants = merchant_services.export_merchants_for_user(current_user.id, merchant_ids if raw_ids else None)
    if not merchants:
        flash("No merchants found to export", "warning")
        return redirect(url_for("merchants.list_merchants"))  # type: ignore[return-value]

    if format_type == "json":
        response = make_response(json.dumps(merchants, indent=2))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = "attachment; filename=merchants.json"
        return response

    output = io.StringIO()
    fieldnames = ["name", "short_name", "website", "category", "restaurant_count", "created_at", "updated_at"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
    writer.writerows(merchants)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=merchants.csv"
    return response


@bp.route("/api/list")
@login_required
def api_list_merchants() -> Any:
    """API endpoint to list merchants for autocomplete/dropdown."""
    if not _check_merchant_access():
        return jsonify([]), 200

    search = request.args.get("q", "").strip()
    filters = {"search": search} if search else {}
    merchants = merchant_services.get_merchants(current_user.id, filters)

    return (
        jsonify(
            [
                {
                    "id": m.id,
                    "name": m.name,
                    "short_name": m.short_name,
                    "website": m.website,
                    "category": m.category,
                }
                for m in merchants
            ]
        ),
        200,
    )


@bp.route("/api/quick-add", methods=["POST"])
@login_required
@validate_api_csrf
def api_quick_add_merchant() -> Any:
    """Quick-add a merchant from the restaurant form."""
    if not _check_merchant_access():
        return jsonify({"status": "error", "message": "Merchants is an advanced feature"}), 403

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    short_name = (payload.get("short_name") or "").strip()
    website = (payload.get("website") or "").strip()

    if not name:
        return jsonify({"status": "error", "message": "Merchant name is required"}), 400

    existing = merchant_services.get_merchant_by_name(name)
    if existing:
        return (
            jsonify(
                {
                    "status": "exists",
                    "merchant": {
                        "id": existing.id,
                        "name": existing.name,
                        "short_name": existing.short_name,
                        "website": existing.website,
                    },
                }
            ),
            200,
        )

    merchant = merchant_services.create_merchant(
        current_user.id,
        {
            "name": name,
            "short_name": short_name,
            "website": website,
        },
    )
    return (
        jsonify(
            {
                "status": "success",
                "merchant": {
                    "id": merchant.id,
                    "name": merchant.name,
                    "short_name": merchant.short_name,
                    "website": merchant.website,
                },
            }
        ),
        201,
    )
