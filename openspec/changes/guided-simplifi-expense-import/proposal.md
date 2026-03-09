## Why

Importing meal expenses from Quicken Simplifi currently breaks down in the cases users care about most:

- Simplifi exports use bank-style payee names instead of the visit-date restaurant records already stored in the app.
- The Simplifi transaction date is often one to three days after the actual restaurant visit date.
- Duplicate detection needs exact amount matching by absolute value, but cannot rely on exact same-day or exact same-string restaurant names.
- Users need control over ambiguous rows instead of an all-or-nothing importer.

The current importer is optimized for direct restore-style CSV imports. It does not provide a guided review flow where users can decide, row by row, whether a row should match an existing restaurant, create a new restaurant, or be skipped.

This creates failed imports, duplicate restaurants, and low user trust when importing financial exports.

## What Changes

This change adds a guided expense import review flow focused on Quicken Simplifi exports while remaining usable for other CSV imports.

### 1. Simplifi-aware import normalization

- Support Simplifi header names and date formats such as `7-Mar-26`.
- Treat the Simplifi `Exclusion` column as informational only and ignore it during import review.
- Normalize payee names for matching without rewriting stored restaurant names automatically.

### 2. Candidate duplicate detection

- Evaluate duplicate candidates using:
  - exact amount match by absolute value
  - restaurant/payee name match against restaurant name or display name
  - visit date tolerance window of up to three days between the import row and existing expense
- Surface duplicate candidates to the user during review instead of silently skipping ambiguous rows.

### 3. Row-by-row review workflow

- Parse the uploaded file into review rows before final import.
- For each row, show:
  - imported source values
  - suggested restaurant match
  - suggested duplicate candidate, if any
  - suggested category mapping
- Allow the user to choose, per row:
  - import and match to an existing restaurant
  - import and create a new restaurant
  - skip the row

### 4. Explicit restaurant resolution controls

- Model the review interaction after the merchant association experience:
  - visible suggested match state
  - explicit change/select controls
  - explicit create-new flow
  - visible skip action
- Preserve user choice when the system suggestion changes or new matches are recomputed.

### 5. Documentation and guidance

- Update the import screen copy to describe the guided review workflow and Simplifi-specific expectations.
- Update the Help page with guidance for review decisions and duplicate interpretation.
- Add repo documentation pointing to the OpenSpec change as the maintained design record.

## Impact

Expected user-facing outcomes:

- Simplifi exports can be reviewed instead of failing immediately.
- Duplicate handling becomes transparent and user-controlled.
- Restaurant data quality improves because matching and creation are explicit choices.
- Users can safely skip rows they do not want to import.

Expected implementation areas:

- expense import parsing and normalization
- expense duplicate-candidate matching logic
- import review routes, templates, and client-side behavior
- restaurant selection/create flows used during import review
- tests for parsing, duplicate candidate generation, and row decision flows
