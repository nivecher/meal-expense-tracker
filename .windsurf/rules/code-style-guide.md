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

**See `.windsurf/rules/google-api-standards.md` for comprehensive Google API standards.**

**Core Requirements:**

- Use ONLY modern Google Places APIs - no legacy fallbacks
- Use google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions() for autocomplete
- Use google.maps.places.Place.fetchFields() for place details
- NO deprecated APIs: AutocompleteService, PlacesService, or Autocomplete constructor
- Keep it simple: direct API calls, minimal abstraction layers
- Zero deprecation warnings - use latest stable APIs only

Avoid putting embedded JavaScript in html templates. Include js files instead.

Terraform code shall follow Anton Babenko's best practices defined here: https://github.com/antonbabenko
