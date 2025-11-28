# Google Places API Fields Reference

Complete reference for Google Places API fields used in the Meal Expense Tracker, organized by SKU/tier and endpoint.

**Source**: https://developers.google.com/maps/documentation/places/web-service/data-fields

## Pricing Tiers / SKUs

Google Places API fields are organized into three pricing tiers (SKUs):

- **Essentials Tier** ✅ - Basic fields, lowest cost
- **Pro Tier** ⚠️ - Advanced fields, higher cost
- **Enterprise Tier** ❌ - Premium fields, highest cost

**Important**: Many fields have different tiers depending on the endpoint (Place Details vs Search endpoints).

## Fields by SKU and Endpoint

### Place Details SKU

| Field                     | Property Name         | SKU                        | Used In Application                                |
| ------------------------- | --------------------- | -------------------------- | -------------------------------------------------- |
| **ID**                    | `id`                  | ✅ Essentials              | All operations - place identification              |
| **Formatted Address**     | `formattedAddress`    | ✅ Essentials              | Address display, parsing fallback                  |
| **Location**              | `location`            | ✅ Essentials              | Geographic coordinates (lat/lng)                   |
| **Address Components**    | `addressComponents`   | ✅ Essentials              | Structured address parsing (city, state, zip)      |
| **Types**                 | `types`               | ✅ Essentials              | Restaurant categorization, service level detection |
| **Viewport**              | `viewport`            | ✅ Essentials              | Geographic bounds                                  |
| **Display Name**          | `displayName`         | ⚠️ Pro                     | Restaurant names in UI and CLI                     |
| **Primary Type**          | `primaryType`         | ⚠️ Pro                     | Service level detection, type classification       |
| **Business Status**       | `businessStatus`      | ⚠️ Pro                     | Operational status validation                      |
| **Website URI**           | `websiteUri`          | ⚠️ Pro                     | Restaurant website links                           |
| **User Rating Count**     | `userRatingCount`     | ⚠️ Pro                     | Service level confidence scoring                   |
| **Rating**                | `rating`              | ❌ Enterprise              | Rating display, service level detection            |
| **National Phone Number** | `nationalPhoneNumber` | ❌ Enterprise              | Phone number display and validation                |
| **Price Level**           | `priceLevel`          | ⚠️ Pro (may be deprecated) | Price level indicators (0-4)                       |

### Text Search SKU

| Field                 | Property Name             | SKU      | Used In Application                        |
| --------------------- | ------------------------- | -------- | ------------------------------------------ |
| **ID**                | `places.id`               | ⚠️ Pro\* | Place identification (inherently included) |
| **Formatted Address** | `places.formattedAddress` | ⚠️ Pro   | Address display in search results          |
| **Location**          | `places.location`         | ⚠️ Pro   | Geographic coordinates                     |
| **Display Name**      | `places.displayName`      | ⚠️ Pro   | Restaurant names in search results         |
| **Primary Type**      | `places.primaryType`      | ⚠️ Pro   | Restaurant type filtering                  |
| **Business Status**   | `places.businessStatus`   | ⚠️ Pro   | Filter out closed restaurants              |
| **Types**             | `places.types`            | ⚠️ Pro   | Restaurant categorization                  |

\*Note: While `id` may show as Pro tier in documentation, place IDs are inherently included in search results.

### Nearby Search SKU

| Field                 | Property Name             | SKU    | Used In Application    |
| --------------------- | ------------------------- | ------ | ---------------------- |
| **Formatted Address** | `places.formattedAddress` | ⚠️ Pro | Address display        |
| **Location**          | `places.location`         | ⚠️ Pro | Geographic coordinates |
| **Display Name**      | `places.displayName`      | ⚠️ Pro | Restaurant names       |
| **Primary Type**      | `places.primaryType`      | ⚠️ Pro | Type filtering         |
| **Business Status**   | `places.businessStatus`   | ⚠️ Pro | Status filtering       |
| **Types**             | `places.types`            | ⚠️ Pro | Categorization         |

## Current Field Masks in Code

### Search Mask

**Location**: `app/services/google_places_service.py:45`

```python
"places.id,places.formattedAddress,places.location,places.displayName,places.primaryType,places.businessStatus,places.types"
```

**Tiers**: Essentials + Pro (search operations require Pro tier for most useful fields)

**Used by**:

- Text search operations (`search_places_by_text`)
- Nearby search operations (`search_places_nearby`)
- Web UI restaurant search (`app/restaurants/routes.py`)

### Comprehensive/CLI Validation Mask

**Location**: `app/services/google_places_service.py:52-55`

```python
"id,formattedAddress,location,addressComponents,displayName,primaryType,businessStatus,types,rating,nationalPhoneNumber,websiteUri,userRatingCount,viewport"
```

**Tiers**: Essentials + Pro + Enterprise

**Used by**:

- Place details API (`get_place_details`)
- CLI restaurant validation (`app/restaurants/cli.py`)
- Restaurant form data mapping (`app/restaurants/routes.py`)

## Field Usage by Feature

### 1. CLI Restaurant Validation

**File**: `app/restaurants/cli.py`

**Field Mask**: `cli_validation` (comprehensive)

**Fields Used**:

- `displayName` (Pro) - Name validation
- `addressComponents` (Essentials) - Address component validation
- `primaryType`, `types` (Pro) - Type/status validation
- `rating` (Enterprise) - Rating validation
- `nationalPhoneNumber` (Enterprise) - Phone validation
- `websiteUri` (Pro) - Website validation
- `priceLevel` (Pro) - Price level validation

**Code Locations**:

- `_validate_restaurant_with_google()` - Retrieves place details
- `_check_name_mismatch()` - Validates restaurant name
- `_check_price_level_mismatch()` - Validates price level
- `_check_website_mismatch()` - Validates website

### 2. Web UI Restaurant Search

**File**: `app/restaurants/routes.py`

**Field Mask**: `search`

**Fields Used**:

- `places.displayName` (Pro) - Restaurant names in results
- `places.formattedAddress` (Pro) - Address display
- `places.location` (Pro) - Geographic coordinates
- `places.primaryType`, `places.types` (Pro) - Type filtering and display
- `places.businessStatus` (Pro) - Status filtering

**Code Locations**:

- `search_places()` route - Main search endpoint
- `_process_search_results()` - Processes search results
- `_filter_place_by_criteria()` - Filters by rating/price level

### 3. Place Details API

**File**: `app/restaurants/routes.py`

**Field Mask**: `comprehensive`

**Fields Used**:

- `displayName` (Pro) - Restaurant name
- `addressComponents` (Essentials) - Structured address parsing
- `rating` (Enterprise) - Rating display
- `nationalPhoneNumber` (Enterprise) - Phone number
- `websiteUri` (Pro) - Website URL
- `primaryType`, `types` (Pro) - Type and service level detection
- `priceLevel` (Pro) - Price level

**Code Locations**:

- `get_place_details()` route - Place details endpoint
- `_map_place_to_restaurant_data()` - Maps Google data to restaurant form

### 4. Service Level Detection

**File**: `app/utils/service_level_detector.py`, `app/services/google_places_service.py`

**Fields Used**:

- `primaryType` (Pro) - Primary classification
- `types` (Pro) - Type array for categorization
- `priceLevel` (Pro) - Price level for confidence scoring

**Code Locations**:

- `detect_service_level_from_data()` - Main detection function
- `analyze_restaurant_types()` - Type analysis

## Cost Implications

### Essentials Tier Requests

- **Place Details**: Can request `id`, `formattedAddress`, `location`, `addressComponents`, `types`, `viewport` at Essentials pricing
- **Search**: Very limited - most useful fields require Pro tier

### Pro Tier Requests

- Required for restaurant names (`displayName`)
- Required for type classification (`primaryType`, `types`)
- Required for search operations (most fields are Pro tier)
- Required for website URLs (`websiteUri`)

### Enterprise Tier Requests

- Required for user ratings (`rating`)
- Required for phone numbers (`nationalPhoneNumber`)

**Note**: Including any Pro or Enterprise field in a request triggers billing at that tier level for the entire request.

## Field Availability Notes

- `priceLevel` may be deprecated in the new Google Places API - code handles gracefully if not returned
- `rating` requires sufficient reviews to be returned
- `addressComponents` is Essentials for Place Details but Pro for Search endpoints
- `types` is Essentials for Place Details but Pro for Search endpoints

## Inline Code Documentation

All field usage in the codebase is annotated with tier comments:

- `# ESSENTIALS TIER` - Basic tier fields
- `# PRO TIER` - Pro tier fields
- `# ENTERPRISE TIER` - Enterprise tier fields

See `app/services/google_places_service.py` for field mask definitions and inline tier documentation.
