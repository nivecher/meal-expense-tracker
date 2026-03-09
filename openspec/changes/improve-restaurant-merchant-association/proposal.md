## Why

Associating restaurants with merchants is currently fragmented and hard to discover.

The main usability problems are:

- The restaurant form treats merchant association as a hidden autocomplete behavior instead of a primary workflow.
- Quick add for merchants is only discoverable from the "no results" state and does not allow the user to choose a category.
- Users cannot easily see which restaurants are linked to merchants versus unlinked.
- There is no strong CTA to clean up unlinked restaurants or accept suggested merchant matches.

This causes low merchant-link completion, inconsistent data quality, and unnecessary per-record editing effort.

## What Changes

This change improves the merchant association experience across restaurant create, edit, and list flows.

### 1. Restaurant list visibility

- Add a dedicated merchant status column or status region in restaurant list/table views.
- Show linked merchant name for linked restaurants.
- Show a visible unlinked state for restaurants without a merchant.
- Add filters for `all`, `linked`, and `unlinked`.
- Add summary counts for linked and unlinked restaurants.
- Add a prominent CTA to review and associate unlinked restaurants.

### 2. Restaurant form association flow

- Replace the current hidden-feeling merchant autocomplete flow with an explicit `Brand / Merchant` association panel.
- If no merchant is linked, show an empty state with a CTA such as `Link a merchant`.
- If a merchant is linked, show a compact linked-merchant summary card with actions to change or clear it.
- Keep search for existing merchants, but make it an explicit action rather than only an input convention.
- Replace the current quick-add interaction with an explicit create flow that supports:
  - merchant name
  - short name
  - category
  - website
- After merchant creation, immediately link the new merchant to the restaurant form state.

### 3. Suggested merchant matching

- Surface existing merchant matching rules directly on the restaurant form.
- When a restaurant name strongly matches an existing merchant, show a suggested merchant CTA.
- Allow one-click acceptance of the suggestion.
- If no suggestion exists, offer an explicit create-merchant CTA.

### 4. Cleanup and association CTA flow

- Add an entry point for users to associate restaurants with merchants from the restaurants list and merchant-related screens.
- Provide a focused view for unlinked restaurants with suggested matches and quick actions.
- Support lightweight bulk actions for accepting obvious matches.

## Impact

Expected user-facing outcomes:

- Users can immediately tell which restaurants still need merchant association.
- Merchant creation is discoverable and complete.
- Linking a restaurant to a merchant takes fewer steps.
- Historical cleanup of unlinked restaurants becomes a guided workflow instead of a manual audit.

Expected implementation areas:

- restaurant list templates and filters
- restaurant form template and client-side behavior
- merchant quick-add API and form payload handling
- merchant suggestion API or route support
- tests for list filtering, form flows, and merchant creation/association behavior
