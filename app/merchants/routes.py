"""Merchant-related routes."""

import csv
import io
import json
from typing import Any
from urllib.parse import urlencode, urlparse

from flask import Response, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.wrappers import Response as WerkzeugResponse

from app.api import validate_api_csrf
from app.constants import get_cuisine_names
from app.extensions import db
from app.loyalty import services as loyalty_services
from app.merchants import bp, services as merchant_services
from app.merchants.forms import MerchantImportForm
from app.restaurants.models import Restaurant


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


def _build_new_merchant_prefill_from_request() -> dict[str, str]:
    """Read merchant form prefill values from query args."""
    return {
        "name": request.args.get("prefill_name", "").strip(),
        "short_name": request.args.get("prefill_short_name", "").strip(),
        "website": request.args.get("prefill_website", "").strip(),
        "description": request.args.get("prefill_description", "").strip(),
        "favicon_url": request.args.get("prefill_favicon_url", "").strip(),
        "category": request.args.get("prefill_category", "").strip(),
        "menu_focus": request.args.get("prefill_menu_focus", "").strip(),
        "cuisine": request.args.get("prefill_cuisine", "").strip(),
        "service_level": request.args.get("prefill_service_level", "").strip(),
        "is_chain": (
            "true" if request.args.get("prefill_is_chain", "").strip().lower() in {"1", "true", "on", "yes"} else ""
        ),
    }


def _build_new_merchant_redirect_url(redirect_to: str, merchant_id: int) -> str:
    """Append merchant_id to a redirect target without breaking existing query params."""
    separator = "&" if "?" in redirect_to else "?"
    return f"{redirect_to}{separator}{urlencode({'merchant_id': merchant_id})}"


def _is_safe_redirect_path(url: str | None) -> bool:
    """Return True if url is a safe internal path for redirect."""
    if not url or not isinstance(url, str):
        return False
    candidate = url.strip()
    if candidate.startswith(("http://", "https://", "//")):
        return False
    if not candidate.startswith("/"):
        return False

    parsed = urlparse(candidate)
    return bool(parsed.path and not parsed.netloc)


def _get_safe_redirect_path(url: str | None) -> str | None:
    """Return a sanitized internal redirect path or None."""
    if not _is_safe_redirect_path(url):
        return None
    return str(url).strip()


def _get_merchant_cuisine_choices() -> list[str]:
    """Return cuisine choices aligned with restaurant cuisine values."""
    return get_cuisine_names()


def _merchant_api_payload(merchant: Any) -> dict[str, Any]:
    """Serialize merchant data for frontend merchant selection flows."""
    payload = merchant.to_dict() if hasattr(merchant, "to_dict") else {}
    payload["view_url"] = url_for("merchants.view_merchant", merchant_id=merchant.id)
    return payload


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
        "service_level": request.args.get("service_level", "").strip(),
        "cuisine": request.args.get("cuisine", "").strip(),
        "menu_focus": request.args.get("menu_focus", "").strip(),
        "is_chain": request.args.get("is_chain", "").strip(),
        "has_description": request.args.get("has_description", "").strip(),
        "restaurant_status": request.args.get("restaurant_status", "").strip(),
        "sort": request.args.get("sort", "name").strip(),
        "order": request.args.get("order", "asc").strip(),
    }

    merchants, data = merchant_services.get_merchants_with_detailed_stats(current_user.id, filters)
    association_rows = merchant_services.get_unlinked_restaurants_with_suggestions(current_user.id)
    suggested_counts_by_merchant: dict[int, int] = {}
    for row in association_rows:
        suggested_merchant = row.get("suggested_merchant")
        if not suggested_merchant or suggested_merchant.id is None:
            continue
        suggested_counts_by_merchant[suggested_merchant.id] = (
            suggested_counts_by_merchant.get(suggested_merchant.id, 0) + 1
        )
    association_summary = {
        "total_unlinked_restaurants": len(association_rows),
        "suggested_unlinked_restaurants": sum(1 for row in association_rows if row.get("suggested_merchant")),
        "merchants_without_restaurants": sum(
            1
            for merchant_stats in data.get("merchant_data", {}).values()
            if (merchant_stats.get("restaurant_count") or 0) == 0
        ),
    }
    merchant_rewards_links = loyalty_services.get_merchant_rewards_links_for_user(
        current_user.id,
        [merchant.id for merchant in merchants if merchant.id is not None],
    )

    return render_template(
        "merchants/list.html",
        merchants=merchants,
        merchant_data=data.get("merchant_data", {}),
        suggested_counts_by_merchant=suggested_counts_by_merchant,
        stats=data.get("stats", {}),
        association_summary=association_summary,
        filters=filters,
        categories=merchant_services.get_unique_merchant_categories(),
        format_category_groups=merchant_services.get_merchant_format_category_groups(),
        service_levels=merchant_services.get_unique_merchant_service_levels(),
        cuisine_filters=merchant_services.get_unique_merchant_cuisines(),
        menu_focus_filters=merchant_services.get_unique_merchant_menu_focuses(),
        merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
        merchant_service_level_labels=merchant_services.MERCHANT_SERVICE_LEVEL_LABELS,
        merchant_rewards_links=merchant_rewards_links,
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
        short_name = merchant_services.normalize_short_name(name, request.form.get("short_name", ""))
        website = request.form.get("website", "").strip()
        description = request.form.get("description", "").strip()
        favicon_url = request.form.get("favicon_url", "").strip()
        category = request.form.get("category", "").strip() or None
        menu_focus = request.form.get("menu_focus", "").strip() or None
        cuisine = request.form.get("cuisine", "").strip() or None
        service_level = request.form.get("service_level", "").strip() or None
        is_chain = request.form.get("is_chain") == "on"
        rewards_program_id_raw = request.form.get("rewards_program_id", "").strip()
        redirect_to = _get_safe_redirect_path(request.form.get("redirect_to")) or ""
        form_prefill = {
            "name": name,
            "short_name": short_name or "",
            "website": website,
            "description": description,
            "favicon_url": favicon_url,
            "category": category or "",
            "menu_focus": menu_focus or "",
            "cuisine": cuisine or "",
            "service_level": service_level or "",
            "is_chain": "true" if is_chain else "",
        }

        if not name:
            flash("Merchant name is required", "error")
            return render_template(
                "merchants/form.html",
                merchant=None,
                prefill=form_prefill,
                categories=merchant_services.get_merchant_categories(),
                format_category_groups=merchant_services.get_merchant_format_category_groups(),
                cuisine_choices=_get_merchant_cuisine_choices(),
                service_levels=merchant_services.get_merchant_service_levels(),
                merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
                rewards_program_choices=loyalty_services.get_rewards_program_choices(current_user.id),
                selected_rewards_program_id=rewards_program_id_raw,
                redirect_to=redirect_to,
            )

        existing = merchant_services.find_conflicting_merchant(name, short_name=short_name)
        if existing:
            flash("Merchant name or alias already exists", "error")
            return render_template(
                "merchants/form.html",
                merchant=None,
                prefill=form_prefill,
                categories=merchant_services.get_merchant_categories(),
                format_category_groups=merchant_services.get_merchant_format_category_groups(),
                cuisine_choices=_get_merchant_cuisine_choices(),
                service_levels=merchant_services.get_merchant_service_levels(),
                merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
                rewards_program_choices=loyalty_services.get_rewards_program_choices(current_user.id),
                selected_rewards_program_id=rewards_program_id_raw,
                redirect_to=redirect_to,
            )

        merchant = merchant_services.create_merchant(
            current_user.id,
            {
                "name": name,
                "short_name": short_name,
                "website": website,
                "description": description or None,
                "favicon_url": favicon_url or None,
                "category": category,
                "menu_focus": menu_focus,
                "cuisine": cuisine,
                "service_level": service_level,
                "is_chain": is_chain,
            },
        )
        rewards_program_id = int(rewards_program_id_raw) if rewards_program_id_raw.isdigit() else None
        try:
            loyalty_services.set_merchant_rewards_program_for_user(current_user.id, merchant.id, rewards_program_id)
        except ValueError as exc:
            flash(str(exc), "warning")
        flash(f"Merchant '{merchant.name}' created successfully", "success")

        if redirect_to:
            return redirect(_build_new_merchant_redirect_url(redirect_to, merchant.id))

        return redirect(url_for("merchants.list_merchants"))

    redirect_to = _get_safe_redirect_path(request.args.get("redirect_to")) or ""
    prefill = _build_new_merchant_prefill_from_request()

    restaurant_id = request.args.get("restaurant_id", "").strip()
    if restaurant_id.isdigit():
        restaurant = db.session.get(Restaurant, int(restaurant_id))
        if restaurant and restaurant.user_id == current_user.id:
            derived_prefill = merchant_services.get_create_merchant_prefill_for_restaurant(restaurant)
            for key, value in derived_prefill.items():
                if not prefill.get(key):
                    prefill[key] = value

    return render_template(
        "merchants/form.html",
        merchant=None,
        prefill=prefill,
        categories=merchant_services.get_merchant_categories(),
        format_category_groups=merchant_services.get_merchant_format_category_groups(),
        cuisine_choices=_get_merchant_cuisine_choices(),
        service_levels=merchant_services.get_merchant_service_levels(),
        merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
        rewards_program_choices=loyalty_services.get_rewards_program_choices(current_user.id),
        selected_rewards_program_id=request.args.get("rewards_program_id", "").strip(),
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

    restaurants = merchant_services.get_restaurants_for_merchant_with_stats(current_user.id, merchant.id)
    merchant_summary = merchant_services.get_merchant_summary(current_user.id, merchant.id)
    matching_restaurants = merchant_services.get_unlinked_matching_restaurants_for_merchant(
        current_user.id, merchant.id
    )
    rewards_link = loyalty_services.get_merchant_rewards_link(current_user.id, merchant.id)

    return render_template(
        "merchants/detail.html",
        merchant=merchant,
        restaurants=restaurants,
        merchant_summary=merchant_summary,
        matching_restaurants=matching_restaurants,
        rewards_link=rewards_link,
    )


@bp.route("/associations")
@login_required
def review_restaurant_associations() -> Any:
    """Review unlinked restaurants and suggested merchant matches."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

    association_rows = merchant_services.get_unlinked_restaurants_with_suggestions(current_user.id)
    suggested_count = sum(1 for row in association_rows if row.get("suggested_merchant"))

    for row in association_rows:
        restaurant = row.get("restaurant")
        if not restaurant:
            continue
        row["create_merchant_prefill"] = merchant_services.get_create_merchant_prefill_for_restaurant(restaurant)

    return render_template(
        "merchants/associations.html",
        association_rows=association_rows,
        suggested_count=suggested_count,
        total_unlinked=len(association_rows),
        merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
    )


@bp.route("/associations/apply-suggestions", methods=["POST"])
@login_required
def apply_suggested_restaurant_associations() -> Any:
    """Bulk-apply suggested merchant matches for unlinked restaurants."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

    requested_ids: list[int] = []
    for raw_id in request.form.getlist("restaurant_ids"):
        value = raw_id.strip()
        if value.isdigit():
            requested_ids.append(int(value))

    updated_count, _updated = merchant_services.associate_restaurants_to_suggested_merchants(
        current_user.id,
        restaurant_ids=requested_ids or None,
    )

    if updated_count:
        flash(f"Linked {updated_count} restaurant(s) to suggested merchants.", "success")
    else:
        flash("No suggested merchant matches were applied.", "info")

    return redirect(url_for("merchants.review_restaurant_associations"))


@bp.route("/<int:merchant_id>/associate-matches", methods=["POST"])
@login_required
def associate_matching_restaurants(merchant_id: int) -> Any:
    """Associate unlinked matching restaurants with a merchant."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

    merchant = merchant_services.get_merchant(merchant_id)
    if not merchant:
        abort(404, description="Merchant not found")

    requested_ids: list[int] = []
    for raw_id in request.form.getlist("restaurant_ids"):
        value = raw_id.strip()
        if value.isdigit():
            requested_ids.append(int(value))

    updated_count, _updated = merchant_services.associate_unlinked_matching_restaurants(
        current_user.id,
        merchant.id,
        restaurant_ids=requested_ids or None,
    )

    if updated_count:
        flash(f"Linked {updated_count} restaurant(s) to '{merchant.name}'.", "success")
    else:
        flash("No matching unlinked restaurants were linked.", "info")

    return redirect(url_for("merchants.view_merchant", merchant_id=merchant.id))


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

    merchant_summary = merchant_services.get_merchant_summary(current_user.id, merchant.id)
    restaurants = merchant_services.get_restaurants_for_merchant_with_stats(current_user.id, merchant.id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        short_name = merchant_services.normalize_short_name(name, request.form.get("short_name", ""))
        website = request.form.get("website", "").strip()
        description = request.form.get("description", "").strip()
        favicon_url = request.form.get("favicon_url", "").strip()
        category = request.form.get("category", "").strip() or None
        menu_focus = request.form.get("menu_focus", "").strip() or None
        cuisine = request.form.get("cuisine", "").strip() or None
        service_level = request.form.get("service_level", "").strip() or None
        is_chain = request.form.get("is_chain") == "on"
        rewards_program_id_raw = request.form.get("rewards_program_id", "").strip()

        if not name:
            flash("Merchant name is required", "error")
            return redirect(url_for("merchants.edit_merchant", merchant_id=merchant_id))

        existing = merchant_services.find_conflicting_merchant(
            name,
            short_name=short_name,
            exclude_id=merchant_id,
        )
        if existing:
            flash("Merchant name or alias already exists", "error")
            return redirect(url_for("merchants.edit_merchant", merchant_id=merchant_id))

        merchant_services.update_merchant(
            merchant_id,
            {
                "name": name,
                "short_name": short_name,
                "website": website,
                "description": description or None,
                "favicon_url": favicon_url or None,
                "category": category,
                "menu_focus": menu_focus,
                "cuisine": cuisine,
                "service_level": service_level,
                "is_chain": is_chain,
            },
        )
        rewards_program_id = int(rewards_program_id_raw) if rewards_program_id_raw.isdigit() else None
        try:
            loyalty_services.set_merchant_rewards_program_for_user(current_user.id, merchant.id, rewards_program_id)
        except ValueError as exc:
            flash(str(exc), "warning")
        flash(f"Merchant '{name}' updated successfully", "success")
        return redirect(url_for("merchants.list_merchants"))

    rewards_link = loyalty_services.get_merchant_rewards_link(current_user.id, merchant.id)
    return render_template(
        "merchants/form.html",
        merchant=merchant,
        merchant_summary=merchant_summary,
        restaurants=restaurants,
        categories=merchant_services.get_merchant_categories(),
        format_category_groups=merchant_services.get_merchant_format_category_groups(),
        cuisine_choices=_get_merchant_cuisine_choices(),
        service_levels=merchant_services.get_merchant_service_levels(),
        merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
        rewards_program_choices=loyalty_services.get_rewards_program_choices(current_user.id),
        selected_rewards_program_id=rewards_link.rewards_program_id if rewards_link else "",
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
                "description": "Regional coffeehouse brand focused on espresso drinks and pastries.",
                "category": "cafe_bakery",
                "menu_focus": "Coffee",
                "cuisine": "American",
                "service_level": "fast_casual",
                "restaurant_count": 3,
            },
            {
                "name": "Sunset Grill Group",
                "short_name": "Sunset",
                "website": "",
                "description": "Neighborhood grill concept with broad lunch and dinner appeal.",
                "category": "standard_restaurant",
                "menu_focus": "Grill",
                "cuisine": "American",
                "service_level": "casual_dining",
                "restaurant_count": 1,
            },
        ]

        if format_type == "json":
            response = make_response(json.dumps(sample_data, indent=2))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Disposition"] = "attachment; filename=sample_merchants.json"
            return response

        output = io.StringIO()
        fieldnames = [
            "name",
            "short_name",
            "website",
            "description",
            "category",
            "service_level",
            "cuisine",
            "menu_focus",
            "restaurant_count",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC, extrasaction="ignore")
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
    fieldnames = [
        "name",
        "short_name",
        "website",
        "description",
        "category",
        "service_level",
        "cuisine",
        "menu_focus",
        "restaurant_count",
        "created_at",
        "updated_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(merchants)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=merchants.csv"
    return response


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_merchants() -> str | Response | WerkzeugResponse:
    """Handle merchant import from file upload."""
    if not _check_merchant_access():
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

    form = MerchantImportForm()

    if request.method == "POST" and form.validate_on_submit():
        file = form.file.data
        if file and file.filename:
            success, result_data = merchant_services.import_merchants_from_file(file, current_user.id)
            if success:
                if result_data.get("success_count", 0) > 0:
                    flash(f"Successfully imported {result_data['success_count']} merchants.", "success")
                if result_data.get("has_warnings", False):
                    flash(f"{result_data['skipped_count']} duplicate merchants were skipped.", "warning")
                return redirect(url_for("merchants.list_merchants"))

            flash(result_data.get("message", "Import failed"), "danger")
            return render_template(
                "merchants/import.html",
                form=form,
                import_summary=result_data,
                warnings=[],
                errors=result_data.get("errors", []),
            )

        flash("No file selected", "danger")

    return render_template("merchants/import.html", form=form, import_summary=None, warnings=None, errors=None)


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
        jsonify([_merchant_api_payload(merchant) for merchant in merchants]),
        200,
    )


@bp.route("/api/suggest")
@login_required
def api_suggest_merchant() -> Any:
    """Return the best merchant suggestion for a restaurant name."""
    if not _check_merchant_access():
        return jsonify({"merchant": None}), 200

    restaurant_name = request.args.get("restaurant_name", "").strip()
    if not restaurant_name:
        return jsonify({"merchant": None}), 200

    merchant = merchant_services.find_merchant_for_restaurant_name(restaurant_name)
    if not merchant:
        return jsonify({"merchant": None}), 200

    return (
        jsonify({"merchant": _merchant_api_payload(merchant)}),
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
    short_name = merchant_services.normalize_short_name(name, payload.get("short_name"))
    website = (payload.get("website") or "").strip()
    description = (payload.get("description") or "").strip() or None
    category = (payload.get("category") or "").strip() or None
    menu_focus = (payload.get("menu_focus") or "").strip() or None
    cuisine = (payload.get("cuisine") or "").strip() or None
    service_level = (payload.get("service_level") or "").strip() or None
    is_chain = bool(payload.get("is_chain", False))

    if not name:
        return jsonify({"status": "error", "message": "Merchant name is required"}), 400

    existing = merchant_services.find_conflicting_merchant(name, short_name=short_name)
    if existing:
        return (
            jsonify(
                {
                    "status": "exists",
                    "merchant": _merchant_api_payload(existing),
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
            "description": description,
            "category": category,
            "menu_focus": menu_focus,
            "cuisine": cuisine,
            "service_level": service_level,
            "is_chain": is_chain,
        },
    )
    return (
        jsonify(
            {
                "status": "success",
                "merchant": _merchant_api_payload(merchant),
            }
        ),
        201,
    )
