"""Rewards program routes."""

from __future__ import annotations

import csv
from email.utils import parseaddr
import io
import json
from typing import Any

from flask import Response, abort, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.loyalty import bp, services as loyalty_services
from app.loyalty.forms import LoyaltyImportForm
from app.merchants import services as merchant_services
from app.utils.phone_utils import normalize_phone_for_storage


def _require_loyalty_access() -> Any | None:
    """Require advanced feature access for loyalty pages."""
    if not (current_user.has_advanced_features or current_user.is_admin):
        flash("Loyalty is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))
    return None


def _validate_optional_email(value: str, field_label: str) -> str:
    """Validate an optional email field and return the normalized value."""
    normalized = value.strip()
    if not normalized:
        return ""
    parsed_name, parsed_email = parseaddr(normalized)
    if parsed_name or not parsed_email or "@" not in parsed_email:
        raise ValueError(f"{field_label} must be a valid email address")
    local_part, _, domain = parsed_email.partition("@")
    if not local_part or "." not in domain:
        raise ValueError(f"{field_label} must be a valid email address")
    return parsed_email


def _build_rewards_form_data() -> dict[str, Any]:
    """Build rewards form data from the current request."""
    membership_email = request.form.get("membership_email", "").strip()
    membership_phone = normalize_phone_for_storage(request.form.get("membership_phone")) or ""
    if request.form.get("use_default_email") == "on" and current_user.email:
        membership_email = current_user.email
    if request.form.get("use_default_phone") == "on" and current_user.phone:
        membership_phone = current_user.phone

    return {
        "name": request.form.get("name", "").strip(),
        "website": request.form.get("website", "").strip(),
        "portal_url": request.form.get("portal_url", "").strip(),
        "notes": request.form.get("notes", "").strip(),
        "membership_email": _validate_optional_email(membership_email, "Membership email"),
        "membership_phone": membership_phone,
        "portal_username": request.form.get("portal_username", "").strip(),
        "account_number": request.form.get("account_number", "").strip(),
        "tier_name": request.form.get("tier_name", "").strip(),
        "account_notes": request.form.get("account_notes", "").strip(),
        "use_default_email": request.form.get("use_default_email") == "on",
        "use_default_phone": request.form.get("use_default_phone") == "on",
    }


def _get_prefill_merchant() -> Any | None:
    """Resolve an optional merchant context for creating a rewards program."""
    merchant_id_raw = request.values.get("merchant_id", "").strip()
    if not merchant_id_raw.isdigit():
        return None
    return merchant_services.get_merchant(int(merchant_id_raw))


@bp.route("/")
@login_required
def list_rewards_programs() -> Any:
    """Show rewards programs for the current user."""
    access_response = _require_loyalty_access()
    if access_response is not None:
        return access_response

    search = request.args.get("q", "").strip()
    link_status = request.args.get("link_status", "").strip().lower()
    programs = loyalty_services.get_rewards_programs_for_user(current_user.id, search=search)
    linked_merchant_counts = loyalty_services.get_linked_merchant_counts_for_user(current_user.id)
    if link_status == "unlinked":
        programs = [program for program in programs if linked_merchant_counts.get(program.id, 0) == 0]
    elif link_status == "linked":
        programs = [program for program in programs if linked_merchant_counts.get(program.id, 0) > 0]
    stats = loyalty_services.get_rewards_stats(current_user.id)
    linked_merchants_by_program = {
        program.id: loyalty_services.get_linked_merchants_for_program(current_user.id, program.id)
        for program in programs
    }
    return render_template(
        "loyalty/list.html",
        rewards_programs=programs,
        stats=stats,
        search=search,
        link_status=link_status,
        linked_merchant_counts=linked_merchant_counts,
        linked_merchants_by_program=linked_merchants_by_program,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_rewards_program() -> Any:
    """Create a rewards program."""
    access_response = _require_loyalty_access()
    if access_response is not None:
        return access_response

    prefill_merchant = _get_prefill_merchant()
    requested_website = request.values.get("website", "").strip()
    prefill = {
        "name": "",
        "website": prefill_merchant.website if prefill_merchant and prefill_merchant.website else requested_website,
        "portal_url": "",
        "notes": "",
        "membership_email": current_user.email or "",
        "membership_phone": current_user.phone or "",
        "portal_username": "",
        "account_number": "",
        "tier_name": "",
        "account_notes": "",
        "use_default_email": bool(current_user.email),
        "use_default_phone": bool(current_user.phone),
        "merchant_id": str(prefill_merchant.id) if prefill_merchant and prefill_merchant.id is not None else "",
    }
    if request.method == "POST":
        try:
            prefill = _build_rewards_form_data()
            program = loyalty_services.create_rewards_program_with_account(current_user.id, prefill)
            merchant_id_raw = request.form.get("merchant_id", "").strip()
            if merchant_id_raw.isdigit():
                loyalty_services.set_merchant_rewards_program_for_user(
                    current_user.id,
                    int(merchant_id_raw),
                    program.id,
                )
        except ValueError as exc:
            flash(str(exc), "error")
            if "merchant_id" not in prefill:
                prefill["merchant_id"] = request.form.get("merchant_id", "").strip()
            return render_template("loyalty/form.html", program=None, prefill=prefill)
        flash(f"Rewards program '{program.name}' created successfully", "success")
        return redirect(url_for("loyalty.view_rewards_program", program_id=program.id))

    return render_template("loyalty/form.html", program=None, prefill=prefill)


@bp.route("/<int:program_id>")
@login_required
def view_rewards_program(program_id: int) -> Any:
    """View a rewards program."""
    access_response = _require_loyalty_access()
    if access_response is not None:
        return access_response

    program = loyalty_services.get_rewards_program(program_id, current_user.id)
    if program is None:
        abort(404, description="Rewards program not found")
    linked_merchants = loyalty_services.get_linked_merchants_for_program(current_user.id, program.id)
    available_merchants = loyalty_services.get_unlinked_merchants_for_user(current_user.id)
    return render_template(
        "loyalty/detail.html",
        program=program,
        linked_merchants=linked_merchants,
        available_merchants=available_merchants,
    )


@bp.route("/<int:program_id>/link-merchant", methods=["POST"])
@login_required
def link_merchant_to_rewards_program(program_id: int) -> Any:
    """Link an existing merchant to a rewards program."""
    access_response = _require_loyalty_access()
    if access_response is not None:
        return access_response

    program = loyalty_services.get_rewards_program(program_id, current_user.id)
    if program is None:
        abort(404, description="Rewards program not found")

    merchant_id_raw = request.form.get("merchant_id", "").strip()
    if not merchant_id_raw.isdigit():
        flash("Select a merchant to link.", "warning")
        return redirect(url_for("loyalty.view_rewards_program", program_id=program.id))

    loyalty_services.set_merchant_rewards_program_for_user(current_user.id, int(merchant_id_raw), program.id)
    flash("Merchant linked to rewards program.", "success")
    return redirect(url_for("loyalty.view_rewards_program", program_id=program.id))


@bp.route("/<int:program_id>/edit", methods=["GET", "POST"])
@login_required
def edit_rewards_program(program_id: int) -> Any:
    """Edit a rewards program."""
    access_response = _require_loyalty_access()
    if access_response is not None:
        return access_response

    program = loyalty_services.get_rewards_program(program_id, current_user.id)
    if program is None:
        abort(404, description="Rewards program not found")

    account = program.rewards_account
    account_membership_email = account.membership_email if account and account.membership_email else ""
    account_membership_phone = account.membership_phone if account and account.membership_phone else ""
    prefill = {
        "name": program.name,
        "website": program.website or "",
        "portal_url": program.portal_url or "",
        "notes": program.notes or "",
        "membership_email": account_membership_email,
        "membership_phone": account_membership_phone,
        "portal_username": (account.portal_username or "") if account else "",
        "account_number": (account.account_number or "") if account else "",
        "tier_name": (account.tier_name or "") if account else "",
        "account_notes": (account.notes or "") if account else "",
        "use_default_email": bool(current_user.email and account_membership_email == current_user.email),
        "use_default_phone": bool(current_user.phone and account_membership_phone == current_user.phone),
    }
    if request.method == "POST":
        try:
            prefill = _build_rewards_form_data()
            loyalty_services.update_rewards_program_with_account(program, prefill)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("loyalty/form.html", program=program, prefill=prefill)
        flash(f"Rewards program '{program.name}' updated successfully", "success")
        return redirect(url_for("loyalty.view_rewards_program", program_id=program.id))

    return render_template("loyalty/form.html", program=program, prefill=prefill)


@bp.route("/export")
@login_required
def export_rewards_programs() -> Response:
    """Export rewards programs as CSV or JSON."""
    access_response = _require_loyalty_access()
    if access_response is not None:
        return access_response

    format_type = request.args.get("format", "csv").lower()
    is_sample = request.args.get("sample", "false").lower() == "true"

    if format_type not in {"csv", "json"}:
        flash("Unsupported export format", "warning")
        return redirect(url_for("loyalty.list_rewards_programs"))

    sample_data = [
        {
            "name": "Starbucks Rewards",
            "website": "https://www.starbucks.com",
            "portal_url": "https://www.starbucks.com/account/signin",
            "notes": "Coffee and cafe rewards",
            "membership_email": "me@example.com",
            "membership_phone": "+15551234567",
            "portal_username": "coffeefan",
            "account_number": "ABC123",
            "tier_name": "Gold",
            "account_notes": "Use in-app ordering",
            "linked_merchants": "Starbucks",
        }
    ]

    rows = sample_data if is_sample else loyalty_services.export_rewards_programs_for_user(current_user.id)
    if not rows:
        flash("No loyalty programs found to export", "warning")
        return redirect(url_for("loyalty.list_rewards_programs"))

    filename = "sample_loyalty" if is_sample else "loyalty_programs"
    if format_type == "json":
        response = make_response(json.dumps(rows, indent=2))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.json"
        return response

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys(), quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
    writer.writerows(rows)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
    return response


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_rewards_programs() -> Any:
    """Import rewards programs from a CSV or JSON upload."""
    access_response = _require_loyalty_access()
    if access_response is not None:
        return access_response

    form = LoyaltyImportForm()
    if request.method == "POST" and form.validate_on_submit():
        file = form.file.data
        if file and file.filename:
            success, result_data = loyalty_services.import_rewards_programs_from_file(file, current_user.id)
            if success:
                if result_data.get("success_count", 0) > 0:
                    flash(f"Successfully imported {result_data['success_count']} loyalty programs.", "success")
                if result_data.get("skipped_count", 0) > 0:
                    flash(f"{result_data['skipped_count']} duplicate loyalty programs were skipped.", "warning")
                for warning in result_data.get("warnings", [])[:5]:
                    flash(warning, "warning")
                return redirect(url_for("loyalty.list_rewards_programs"))

            flash(result_data.get("message", "Import failed"), "danger")
            return render_template(
                "loyalty/import.html",
                form=form,
                import_summary=result_data,
                warnings=result_data.get("warnings", []),
                errors=result_data.get("errors", []),
            )

    return render_template("loyalty/import.html", form=form, import_summary=None, warnings=None, errors=None)
