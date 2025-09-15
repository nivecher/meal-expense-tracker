---
trigger: always_on
---

# Google API Standards

## Core Principles

### 🎯 **Modern APIs Only**

- **NEVER** use deprecated Google APIs
- **ALWAYS** use the latest stable Google Places API
- **ZERO** deprecation warnings allowed
- **NO** legacy fallbacks or graceful degradation

### 🧹 **Keep It Simple**

- **Direct API calls** - no complex abstraction layers
- **Minimal code** - focus on user experience
- **Single purpose** - one component, one job
- **Clean architecture** - backend logic on backend, frontend simple

## Google Places API Standards

### ✅ **Required: Use Modern APIs**

#### Autocomplete

```javascript
// ✅ CORRECT: Modern AutocompleteSuggestion API
const suggestions =
  await google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input: query,
    types: ["establishment"],
    componentRestrictions: { country: "us" },
  });

// ❌ WRONG: Deprecated AutocompleteService
const service = new google.maps.places.AutocompleteService();
service.getPlacePredictions(request, callback);
```

#### Place Details

```javascript
// ✅ CORRECT: Modern Place API
const place = new google.maps.places.Place({ id: placeId });
await place.fetchFields({
  fields: [
    "name",
    "formattedAddress",
    "formattedPhoneNumber",
    "website",
    "rating",
  ],
});

// ❌ WRONG: Deprecated PlacesService
const service = new google.maps.places.PlacesService(map);
service.getDetails(request, callback);
```

#### Autocomplete Constructor

```javascript
// ❌ WRONG: Deprecated Autocomplete constructor
const autocomplete = new google.maps.places.Autocomplete(input, options);

// ✅ CORRECT: Modern approach with input listeners
input.addEventListener("input", async (e) => {
  const suggestions =
    await google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions(
      request
    );
  showSuggestions(suggestions);
});
```

### 🚫 **Forbidden APIs**

**NEVER use these deprecated APIs:**

- `google.maps.places.AutocompleteService`
- `google.maps.places.PlacesService`
- `google.maps.places.Autocomplete` constructor
- `google.maps.places.PlacesServiceStatus`
- Any legacy callback-based APIs

### 📝 **Implementation Patterns**

#### Simple Autocomplete Component

```javascript
// ✅ Good: Simple, focused component
class SimpleRestaurantAutocomplete {
  constructor(inputElement) {
    this.input = inputElement;
    this.init();
  }

  async getSuggestions(query) {
    const request = {
      input: query,
      types: ["establishment"],
    };

    return await google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions(
      request
    );
  }

  async getPlaceDetails(placeId) {
    const place = new google.maps.places.Place({ id: placeId });
    await place.fetchFields({ fields: ["name", "formattedAddress"] });
    return place;
  }
}
```

#### Form Population

```javascript
// ✅ Good: Simple form population
async function populateForm(placeData) {
  const fields = {
    name: placeData.name || "",
    address: placeData.formattedAddress || "",
    phone: placeData.formattedPhoneNumber || "",
    website: placeData.website || "",
  };

  Object.entries(fields).forEach(([fieldId, value]) => {
    const field = document.getElementById(fieldId);
    if (field && value) field.value = value;
  });
}
```

### 🔧 **Error Handling**

```javascript
// ✅ Good: Simple error handling
try {
  const suggestions =
    await google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions(
      request
    );
  return suggestions;
} catch (error) {
  console.error("Google Places API error:", error);
  showError("Failed to get suggestions");
  return [];
}
```

### 🎨 **User Experience**

#### Loading States

```javascript
// ✅ Good: Simple loading feedback
function showLoading() {
  suggestionsContainer.innerHTML = `
    <div class="p-3 text-center">
      <div class="spinner-border spinner-border-sm text-primary"></div>
      <span class="ms-2">Loading...</span>
    </div>
  `;
}
```

#### Success Feedback

```javascript
// ✅ Good: Simple success message
function showSuccess(message) {
  const successDiv = document.createElement("div");
  successDiv.className = "alert alert-success alert-dismissible fade show";
  successDiv.innerHTML = `
    <i class="fas fa-check-circle me-2"></i>${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;
  input.parentNode.insertBefore(successDiv, input.nextSibling);
}
```

## Code Quality Standards

### 📏 **Function Limits**

- **Max 20 statements** per function
- **Max 100 lines** per function
- **Max 2 classes** per file
- **Single responsibility** principle

### 🏗️ **Architecture**

- **Backend logic on backend** - keep frontend simple
- **Testable code** - use unit tests for backend logic
- **No complex abstractions** - direct API calls preferred
- **Clear separation** - HTML/JS separation with data attributes

### 🔍 **Code Review Checklist**

Before submitting Google API code, verify:

- [ ] **No deprecated APIs** used
- [ ] **Modern Google Places API** only
- [ ] **Zero deprecation warnings** possible
- [ ] **Simple, focused** functionality
- [ ] **Direct API calls** (no complex abstractions)
- [ ] **Error handling** included
- [ ] **User feedback** provided
- [ ] **Mobile responsive** design
- [ ] **Accessible** implementation

### 🚨 **Common Anti-Patterns**

#### ❌ Complex Abstraction Layers

```javascript
// ❌ WRONG: Over-engineered abstraction
class GooglePlacesServiceManager {
  constructor() {
    this.serviceLayer = new ServiceLayer();
    this.apiVersionManager = new ApiVersionManager();
    this.fallbackHandler = new FallbackHandler();
  }

  async getSuggestions(query) {
    return await this.serviceLayer.processRequest(query);
  }
}
```

#### ❌ Legacy API Usage

```javascript
// ❌ WRONG: Using deprecated APIs
function getSuggestions(query) {
  return new Promise((resolve, reject) => {
    const service = new google.maps.places.AutocompleteService();
    service.getPlacePredictions({ input: query }, (predictions, status) => {
      if (status === google.maps.places.PlacesServiceStatus.OK) {
        resolve(predictions);
      } else {
        reject(new Error(status));
      }
    });
  });
}
```

#### ❌ Complex Field Mapping

```javascript
// ❌ WRONG: Overly complex field mapping
function mapGooglePlacesToFormFields(
  placeData,
  context,
  options,
  mappingConfig
) {
  const fieldMappings = getFieldMappingsForContext(context);
  const processedData = processPlaceData(placeData, options);
  return applyMappingConfig(processedData, mappingConfig, fieldMappings);
}
```

## Enforcement

This rule is **MANDATORY** for all Google API code. Code that violates these standards will be rejected.

**Key Requirements:**

- ✅ Use **ONLY** modern Google Places APIs
- ✅ **Zero** deprecation warnings
- ✅ **Simple, direct** API calls
- ✅ **Clean, focused** components
- ✅ **Testable** backend logic
- ✅ **Simple** frontend code

**Remember:** The goal is **simple data entry with Google data** - not complex abstractions or legacy compatibility.
