## 1. Simplifi Parsing and Normalization

- [ ] Add Simplifi header normalization coverage for canonical and alias field names.
- [ ] Add support for Simplifi date formats such as `7-Mar-26`.
- [ ] Parse Simplifi payee, category, notes, and tags formats without treating `Exclusion` as a skip signal.
- [ ] Add regression tests for Simplifi sample rows.

## 2. Duplicate Candidate Logic

- [ ] Add duplicate-candidate matching by absolute amount equality.
- [ ] Add visit-date tolerance matching for dates within one to three days.
- [ ] Add payee-to-restaurant matching against restaurant name and display name.
- [ ] Add tests for same-restaurant duplicates where Simplifi payee text differs from stored restaurant text.

## 3. Guided Review Workflow

- [ ] Add a pre-import review route or step that produces row-by-row decisions before commit.
- [ ] Show suggested restaurant, duplicate candidate, and category details for each row.
- [ ] Support row actions for `match existing restaurant`, `create restaurant`, and `skip`.
- [ ] Support bulk import submit after review without losing row-level choices.

## 4. Restaurant Resolution UX

- [ ] Reuse the merchant-association interaction patterns where practical for import review.
- [ ] Add explicit restaurant search/change controls in the review UI.
- [ ] Add explicit create-restaurant controls from a review row.
- [ ] Ensure explicit user selections override future suggestion recalculation.

## 5. Documentation

- [ ] Update the expense import page copy to describe the planned guided review flow.
- [ ] Update the Help page with Simplifi import and duplicate-review guidance.
- [ ] Add repo documentation that points to this OpenSpec change as the maintained source of truth.

## 6. Testing

- [ ] Add service tests for Simplifi parsing and duplicate candidate generation.
- [ ] Add route tests for review-step rendering and row decision submission.
- [ ] Add UI behavior tests for skip, match, and create decisions.
- [ ] Add regression coverage for ignored `Exclusion` values and absolute-value amount matching.
