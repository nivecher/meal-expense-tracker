"""Address normalization utilities for comparing addresses.

This module provides functions to normalize addresses to USPS standard format
by expanding common abbreviations, which allows semantic comparison of addresses
that may be formatted differently (e.g., "FM 544" vs "Farm to Market Road 544").
"""

import re

# USPS standard abbreviations mapping (abbreviation -> full form)
# Source: USPS Publication 28 - Postal Addressing Standards
USPS_ABBREVIATIONS: dict[str, str] = {
    # Street types
    "ALY": "ALLEY",
    "ANX": "ANNEX",
    "ARC": "ARCADE",
    "AVE": "AVENUE",
    "AV": "AVENUE",
    "BLVD": "BOULEVARD",
    "BVD": "BOULEVARD",
    "BR": "BRANCH",
    "BRG": "BRIDGE",
    "BRK": "BROOK",
    "BG": "BURG",
    "BYP": "BYPASS",
    "BY": "BYPASS",
    "CP": "CAMP",
    "CYN": "CANYON",
    "CPE": "CAPE",
    "CSWY": "CAUSEWAY",
    "CTR": "CENTER",
    "CT": "COURT",
    "CV": "COVE",
    "CRK": "CREEK",
    "CRES": "CRESCENT",
    "CRST": "CREST",
    "XING": "CROSSING",
    "DL": "DALE",
    "DM": "DAM",
    "DR": "DRIVE",
    "DV": "DIVIDE",
    "EST": "ESTATE",
    "EXPY": "EXPRESSWAY",
    "EXT": "EXTENSION",
    "FALLS": "FALLS",
    "FRG": "FORGE",
    "FRK": "FORK",
    "FRST": "FOREST",
    "FRT": "FORT",
    "FRY": "FERRY",
    "FLD": "FIELD",
    "FLDS": "FIELDS",
    "FLT": "FLAT",
    "FL": "FLOOR",
    "FM": "FARM TO MARKET ROAD",
    "FRD": "FORD",
    "FT": "FORT",
    "FWY": "FREEWAY",
    "GDN": "GARDEN",
    "GDNS": "GARDENS",
    "GTWY": "GATEWAY",
    "GLN": "GLEN",
    "GRN": "GREEN",
    "GRV": "GROVE",
    "HBR": "HARBOR",
    "HVN": "HAVEN",
    "HTS": "HEIGHTS",
    "HWY": "HIGHWAY",
    "HL": "HILL",
    "HLS": "HILLS",
    "HOLW": "HOLLOW",
    "INLT": "INLET",
    "IS": "ISLAND",
    "ISS": "ISLANDS",
    "ISLE": "ISLE",
    "JCT": "JUNCTION",
    "KY": "KEY",
    "KNLS": "KNOLLS",
    "KNL": "KNOLL",
    "LK": "LAKE",
    "LKS": "LAKES",
    "LNDG": "LANDING",
    "LN": "LANE",
    "LGT": "LIGHT",
    "LF": "LOAF",
    "LBBY": "LOBBY",
    "LCK": "LOCK",
    "LCKS": "LOCKS",
    "LDG": "LODGE",
    "LOOP": "LOOP",
    "MALL": "MALL",
    "MNR": "MANOR",
    "MDW": "MEADOW",
    "MDWS": "MEADOWS",
    "MEWS": "MEWS",
    "ML": "MILE",
    "MLS": "MILES",
    "MSN": "MISSION",
    "MTWY": "MOTORWAY",
    "MT": "MOUNT",
    "MTN": "MOUNTAIN",
    "MTNS": "MOUNTAINS",
    "NCK": "NECK",
    "OPAS": "OVERPASS",
    "ORCH": "ORCHARD",
    "OVAL": "OVAL",
    "PARK": "PARK",
    "PKWY": "PARKWAY",
    "PKY": "PARKWAY",
    "PASS": "PASS",
    "PSGE": "PASSAGE",
    "PATH": "PATH",
    "PIKE": "PIKE",
    "PNE": "PINE",
    "PNES": "PINES",
    "PL": "PLACE",
    "PLN": "PLAIN",
    "PLNS": "PLAINS",
    "PLZ": "PLAZA",
    "PT": "POINT",
    "PTS": "POINTS",
    "PRT": "PORT",
    "PRTS": "PORTS",
    "PR": "PRAIRIE",
    "RADL": "RADIAL",
    "RAMP": "RAMP",
    "RNCH": "RANCH",
    "RPD": "RAPID",
    "RPDS": "RAPIDS",
    "RST": "REST",
    "RDG": "RIDGE",
    "RDGS": "RIDGES",
    "RIV": "RIVER",
    "RD": "ROAD",
    "RDS": "ROADS",
    "RTE": "ROUTE",
    "ROW": "ROW",
    "RUE": "RUE",
    "RUN": "RUN",
    "SHL": "SHOAL",
    "SHLS": "SHOALS",
    "SHR": "SHORE",
    "SHRS": "SHORES",
    "SKWY": "SKYWAY",
    "SPG": "SPRING",
    "SPGS": "SPRINGS",
    "SPUR": "SPUR",
    "SQ": "SQUARE",
    "SQS": "SQUARES",
    "STA": "STATION",
    "STRA": "STRAVENUE",
    "STRM": "STREAM",
    "ST": "STREET",
    "STS": "STREETS",
    "SMT": "SUMMIT",
    "TER": "TERRACE",
    "TRCE": "TRACE",
    "TRAK": "TRACK",
    "TRFY": "TRAFFICWAY",
    "TRL": "TRAIL",
    "TRLR": "TRAILER",
    "TUNL": "TUNNEL",
    "TPKE": "TURNPIKE",
    "UN": "UNION",
    "UNS": "UNIONS",
    "UPAS": "UNDERPASS",
    "VLY": "VALLEY",
    "VLYS": "VALLEYS",
    "VIA": "VIA",
    "VW": "VIEW",
    "VWS": "VIEWS",
    "VLG": "VILLAGE",
    "VL": "VILLE",
    "VIS": "VISTA",
    "WALK": "WALK",
    "WALL": "WALL",
    "WAY": "WAY",
    "WAYS": "WAYS",
    "WL": "WELL",
    "WLS": "WELLS",
    # Directional abbreviations
    "N": "NORTH",
    "S": "SOUTH",
    "E": "EAST",
    "W": "WEST",
    "NE": "NORTHEAST",
    "NW": "NORTHWEST",
    "SE": "SOUTHEAST",
    "SW": "SOUTHWEST",
    # Unit designators
    "APT": "APARTMENT",
    "AP": "APARTMENT",
    "BSMT": "BASEMENT",
    "BLDG": "BUILDING",
    "BLD": "BUILDING",
    "DEPT": "DEPARTMENT",
    "DPT": "DEPARTMENT",
    "FRNT": "FRONT",
    "HNGR": "HANGER",
    "HNG": "HANGER",
    "KEY": "KEY",
    "LOT": "LOT",
    "LOWR": "LOWER",
    "OFC": "OFFICE",
    "OF": "OFFICE",
    "PH": "PENTHOUSE",
    "PIER": "PIER",
    "REAR": "REAR",
    "RM": "ROOM",
    "SIDE": "SIDE",
    "SLIP": "SLIP",
    "SPC": "SPACE",
    "SP": "SPACE",
    "STOP": "STOP",
    "STE": "SUITE",
    "SU": "SUITE",
    "UNIT": "UNIT",
    "UPPR": "UPPER",
}


def normalize_address_to_usps(address: str) -> str:
    """Normalize an address to USPS standard format by expanding abbreviations.

    This function expands common address abbreviations (e.g., "FM" -> "FARM TO MARKET ROAD",
    "St" -> "STREET") to their full USPS standard forms for semantic comparison.

    Args:
        address: Address string to normalize

    Returns:
        Normalized address string in USPS standard format

    Examples:
        >>> normalize_address_to_usps("203 FM 544")
        "203 FARM TO MARKET ROAD 544"
        >>> normalize_address_to_usps("123 Main St")
        "123 MAIN STREET"
        >>> normalize_address_to_usps("456 N. Park Ave")
        "456 NORTH PARK AVENUE"
    """
    if not address or not isinstance(address, str):
        return ""

    # Convert to uppercase for consistent comparison
    normalized = address.upper().strip()

    # Remove extra whitespace
    normalized = re.sub(r"\s+", " ", normalized)

    # Split into words while preserving structure
    # We need to handle abbreviations that might be part of larger words
    # Pattern: word boundary, abbreviation, word boundary or end of string
    words = normalized.split()

    result_words: list[str] = []
    i = 0
    while i < len(words):
        word = words[i]
        # Remove trailing punctuation but keep it for context
        word_clean = re.sub(r"[^\w]", "", word)

        # Check if this word is an abbreviation
        if word_clean in USPS_ABBREVIATIONS:
            # Expand the abbreviation
            expanded = USPS_ABBREVIATIONS[word_clean]
            # Preserve any trailing punctuation
            trailing_punct = re.sub(r"[\w]", "", word)
            result_words.append(expanded + trailing_punct)
        else:
            # Check for directional abbreviations that might be standalone
            # Handle cases like "N", "S", "E", "W" as standalone directionals
            if word_clean in ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]:
                expanded = USPS_ABBREVIATIONS.get(word_clean, word_clean)
                trailing_punct = re.sub(r"[\w]", "", word)
                result_words.append(expanded + trailing_punct)
            else:
                # Not an abbreviation, keep as-is
                result_words.append(word)
        i += 1

    # Join words back together
    normalized = " ".join(result_words)

    # Normalize common patterns
    # Handle "FARM TO MARKET ROAD" variations
    normalized = re.sub(r"\bFM\b", "FARM TO MARKET ROAD", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bF\.?M\.?\b", "FARM TO MARKET ROAD", normalized, flags=re.IGNORECASE)

    # Handle numbered routes (e.g., "FM 544" -> "FARM TO MARKET ROAD 544")
    # This is already handled above, but ensure consistency
    normalized = re.sub(r"\bFARM TO MARKET ROAD\s+(\d+)", r"FARM TO MARKET ROAD \1", normalized)

    # Remove extra spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def compare_addresses_semantic(address1: str, address2: str) -> tuple[bool, bool]:
    """Compare two addresses semantically, returning match status and format difference.

    Args:
        address1: First address to compare
        address2: Second address to compare

    Returns:
        Tuple of (is_match, format_differs):
        - is_match: True if addresses match semantically (after normalization)
        - format_differs: True if normalized addresses match but original formats differ

    Examples:
        >>> compare_addresses_semantic("203 Farm to Market Road 544", "203 FM 544")
        (True, True)  # Match semantically, but formats differ
        >>> compare_addresses_semantic("123 Main St", "123 Main Street")
        (True, True)  # Match semantically, but formats differ
        >>> compare_addresses_semantic("123 Main St", "456 Oak Ave")
        (False, False)  # Don't match
    """
    if not address1 or not address2:
        return (False, False)

    # Normalize both addresses
    normalized1 = normalize_address_to_usps(address1)
    normalized2 = normalize_address_to_usps(address2)

    # Check if normalized addresses match
    # Remove punctuation and extra whitespace for comparison
    clean1 = re.sub(r"[^\w\s]", "", normalized1).upper()
    clean2 = re.sub(r"[^\w\s]", "", normalized2).upper()
    clean1 = re.sub(r"\s+", " ", clean1).strip()
    clean2 = re.sub(r"\s+", " ", clean2).strip()

    is_match = clean1 == clean2

    # Check if original formats differ (but normalized versions match)
    original_clean1 = re.sub(r"[^\w\s]", "", address1).upper()
    original_clean2 = re.sub(r"[^\w\s]", "", address2).upper()
    original_clean1 = re.sub(r"\s+", " ", original_clean1).strip()
    original_clean2 = re.sub(r"\s+", " ", original_clean2).strip()

    format_differs = is_match and (original_clean1 != original_clean2)

    return (is_match, format_differs)
