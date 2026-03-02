"""Tests for address normalization utilities (USPS state/country and semantic comparison)."""

import pytest

from app.utils.address_utils import (
    compare_addresses_semantic,
    normalize_address_to_usps,
    normalize_country_to_iso2,
    normalize_state_to_usps,
)


class TestNormalizeStateToUsps:
    """Tests for normalize_state_to_usps."""

    def test_texas_to_tx(self) -> None:
        assert normalize_state_to_usps("Texas") == "TX"

    def test_tx_unchanged(self) -> None:
        assert normalize_state_to_usps("TX") == "TX"

    def test_missouri_to_mo(self) -> None:
        assert normalize_state_to_usps("Missouri") == "MO"

    def test_mo_unchanged(self) -> None:
        assert normalize_state_to_usps("MO") == "MO"

    def test_empty_returns_empty(self) -> None:
        assert normalize_state_to_usps("") == ""
        assert normalize_state_to_usps("   ") == ""

    def test_unknown_returns_original(self) -> None:
        assert normalize_state_to_usps("Ontario") == "Ontario"
        assert normalize_state_to_usps("XX") == "XX"

    def test_whitespace_trimmed(self) -> None:
        assert normalize_state_to_usps("  Texas  ") == "TX"


class TestNormalizeCountryToIso2:
    """Tests for normalize_country_to_iso2."""

    def test_usa_to_us(self) -> None:
        assert normalize_country_to_iso2("USA") == "US"

    def test_united_states_to_us(self) -> None:
        assert normalize_country_to_iso2("United States") == "US"

    def test_u_s_to_us(self) -> None:
        assert normalize_country_to_iso2("U.S.") == "US"

    def test_u_s_a_to_us(self) -> None:
        assert normalize_country_to_iso2("U.S.A.") == "US"

    def test_united_states_of_america_to_us(self) -> None:
        assert normalize_country_to_iso2("United States of America") == "US"

    def test_us_unchanged(self) -> None:
        assert normalize_country_to_iso2("US") == "US"

    def test_case_insensitive(self) -> None:
        assert normalize_country_to_iso2("usa") == "US"
        assert normalize_country_to_iso2("UNITED STATES") == "US"

    def test_canada_to_ca(self) -> None:
        assert normalize_country_to_iso2("Canada") == "CA"
        assert normalize_country_to_iso2("CA") == "CA"

    def test_uk_to_gb(self) -> None:
        assert normalize_country_to_iso2("United Kingdom") == "GB"
        assert normalize_country_to_iso2("UK") == "GB"
        assert normalize_country_to_iso2("Great Britain") == "GB"
        assert normalize_country_to_iso2("England") == "GB"

    def test_other_country_unchanged(self) -> None:
        assert normalize_country_to_iso2("FR") == "FR"
        assert normalize_country_to_iso2("Germany") == "Germany"

    def test_empty_returns_empty(self) -> None:
        assert normalize_country_to_iso2("") == ""
        assert normalize_country_to_iso2("   ") == ""


class TestCompareAddressesSemantic:
    """Tests for semantic address comparison (USPS abbreviation expansion)."""

    def test_south_state_highway_vs_s_state_hwy(self) -> None:
        """Stored '400 South State Highway 78' should match Google '400 S State Hwy 78'."""
        is_match, _ = compare_addresses_semantic(
            "400 South State Highway 78",
            "400 S State Hwy 78",
        )
        assert is_match is True

    def test_farm_to_market_vs_fm(self) -> None:
        """Farm to Market Road vs FM should match."""
        is_match, _ = compare_addresses_semantic("203 Farm to Market Road 544", "203 FM 544")
        assert is_match is True

    def test_different_addresses_no_match(self) -> None:
        """Different street numbers should not match."""
        is_match, _ = compare_addresses_semantic("123 Main St", "456 Oak Ave")
        assert is_match is False

    def test_empty_addresses_no_match(self) -> None:
        is_match, _ = compare_addresses_semantic("", "123 Main St")
        assert is_match is False
        is_match, _ = compare_addresses_semantic("123 Main St", "")
        assert is_match is False


class TestNormalizeAddressToUsps:
    """Sanity check that normalize_address_to_usps still expands as expected."""

    def test_fm_expanded(self) -> None:
        assert "FARM TO MARKET ROAD" in normalize_address_to_usps("203 FM 544")

    def test_hwy_expanded(self) -> None:
        assert "HIGHWAY" in normalize_address_to_usps("State Hwy 78")
