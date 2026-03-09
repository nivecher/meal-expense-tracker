# Expense Import Review Plan

The maintained design record for the upcoming guided expense import workflow lives in OpenSpec:

- [openspec/changes/guided-simplifi-expense-import/proposal.md](/home/mtd37/workspace/meal-expense-tracker/openspec/changes/guided-simplifi-expense-import/proposal.md)
- [openspec/changes/guided-simplifi-expense-import/tasks.md](/home/mtd37/workspace/meal-expense-tracker/openspec/changes/guided-simplifi-expense-import/tasks.md)
- [openspec/changes/guided-simplifi-expense-import/specs/expense-import-review/spec.md](/home/mtd37/workspace/meal-expense-tracker/openspec/changes/guided-simplifi-expense-import/specs/expense-import-review/spec.md)

## Scope

This change is intended to make Quicken Simplifi imports workable without sacrificing data quality.

Planned behavior:

- parse Simplifi CSV exports directly
- ignore the `Exclusion` column for import eligibility
- identify duplicate candidates using exact absolute amount plus a one-to-three-day date window
- compare Simplifi payees against restaurant names and display names
- require explicit row decisions for ambiguous matches
- allow per-row actions to match an existing restaurant, create a new restaurant, or skip

## Product Surfaces

The planned workflow affects:

- the expense import screen
- the Help page
- expense import routes and services
- any review UI introduced for per-row import decisions

## Status

This document is informational. OpenSpec is the source of truth for requirements and tasks until the feature is implemented.
