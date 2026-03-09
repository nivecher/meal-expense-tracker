## ADDED Requirements

### Requirement: Expense import must support Quicken Simplifi export formats

The expense import pipeline must accept Quicken Simplifi CSV exports without requiring manual column renaming.

#### Scenario: Simplifi headers are normalized

- **GIVEN** a CSV row with headers such as `Date`, `Payee`, `Category`, `Amount`, `Tags`, `Notes`, and `Exclusion`
- **WHEN** the file is parsed for import
- **THEN** the importer must map the supported fields to the internal import schema
- **AND** unsupported fields may be ignored without failing the row

#### Scenario: Simplifi short month dates are accepted

- **GIVEN** a CSV row with a date value such as `7-Mar-26`
- **WHEN** the importer parses the row
- **THEN** the row date must be accepted as a valid import date

#### Scenario: Exclusion column is ignored

- **GIVEN** a CSV row includes an `Exclusion` value of `yes` or `no`
- **WHEN** the importer parses the row
- **THEN** the row must remain eligible for review and import
- **AND** the `Exclusion` value must not automatically skip the row

### Requirement: Duplicate candidates must be identified using bank-import tolerant rules

The import review flow must identify likely duplicates using rules that match bank-export behavior instead of requiring exact same-day or exact-name equality.

#### Scenario: Absolute amount and nearby date produce a duplicate candidate

- **GIVEN** an existing expense and an import row with the same absolute amount
- **AND** the import row date is within three calendar days of the existing expense date
- **AND** the payee matches the restaurant name or display name by the configured import matching rules
- **WHEN** the review rows are generated
- **THEN** the row must show the existing expense as a duplicate candidate

#### Scenario: Exact amount mismatch prevents duplicate candidate

- **GIVEN** an existing expense with a different absolute amount from the import row
- **WHEN** duplicate candidates are evaluated
- **THEN** that expense must not be considered a duplicate candidate even if the payee and date are close

#### Scenario: Multiple duplicate candidates remain user-reviewable

- **GIVEN** an import row matches multiple existing expenses within the allowed date window
- **WHEN** the review row is rendered
- **THEN** the user must be shown the candidate duplicates
- **AND** the row must not be auto-imported without an explicit user decision

### Requirement: Review rows must support explicit restaurant resolution

Users must be able to control restaurant matching on each row before expenses are created.

#### Scenario: User accepts suggested restaurant match

- **GIVEN** an import row has a suggested restaurant match
- **WHEN** the user accepts that suggestion
- **THEN** the row must import against the selected existing restaurant

#### Scenario: User creates a new restaurant from a review row

- **GIVEN** an import row does not have a suitable existing restaurant
- **WHEN** the user chooses to create a new restaurant from the review UI
- **THEN** the new restaurant must be associated with that row
- **AND** the row must remain reviewable before final import submission

#### Scenario: User overrides suggested restaurant

- **GIVEN** the system suggests an existing restaurant for a row
- **WHEN** the user selects a different restaurant manually
- **THEN** the explicit user selection must be preserved
- **AND** subsequent suggestion recalculation must not overwrite it

### Requirement: Review rows must support explicit skip behavior

Users must be able to skip individual rows during import review.

#### Scenario: User skips a row

- **GIVEN** a parsed review row
- **WHEN** the user marks the row as skipped
- **THEN** that row must not create an expense
- **AND** the remaining reviewed rows must remain eligible for submission

#### Scenario: Skipped rows appear in review summary

- **GIVEN** one or more rows were skipped during review
- **WHEN** the user views the review summary before import
- **THEN** the summary must include a skipped-row count

### Requirement: Review UI must surface guidance for row decisions

The product must explain how Simplifi review decisions work in the import display and help surfaces.

#### Scenario: Import page explains review workflow

- **GIVEN** the user opens the expense import page
- **WHEN** the page is rendered
- **THEN** the page must describe that Simplifi imports are intended to go through a row-by-row review flow
- **AND** the page must explain the available actions to match, create, or skip

#### Scenario: Help page explains duplicate candidate rules

- **GIVEN** the user views the Help page
- **WHEN** the import guidance is displayed
- **THEN** the Help content must describe the duplicate-candidate rules at a high level
- **AND** the content must explain that exact absolute amount matters and dates may differ by up to three days
