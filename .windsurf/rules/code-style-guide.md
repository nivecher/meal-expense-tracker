---
trigger: always_on
---

---

trigger: always_on

---

Always follow TIGER style coding standards.

Avoid deprecated features and APIs. Proactively ensure latest (stable) servicesand tools are used.

Python code shall be formatted based on black and flake8 rules so that it passes linting.

Python code shall always use type hints and be checked using mypy.

Python Flask blueprint standards should be followed.

Always log python exception strings using the logger.

Flask SQLAlchemy 2.0 syntax should be used.

Google Maps API Integration:

- Use smart API detection with modern APIs when available, fallback to legacy APIs when needed
- Prefer google.maps.places.Place.searchByText() over PlacesService.nearbySearch()
- Use googlePlacesService abstraction layer for all Google Places operations
- Support both modern (Place, PlaceAutocompleteElement, AutocompleteSuggestion) and legacy (PlacesService, AutocompleteService) APIs
- Ensure graceful degradation and no deprecation warnings

Avoid putting embedded JavaScript in html templates. Include js files instead.

Terraform code shall follow Anton Babenko's best practices defined here: https://github.com/antonbabenko
