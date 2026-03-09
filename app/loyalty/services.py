"""Service helpers for loyalty rewards."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from sqlalchemy import func, inspect, select
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.loyalty.models import MerchantRewardsLink, RewardsAccount, RewardsProgram
from app.merchants.models import Merchant
from app.utils.phone_utils import normalize_phone_for_storage


def _loyalty_tables_ready() -> bool:
    """Return whether the loyalty tables exist in the current database."""
    bind = db.session.get_bind()
    if bind is None:
        return False
    inspector = inspect(bind)
    required_tables = {"rewards_program", "rewards_account", "merchant_rewards_link"}
    existing_tables = set(inspector.get_table_names())
    return required_tables.issubset(existing_tables)


def get_rewards_programs_for_user(user_id: int, search: str = "") -> list[RewardsProgram]:
    """Return rewards programs for a user."""
    if not _loyalty_tables_ready():
        return []
    stmt = select(RewardsProgram).where(RewardsProgram.user_id == user_id)
    if search.strip():
        needle = f"%{search.strip()}%"
        stmt = stmt.where(
            (RewardsProgram.name.ilike(needle))
            | (RewardsProgram.website.ilike(needle))
            | (RewardsProgram.portal_url.ilike(needle))
        )
    stmt = stmt.order_by(func.lower(RewardsProgram.name))
    return list(db.session.scalars(stmt).all())


def get_rewards_program(program_id: int, user_id: int) -> RewardsProgram | None:
    """Return a single rewards program for a user."""
    if not _loyalty_tables_ready():
        return None
    return db.session.scalar(
        select(RewardsProgram).where(RewardsProgram.id == program_id, RewardsProgram.user_id == user_id)
    )


def get_rewards_program_choices(user_id: int) -> list[tuple[int, str]]:
    """Return reward program choices for merchant forms."""
    return [(program.id, program.name) for program in get_rewards_programs_for_user(user_id)]


def get_linked_merchant_counts_for_user(user_id: int) -> dict[int, int]:
    """Return linked merchant counts keyed by rewards program id."""
    if not _loyalty_tables_ready():
        return {}
    rows = db.session.execute(
        select(
            MerchantRewardsLink.rewards_program_id,
            func.count(MerchantRewardsLink.id),
        )
        .where(MerchantRewardsLink.user_id == user_id)
        .group_by(MerchantRewardsLink.rewards_program_id)
    ).all()
    return {int(program_id): int(count) for program_id, count in rows}


def set_merchant_rewards_program_for_user(user_id: int, merchant_id: int, rewards_program_id: int | None) -> None:
    """Assign or clear the current user's rewards program for a merchant."""
    if not _loyalty_tables_ready():
        if rewards_program_id is None:
            return
        raise ValueError("Loyalty tables are not available yet. Run the database migration first.")
    existing = db.session.scalar(
        select(MerchantRewardsLink).where(
            MerchantRewardsLink.user_id == user_id,
            MerchantRewardsLink.merchant_id == merchant_id,
        )
    )
    if rewards_program_id is None:
        if existing is not None:
            db.session.delete(existing)
            db.session.commit()
        return

    program = get_rewards_program(rewards_program_id, user_id)
    if program is None:
        raise ValueError("Rewards program not found")

    if existing is None:
        existing = MerchantRewardsLink(user_id=user_id, merchant_id=merchant_id, rewards_program_id=program.id)
        db.session.add(existing)
    else:
        existing.rewards_program_id = program.id
    db.session.commit()


def get_merchant_rewards_links_for_user(user_id: int, merchant_ids: list[int]) -> dict[int, MerchantRewardsLink]:
    """Return rewards links keyed by merchant id for a user."""
    if not _loyalty_tables_ready():
        return {}
    if not merchant_ids:
        return {}
    rows = db.session.scalars(
        select(MerchantRewardsLink).where(
            MerchantRewardsLink.user_id == user_id,
            MerchantRewardsLink.merchant_id.in_(merchant_ids),
        )
    ).all()
    return {row.merchant_id: row for row in rows}


def get_merchant_rewards_link(user_id: int, merchant_id: int) -> MerchantRewardsLink | None:
    """Return rewards link for a single merchant."""
    if not _loyalty_tables_ready():
        return None
    return db.session.scalar(
        select(MerchantRewardsLink).where(
            MerchantRewardsLink.user_id == user_id,
            MerchantRewardsLink.merchant_id == merchant_id,
        )
    )


def create_rewards_program_with_account(user_id: int, data: dict[str, Any]) -> RewardsProgram:
    """Create a rewards program and its user account details."""
    if not _loyalty_tables_ready():
        raise ValueError("Loyalty tables are not available yet. Run the database migration first.")
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("Rewards program name is required")

    program = RewardsProgram(
        user_id=user_id,
        name=name,
        website=str(data.get("website") or "").strip() or None,
        portal_url=str(data.get("portal_url") or "").strip() or None,
        notes=str(data.get("notes") or "").strip() or None,
    )
    db.session.add(program)
    db.session.flush()

    account = RewardsAccount(
        user_id=user_id,
        rewards_program_id=program.id,
        membership_email=str(data.get("membership_email") or "").strip() or None,
        membership_phone=normalize_phone_for_storage(str(data.get("membership_phone") or "")),
        portal_username=str(data.get("portal_username") or "").strip() or None,
        account_number=str(data.get("account_number") or "").strip() or None,
        tier_name=str(data.get("tier_name") or "").strip() or None,
        notes=str(data.get("account_notes") or "").strip() or None,
    )
    db.session.add(account)
    db.session.commit()
    return program


def update_rewards_program_with_account(program: RewardsProgram, data: dict[str, Any]) -> RewardsProgram:
    """Update a rewards program and account details."""
    if not _loyalty_tables_ready():
        raise ValueError("Loyalty tables are not available yet. Run the database migration first.")
    account = program.rewards_account
    if account is None:
        account = RewardsAccount(user_id=program.user_id, rewards_program_id=program.id)
        db.session.add(account)

    program.name = str(data.get("name") or "").strip() or program.name
    program.website = str(data.get("website") or "").strip() or None
    program.portal_url = str(data.get("portal_url") or "").strip() or None
    program.notes = str(data.get("notes") or "").strip() or None

    account.membership_email = str(data.get("membership_email") or "").strip() or None
    account.membership_phone = normalize_phone_for_storage(str(data.get("membership_phone") or ""))
    account.portal_username = str(data.get("portal_username") or "").strip() or None
    account.account_number = str(data.get("account_number") or "").strip() or None
    account.tier_name = str(data.get("tier_name") or "").strip() or None
    account.notes = str(data.get("account_notes") or "").strip() or None
    db.session.commit()
    return program


def get_rewards_stats(user_id: int) -> dict[str, int]:
    """Return summary stats for rewards programs."""
    if not _loyalty_tables_ready():
        return {
            "total_programs": 0,
            "total_linked_merchants": 0,
            "total_accounts": 0,
            "programs_without_linked_merchants": 0,
        }
    total_programs = (
        db.session.scalar(select(func.count(RewardsProgram.id)).where(RewardsProgram.user_id == user_id)) or 0
    )
    total_linked_merchants = (
        db.session.scalar(select(func.count(MerchantRewardsLink.id)).where(MerchantRewardsLink.user_id == user_id)) or 0
    )
    total_accounts = (
        db.session.scalar(select(func.count(RewardsAccount.id)).where(RewardsAccount.user_id == user_id)) or 0
    )
    linked_program_ids = set(get_linked_merchant_counts_for_user(user_id))
    return {
        "total_programs": int(total_programs),
        "total_linked_merchants": int(total_linked_merchants),
        "total_accounts": int(total_accounts),
        "programs_without_linked_merchants": max(int(total_programs) - len(linked_program_ids), 0),
    }


def get_linked_merchants_for_program(user_id: int, program_id: int) -> list[Merchant]:
    """Return merchants linked to a rewards program for the current user."""
    if not _loyalty_tables_ready():
        return []
    stmt = (
        select(Merchant)
        .join(MerchantRewardsLink, MerchantRewardsLink.merchant_id == Merchant.id)
        .where(
            MerchantRewardsLink.user_id == user_id,
            MerchantRewardsLink.rewards_program_id == program_id,
        )
        .order_by(func.lower(Merchant.name))
    )
    return list(db.session.scalars(stmt).all())


def get_unlinked_merchants_for_user(user_id: int) -> list[Merchant]:
    """Return merchants without any rewards link for the current user."""
    if not _loyalty_tables_ready():
        return []

    linked_merchant_ids_subquery = (
        select(MerchantRewardsLink.merchant_id).where(MerchantRewardsLink.user_id == user_id).subquery()
    )
    stmt = (
        select(Merchant)
        .where(~Merchant.id.in_(select(linked_merchant_ids_subquery.c.merchant_id)))
        .order_by(func.lower(Merchant.name))
    )
    return list(db.session.scalars(stmt).all())


def export_rewards_programs_for_user(user_id: int) -> list[dict[str, Any]]:
    """Return rewards programs in an export-friendly structure."""
    programs = get_rewards_programs_for_user(user_id)
    linked_merchants_by_program = {
        program.id: get_linked_merchants_for_program(user_id, program.id)
        for program in programs
        if program.id is not None
    }
    exported_rows: list[dict[str, Any]] = []
    for program in programs:
        account = program.rewards_account
        linked_merchants = linked_merchants_by_program.get(program.id, [])
        exported_rows.append(
            {
                "name": program.name,
                "website": program.website or "",
                "portal_url": program.portal_url or "",
                "notes": program.notes or "",
                "membership_email": account.membership_email if account and account.membership_email else "",
                "membership_phone": account.membership_phone if account and account.membership_phone else "",
                "portal_username": account.portal_username if account and account.portal_username else "",
                "account_number": account.account_number if account and account.account_number else "",
                "tier_name": account.tier_name if account and account.tier_name else "",
                "account_notes": account.notes if account and account.notes else "",
                "linked_merchants": "; ".join(merchant.name for merchant in linked_merchants),
                "created_at": program.created_at.isoformat() if program.created_at else "",
                "updated_at": program.updated_at.isoformat() if program.updated_at else "",
            }
        )
    return exported_rows


def _find_merchant_for_loyalty_link(merchant_name: str) -> Merchant | None:
    """Resolve a merchant for import by exact name or short name."""
    normalized = merchant_name.strip()
    if not normalized:
        return None
    merchant = db.session.scalar(select(Merchant).where(Merchant.name == normalized))
    if merchant is not None:
        return merchant
    return db.session.scalar(select(Merchant).where(Merchant.short_name == normalized))


def _upsert_merchant_rewards_link(user_id: int, merchant_id: int, rewards_program_id: int) -> None:
    """Create or update the user-scoped rewards link without committing."""
    existing = db.session.scalar(
        select(MerchantRewardsLink).where(
            MerchantRewardsLink.user_id == user_id,
            MerchantRewardsLink.merchant_id == merchant_id,
        )
    )
    if existing is None:
        db.session.add(
            MerchantRewardsLink(
                user_id=user_id,
                merchant_id=merchant_id,
                rewards_program_id=rewards_program_id,
            )
        )
        return
    existing.rewards_program_id = rewards_program_id


def _read_loyalty_import_records(file: FileStorage) -> tuple[list[dict[str, Any]], str | None]:
    """Read loyalty import records from a CSV or JSON upload."""
    filename = (file.filename or "").lower()
    raw_bytes = file.read()
    file.seek(0)
    decoded = raw_bytes.decode("utf-8-sig")

    if filename.endswith(".json"):
        payload = json.loads(decoded)
        if not isinstance(payload, list):
            return [], "JSON loyalty imports must contain a top-level array"
        records = [row for row in payload if isinstance(row, dict)]
        return records, None

    reader = csv.DictReader(io.StringIO(decoded))
    records = [dict(row) for row in reader]
    return records, None


def import_rewards_programs_from_file(file: FileStorage, user_id: int) -> tuple[bool, dict[str, Any]]:
    """Import rewards programs from CSV or JSON."""
    if not _loyalty_tables_ready():
        return False, {"message": "Loyalty tables are not available yet. Run the database migration first."}

    try:
        records, error = _read_loyalty_import_records(file)
        if error:
            return False, {"message": error, "errors": [error]}
    except UnicodeDecodeError:
        return False, {"message": "Unable to decode import file. Use UTF-8 encoded CSV or JSON.", "errors": []}
    except json.JSONDecodeError as exc:
        message = f"Invalid JSON file: {exc}"
        return False, {"message": message, "errors": [message]}
    except Exception as exc:
        message = f"Error processing loyalty import file: {exc}"
        return False, {"message": message, "errors": [message]}

    success_count = 0
    skipped_count = 0
    warnings: list[str] = []
    errors: list[str] = []

    for index, row in enumerate(records, start=2):
        name = str(row.get("name") or "").strip()
        if not name:
            errors.append(f"Row {index}: name is required")
            continue

        existing = db.session.scalar(
            select(RewardsProgram).where(
                RewardsProgram.user_id == user_id,
                RewardsProgram.name == name,
            )
        )
        if existing is not None:
            skipped_count += 1
            warnings.append(f"Row {index}: skipped duplicate rewards program '{name}'")
            continue

        program = RewardsProgram(
            user_id=user_id,
            name=name,
            website=str(row.get("website") or "").strip() or None,
            portal_url=str(row.get("portal_url") or "").strip() or None,
            notes=str(row.get("notes") or "").strip() or None,
        )
        db.session.add(program)
        db.session.flush()

        account = RewardsAccount(
            user_id=user_id,
            rewards_program_id=program.id,
            membership_email=str(row.get("membership_email") or "").strip() or None,
            membership_phone=str(row.get("membership_phone") or "").strip() or None,
            portal_username=str(row.get("portal_username") or "").strip() or None,
            account_number=str(row.get("account_number") or "").strip() or None,
            tier_name=str(row.get("tier_name") or "").strip() or None,
            notes=str(row.get("account_notes") or "").strip() or None,
        )
        db.session.add(account)

        linked_merchants_raw = str(row.get("linked_merchants") or "").strip()
        merchant_names = [part.strip() for part in linked_merchants_raw.replace(",", ";").split(";") if part.strip()]
        for merchant_name in merchant_names:
            merchant = _find_merchant_for_loyalty_link(merchant_name)
            if merchant is None:
                warnings.append(
                    f"Row {index}: merchant '{merchant_name}' was not found, so it was not linked to '{name}'"
                )
                continue
            _upsert_merchant_rewards_link(user_id, merchant.id, program.id)

        success_count += 1

    if errors and success_count == 0:
        db.session.rollback()
        return False, {
            "message": "Loyalty import failed",
            "errors": errors,
            "warnings": warnings,
            "success_count": 0,
            "skipped_count": skipped_count,
            "error_count": len(errors),
            "has_warnings": bool(warnings),
        }

    db.session.commit()
    return True, {
        "message": "Loyalty import completed",
        "errors": errors,
        "warnings": warnings,
        "success_count": success_count,
        "skipped_count": skipped_count,
        "error_count": len(errors),
        "has_warnings": bool(warnings),
    }
