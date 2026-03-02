<!-- markdownlint-disable MD060 -->

# Google Places API Field Mapping

This document is the canonical reference for mapping Google Places API (New) fields to the meal expense tracker Restaurant model. We use Essentials tier where possible and Pro tier only when needed for UX (name, cuisine, service level).

## Tier Reference

- **Essentials**: id, formattedAddress, location, addressComponents, postalAddress, addressDescriptor (Place Details)
- **Pro**: displayName, primaryType, types, websiteUri
- **Enterprise**: rating, nationalPhoneNumber, priceLevel (Place Details bills at Enterprise; priceLevel adds no extra cost)

## Planned Field Mapping

### Google to Restaurant Model

| Google Field                | Tier       | Restaurant Field                                                  | Mapping Logic                                       |
| --------------------------- | ---------- | ----------------------------------------------------------------- | --------------------------------------------------- |
| id                          | Essentials | google_place_id                                                   | Direct                                              |
| formattedAddress            | Essentials | formatted_address (display)                                       | Direct                                              |
| location.latitude/longitude | Essentials | latitude, longitude                                               | Direct                                              |
| addressComponents           | Essentials | address_line_1, address_line_2, city, state, postal_code, country | Parse with priority below                           |
| postalAddress               | Essentials | address_line_1, address_line_2, city, state, postal_code, country | Fallback when addressComponents empty               |
| addressDescriptor           | Essentials | located_within                                                    | Landmarks/areas (e.g. "inside Mall of America")     |
| sublocality, premise        | Essentials | located_within                                                    | From addressComponents when addressDescriptor empty |
| displayName.text            | Pro        | name                                                              | Required for UX                                     |
| primaryType                 | Pro        | primary_type, type                                                | For cuisine/service detection                       |
| types                       | Pro        | types                                                             | For cuisine/service_level                           |
| websiteUri                  | Pro        | website                                                           | Strip query params (UTM, etc.) at extraction        |
| priceLevel                  | Enterprise | price_level                                                       | 0–4 ($–$$$$); converted from PRICE*LEVEL*\* strings |

### Address Parsing Priority

1. **addressComponents** (if present):
   - street_number + route -> address_line_1
   - premise, subpremise, sublocality_level_1, floor -> address_line_2 (join if multiple)
   - locality (prefer over sublocality) -> city
   - administrative_area_level_1 -> state (longText preferred)
   - postal_code -> postal_code
   - country -> country
   - Use longText/shortText only (Places API New format)

2. **postalAddress** (if addressComponents empty):
   - addressLines[0] -> address_line_1
   - addressLines[1] -> address_line_2
   - locality -> city
   - administrativeArea -> state
   - postalCode -> postal_code
   - regionCode -> country (map to full name if needed)

3. **parse_formatted_address** (last resort): Existing comma-split heuristic.

### located_within Sources

- **addressDescriptor** (Essentials): Landmarks and areas, e.g. "near Central Park", "inside Mall of America"
- **sublocality** in addressComponents: Neighborhood, district, or venue name
- **premise** in addressComponents: Building or property name

## API Cost Strategy

- **Place Details**: One request per place when user selects (not per search result). Mask includes `websiteUri` (Pro), `nationalPhoneNumber` (Enterprise), and `priceLevel` (Enterprise); request bills at Enterprise. No extra API calls—same single call, more fields.
- **Search**: Unchanged; Place Details on select for full address, cuisine, phone, website.
- **Billing**: Per-request at highest tier. Adding more fields in the same request does not add calls.

## Fields We Skip

| Field           | Tier       | Reason                                                    |
| --------------- | ---------- | --------------------------------------------------------- |
| rating (Google) | Enterprise | Model stores user's personal rating; we do not request it |

## Code Locations

- **Parsing**: `app/services/google_places_service.py` – `parse_address_components`, `parse_postal_address`, `extract_located_within`
- **Mapping**: `app/restaurants/routes.py` – `_map_place_to_restaurant_data`
- **Model update**: `app/restaurants/models.py` – `update_from_google_places`
