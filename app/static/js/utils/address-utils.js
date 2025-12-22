/**
 * Address normalization utilities for comparing addresses.
 *
 * This module provides functions to normalize addresses to USPS standard format
 * by expanding common abbreviations, which allows semantic comparison of addresses
 * that may be formatted differently (e.g., "FM 544" vs "Farm to Market Road 544").
 */

// USPS standard abbreviations mapping (abbreviation -> full form)
// Source: USPS Publication 28 - Postal Addressing Standards
const USPS_ABBREVIATIONS = {
  // Street types
  ALY: 'ALLEY',
  ANX: 'ANNEX',
  ARC: 'ARCADE',
  AVE: 'AVENUE',
  AV: 'AVENUE',
  BLVD: 'BOULEVARD',
  BVD: 'BOULEVARD',
  BR: 'BRANCH',
  BRG: 'BRIDGE',
  BRK: 'BROOK',
  BG: 'BURG',
  BYP: 'BYPASS',
  BY: 'BYPASS',
  CP: 'CAMP',
  CYN: 'CANYON',
  CPE: 'CAPE',
  CSWY: 'CAUSEWAY',
  CTR: 'CENTER',
  CT: 'COURT',
  CV: 'COVE',
  CRK: 'CREEK',
  CRES: 'CRESCENT',
  CRST: 'CREST',
  XING: 'CROSSING',
  DL: 'DALE',
  DM: 'DAM',
  DR: 'DRIVE',
  DV: 'DIVIDE',
  EST: 'ESTATE',
  EXPY: 'EXPRESSWAY',
  EXT: 'EXTENSION',
  FALLS: 'FALLS',
  FRG: 'FORGE',
  FRK: 'FORK',
  FRST: 'FOREST',
  FRT: 'FORT',
  FRY: 'FERRY',
  FLD: 'FIELD',
  FLDS: 'FIELDS',
  FLT: 'FLAT',
  FL: 'FLOOR',
  FM: 'FARM TO MARKET ROAD',
  FRD: 'FORD',
  FT: 'FORT',
  FWY: 'FREEWAY',
  GDN: 'GARDEN',
  GDNS: 'GARDENS',
  GTWY: 'GATEWAY',
  GLN: 'GLEN',
  GRN: 'GREEN',
  GRV: 'GROVE',
  HBR: 'HARBOR',
  HVN: 'HAVEN',
  HTS: 'HEIGHTS',
  HWY: 'HIGHWAY',
  HL: 'HILL',
  HLS: 'HILLS',
  HOLW: 'HOLLOW',
  INLT: 'INLET',
  IS: 'ISLAND',
  ISS: 'ISLANDS',
  ISLE: 'ISLE',
  JCT: 'JUNCTION',
  KY: 'KEY',
  KNLS: 'KNOLLS',
  KNL: 'KNOLL',
  LK: 'LAKE',
  LKS: 'LAKES',
  LNDG: 'LANDING',
  LN: 'LANE',
  LGT: 'LIGHT',
  LF: 'LOAF',
  LBBY: 'LOBBY',
  LCK: 'LOCK',
  LCKS: 'LOCKS',
  LDG: 'LODGE',
  LOOP: 'LOOP',
  MALL: 'MALL',
  MNR: 'MANOR',
  MDW: 'MEADOW',
  MDWS: 'MEADOWS',
  MEWS: 'MEWS',
  ML: 'MILE',
  MLS: 'MILES',
  MSN: 'MISSION',
  MTWY: 'MOTORWAY',
  MT: 'MOUNT',
  MTN: 'MOUNTAIN',
  MTNS: 'MOUNTAINS',
  NCK: 'NECK',
  OPAS: 'OVERPASS',
  ORCH: 'ORCHARD',
  OVAL: 'OVAL',
  PARK: 'PARK',
  PKWY: 'PARKWAY',
  PKY: 'PARKWAY',
  PASS: 'PASS',
  PSGE: 'PASSAGE',
  PATH: 'PATH',
  PIKE: 'PIKE',
  PNE: 'PINE',
  PNES: 'PINES',
  PL: 'PLACE',
  PLN: 'PLAIN',
  PLNS: 'PLAINS',
  PLZ: 'PLAZA',
  PT: 'POINT',
  PTS: 'POINTS',
  PRT: 'PORT',
  PRTS: 'PORTS',
  PR: 'PRAIRIE',
  RADL: 'RADIAL',
  RAMP: 'RAMP',
  RNCH: 'RANCH',
  RPD: 'RAPID',
  RPDS: 'RAPIDS',
  RST: 'REST',
  RDG: 'RIDGE',
  RDGS: 'RIDGES',
  RIV: 'RIVER',
  RD: 'ROAD',
  RDS: 'ROADS',
  RTE: 'ROUTE',
  ROW: 'ROW',
  RUE: 'RUE',
  RUN: 'RUN',
  SHL: 'SHOAL',
  SHLS: 'SHOALS',
  SHR: 'SHORE',
  SHRS: 'SHORES',
  SKWY: 'SKYWAY',
  SPG: 'SPRING',
  SPGS: 'SPRINGS',
  SPUR: 'SPUR',
  SQ: 'SQUARE',
  SQS: 'SQUARES',
  STA: 'STATION',
  STRA: 'STRAVENUE',
  STRM: 'STREAM',
  ST: 'STREET',
  STS: 'STREETS',
  SMT: 'SUMMIT',
  TER: 'TERRACE',
  TRCE: 'TRACE',
  TRAK: 'TRACK',
  TRFY: 'TRAFFICWAY',
  TRL: 'TRAIL',
  TRLR: 'TRAILER',
  TUNL: 'TUNNEL',
  TPKE: 'TURNPIKE',
  UN: 'UNION',
  UNS: 'UNIONS',
  UPAS: 'UNDERPASS',
  VLY: 'VALLEY',
  VLYS: 'VALLEYS',
  VIA: 'VIA',
  VW: 'VIEW',
  VWS: 'VIEWS',
  VLG: 'VILLAGE',
  VL: 'VILLE',
  VIS: 'VISTA',
  WALK: 'WALK',
  WALL: 'WALL',
  WAY: 'WAY',
  WAYS: 'WAYS',
  WL: 'WELL',
  WLS: 'WELLS',
  // Directional abbreviations
  N: 'NORTH',
  S: 'SOUTH',
  E: 'EAST',
  W: 'WEST',
  NE: 'NORTHEAST',
  NW: 'NORTHWEST',
  SE: 'SOUTHEAST',
  SW: 'SOUTHWEST',
  // Unit designators
  APT: 'APARTMENT',
  AP: 'APARTMENT',
  BSMT: 'BASEMENT',
  BLDG: 'BUILDING',
  BLD: 'BUILDING',
  DEPT: 'DEPARTMENT',
  DPT: 'DEPARTMENT',
  FRNT: 'FRONT',
  HNGR: 'HANGER',
  HNG: 'HANGER',
  KEY: 'KEY',
  LOT: 'LOT',
  LOWR: 'LOWER',
  OFC: 'OFFICE',
  OF: 'OFFICE',
  PH: 'PENTHOUSE',
  PIER: 'PIER',
  REAR: 'REAR',
  RM: 'ROOM',
  SIDE: 'SIDE',
  SLIP: 'SLIP',
  SPC: 'SPACE',
  SP: 'SPACE',
  STOP: 'STOP',
  STE: 'SUITE',
  SU: 'SUITE',
  UNIT: 'UNIT',
  UPPR: 'UPPER',
};

/**
 * Normalize an address to USPS standard format by expanding abbreviations.
 *
 * @param {string} address - Address string to normalize
 * @returns {string} Normalized address string in USPS standard format
 *
 * @example
 * normalizeAddressToUSPS("203 FM 544")
 * // Returns: "203 FARM TO MARKET ROAD 544"
 *
 * @example
 * normalizeAddressToUSPS("123 Main St")
 * // Returns: "123 MAIN STREET"
 */
function normalizeAddressToUSPS(address) {
  if (!address || typeof address !== 'string') {
    return '';
  }

  // Convert to uppercase for consistent comparison
  let normalized = address.toUpperCase().trim();

  // Remove extra whitespace
  normalized = normalized.replace(/\s+/g, ' ');

  // Split into words
  const words = normalized.split(' ');
  const resultWords = [];

  for (let i = 0; i < words.length; i++) {
    const word = words[i];
    // Remove trailing punctuation but keep it for context
    const wordClean = word.replace(/[^\w]/g, '');

    // Check if this word is an abbreviation
    if (wordClean in USPS_ABBREVIATIONS) {
      // Expand the abbreviation
      const expanded = USPS_ABBREVIATIONS[wordClean];
      // Preserve any trailing punctuation
      const trailingPunct = word.replace(/[\w]/g, '');
      resultWords.push(expanded + trailingPunct);
    } else {
      // Not an abbreviation, keep as-is
      resultWords.push(word);
    }
  }

  // Join words back together
  normalized = resultWords.join(' ');

  // Normalize common patterns
  // Handle "FARM TO MARKET ROAD" variations
  normalized = normalized.replace(/\bFM\b/g, 'FARM TO MARKET ROAD');
  normalized = normalized.replace(/\bF\.?M\.?\b/g, 'FARM TO MARKET ROAD');

  // Handle numbered routes (e.g., "FM 544" -> "FARM TO MARKET ROAD 544")
  normalized = normalized.replace(/\bFARM TO MARKET ROAD\s+(\d+)/g, 'FARM TO MARKET ROAD $1');

  // Remove extra spaces
  normalized = normalized.replace(/\s+/g, ' ').trim();

  return normalized;
}

/**
 * Compare two addresses semantically, returning match status and format difference.
 *
 * @param {string} address1 - First address to compare
 * @param {string} address2 - Second address to compare
 * @returns {{isMatch: boolean, formatDiffers: boolean}} Object with match status:
 *   - isMatch: True if addresses match semantically (after normalization)
 *   - formatDiffers: True if normalized addresses match but original formats differ
 *
 * @example
 * compareAddressesSemantic("203 Farm to Market Road 544", "203 FM 544")
 * // Returns: {isMatch: true, formatDiffers: true}
 *
 * @example
 * compareAddressesSemantic("123 Main St", "123 Main Street")
 * // Returns: {isMatch: true, formatDiffers: true}
 */
function compareAddressesSemantic(address1, address2) {
  if (!address1 || !address2) {
    return { isMatch: false, formatDiffers: false };
  }

  // Normalize both addresses
  const normalized1 = normalizeAddressToUSPS(address1);
  const normalized2 = normalizeAddressToUSPS(address2);

  // Remove punctuation and extra whitespace for comparison
  const clean1 = normalized1.replace(/[^\w\s]/g, '').toUpperCase().replace(/\s+/g, ' ').trim();
  const clean2 = normalized2.replace(/[^\w\s]/g, '').toUpperCase().replace(/\s+/g, ' ').trim();

  const isMatch = clean1 === clean2;

  // Check if original formats differ (but normalized versions match)
  const originalClean1 = address1.replace(/[^\w\s]/g, '').toUpperCase().replace(/\s+/g, ' ').trim();
  const originalClean2 = address2.replace(/[^\w\s]/g, '').toUpperCase().replace(/\s+/g, ' ').trim();

  const formatDiffers = isMatch && (originalClean1 !== originalClean2);

  return { isMatch, formatDiffers };
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    normalizeAddressToUSPS,
    compareAddressesSemantic,
  };
}

// Make functions available globally for use in HTML
if (typeof window !== 'undefined') {
  window.AddressUtils = {
    normalizeAddressToUSPS,
    compareAddressesSemantic,
  };
}
