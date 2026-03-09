## 1. Restaurant List Visibility

- [ ] Add linked/unlinked merchant status display to restaurant list rows and mobile/card variants.
- [ ] Add merchant status filter support in restaurant list route and UI.
- [ ] Add linked and unlinked counts to the restaurant list header.
- [ ] Add a visible CTA from the restaurant list to review unlinked restaurants.

## 2. Restaurant Form Merchant Panel

- [ ] Replace the current merchant input presentation with an explicit `Brand / Merchant` association section.
- [ ] Add an empty-state CTA for unlinked restaurants on add/edit form.
- [ ] Add a linked-merchant summary state with `change` and `clear` actions.
- [ ] Ensure merchant association state updates the display-preview behavior correctly.

## 3. Merchant Creation Flow

- [ ] Expand quick-add merchant UI to include category selection.
- [ ] Update quick-add merchant API to accept and persist category.
- [ ] Improve create-and-link affordance so users do not need to discover it through autocomplete failure.
- [ ] Add validation and conflict handling for category-inclusive merchant creation.

## 4. Suggested Merchant Flow

- [ ] Add a backend endpoint or route helper that returns best merchant suggestion for a restaurant name.
- [ ] Show suggested merchant UI in the restaurant form when a strong match exists.
- [ ] Add one-click acceptance of suggested merchant matches.
- [ ] Ensure suggestions do not override explicit user-selected merchants.

## 5. Unlinked Restaurant Cleanup Flow

- [ ] Add a filtered unlinked-restaurants experience from the main restaurant list CTA.
- [ ] Show suggested merchant matches in the cleanup view.
- [ ] Add quick actions for `accept suggestion`, `choose merchant`, and `create merchant`.
- [ ] Add a lightweight bulk action for obvious matches.

## 6. Testing

- [ ] Add route tests for merchant status filtering and counts in restaurant list.
- [ ] Add route/API tests for suggested merchant responses.
- [ ] Add merchant quick-add tests covering category submission.
- [ ] Add UI behavior tests for explicit merchant association states on the restaurant form.
- [ ] Add regression tests ensuring existing auto-link behavior still works when merchant is unset.
