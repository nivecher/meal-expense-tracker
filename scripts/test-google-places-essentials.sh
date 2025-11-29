#!/bin/bash
# Test Google Places API (New) with Essentials tier fields only

set -e

# Check for API key
if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
    echo "❌ Error: GOOGLE_MAPS_API_KEY environment variable not set"
    echo "Usage: export GOOGLE_MAPS_API_KEY='your-api-key' && $0"
    exit 1
fi

API_KEY="${GOOGLE_MAPS_API_KEY}"
BASE_URL="https://places.googleapis.com/v1/places"

echo "🧪 Testing Google Places API (New) - Essentials Tier Fields Only"
echo "================================================================"
echo ""

# Test 1: Place Details - Essentials tier
echo "📍 Test 1: Place Details (Essentials tier fields)"
echo "Field mask: id,formattedAddress,location,addressComponents"
echo ""

PLACE_ID="ChIJN1t_tDeuEmsRUsoyG83frY4"  # Google HQ as example
curl -s -X GET \
  "${BASE_URL}/${PLACE_ID}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-Api-Key: ${API_KEY}" \
  -H "X-Goog-FieldMask: id,formattedAddress,location,addressComponents" \
  | jq '.' || echo "Response received (install jq for pretty printing)"

echo ""
echo "---"
echo ""

# Test 2: Text Search - Essentials tier
echo "🔍 Test 2: Text Search (Essentials tier fields)"
echo "Field mask: places.id,places.formattedAddress,places.location"
echo ""

curl -s -X POST \
  "${BASE_URL}:searchText" \
  -H "Content-Type: application/json" \
  -H "X-Goog-Api-Key: ${API_KEY}" \
  -H "X-Goog-FieldMask: places.id,places.formattedAddress,places.location" \
  -d '{
    "textQuery": "pizza restaurant",
    "maxResultCount": 3
  }' \
  | jq '.' || echo "Response received (install jq for pretty printing)"

echo ""
echo "---"
echo ""

# Test 3: Nearby Search - Essentials tier
echo "🗺️  Test 3: Nearby Search (Essentials tier fields)"
echo "Field mask: places.id,places.formattedAddress,places.location"
echo ""

curl -s -X POST \
  "${BASE_URL}:searchNearby" \
  -H "Content-Type: application/json" \
  -H "X-Goog-Api-Key: ${API_KEY}" \
  -H "X-Goog-FieldMask: places.id,places.formattedAddress,places.location" \
  -d '{
    "includedTypes": ["restaurant"],
    "maxResultCount": 3,
    "locationRestriction": {
      "circle": {
        "center": {
          "latitude": 40.7128,
          "longitude": -74.0060
        },
        "radius": 5000
      }
    }
  }' \
  | jq '.' || echo "Response received (install jq for pretty printing)"

echo ""
echo "✅ Tests complete!"
echo ""
echo "All requests used ONLY Essentials tier fields:"
echo "  - id"
echo "  - formattedAddress"
echo "  - location"
echo "  - addressComponents (Place Details only)"
