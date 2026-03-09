## ADDED Requirements

### Requirement: Restaurant list must expose merchant association status

The restaurants list must clearly show whether each restaurant is linked to a merchant.

#### Scenario: Linked restaurant displays merchant

- **GIVEN** a restaurant with a non-null `merchant_id`
- **WHEN** the user views the restaurants list
- **THEN** the restaurant row must display the linked merchant name
- **AND** the row must not be rendered as unlinked

#### Scenario: Unlinked restaurant displays clear status

- **GIVEN** a restaurant with a null `merchant_id`
- **WHEN** the user views the restaurants list
- **THEN** the restaurant row must display an explicit unlinked state
- **AND** the unlinked state must be visually distinguishable from linked rows

#### Scenario: User filters restaurants by merchant linkage

- **GIVEN** a user has a mix of linked and unlinked restaurants
- **WHEN** the user applies the `linked` filter
- **THEN** only linked restaurants must be shown

- **WHEN** the user applies the `unlinked` filter
- **THEN** only unlinked restaurants must be shown

### Requirement: Restaurant form must provide an explicit merchant association workflow

The restaurant create and edit forms must present merchant association as a primary workflow.

#### Scenario: Unlinked restaurant shows CTA

- **GIVEN** the restaurant form has no merchant selected
- **WHEN** the merchant section is rendered
- **THEN** the UI must show a clear empty state
- **AND** the UI must include a CTA to link or create a merchant

#### Scenario: Linked merchant shows summary state

- **GIVEN** the restaurant form has a selected merchant
- **WHEN** the merchant section is rendered
- **THEN** the UI must show the merchant name
- **AND** the UI should show short name, category, and website when present
- **AND** the UI must provide actions to change or clear the merchant association

### Requirement: Merchant quick-add from restaurant form must support category

Users must be able to create a merchant from the restaurant form without leaving the workflow and without losing required merchant metadata.

#### Scenario: User creates merchant with category

- **GIVEN** the user opens the create-merchant flow from the restaurant form
- **WHEN** the user submits merchant name, optional short name, category, and optional website
- **THEN** a new merchant must be created with the provided category
- **AND** the new merchant must become the selected merchant in the form

#### Scenario: Duplicate merchant conflict returns existing merchant

- **GIVEN** a merchant already exists with a conflicting name or short name
- **WHEN** the user submits the create-merchant flow from the restaurant form
- **THEN** the response must preserve conflict handling behavior
- **AND** the client must be able to use the existing merchant as the selected merchant

### Requirement: Restaurant form must surface merchant suggestions

The restaurant form must proactively suggest a merchant when existing matching rules produce a strong match.

#### Scenario: Strong merchant match is suggested

- **GIVEN** the restaurant name strongly matches an existing merchant by the configured matching rules
- **WHEN** the restaurant form has no explicit merchant selected
- **THEN** the UI must show the suggested merchant
- **AND** the UI must provide a one-click action to accept the suggestion

#### Scenario: Explicit user selection wins over suggestion

- **GIVEN** a merchant suggestion is available
- **AND** the user explicitly selects a different merchant
- **WHEN** the form state updates
- **THEN** the explicit user selection must be preserved
- **AND** the suggestion must not overwrite the chosen merchant

### Requirement: Users must have a guided path to associate unlinked restaurants

The product must provide a clear call-to-action for associating unlinked restaurants with merchants.

#### Scenario: Restaurants list includes cleanup CTA

- **GIVEN** the user is viewing restaurants
- **WHEN** at least one unlinked restaurant exists
- **THEN** the page must show a CTA to review or associate unlinked restaurants

#### Scenario: Cleanup flow presents suggested matches

- **GIVEN** the user opens the unlinked restaurant cleanup flow
- **WHEN** unlinked restaurants have strong merchant matches
- **THEN** each restaurant should show its suggested merchant
- **AND** the UI should provide a quick action to accept the suggestion

#### Scenario: Cleanup flow allows lightweight bulk acceptance

- **GIVEN** multiple unlinked restaurants have unambiguous strong matches
- **WHEN** the user invokes a bulk accept action
- **THEN** the matching restaurants must be linked to their suggested merchants
- **AND** restaurants without unambiguous matches must remain unchanged
