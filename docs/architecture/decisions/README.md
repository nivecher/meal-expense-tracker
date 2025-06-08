# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records (ADRs) for the Meal Expense Tracker project. These documents capture important architectural decisions made during the development of the project, including the context, options considered, and rationale behind each decision.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences. It serves as a historical record of why a particular approach was chosen.

## ADR Index

| ADR Number | Title | Status | Date |
|------------|-------|--------|------|
| [ADR-001](./0001-infrastructure-as-code.md) | Infrastructure as Code with Terraform | Accepted | 2024-06-08 |
| [ADR-002](./0002-ci-cd-pipeline.md) | CI/CD Pipeline with GitHub Actions | Accepted | 2024-06-08 |
| [ADR-003](./0003-aws-service-selection.md) | AWS Service Selection | Accepted | 2024-06-08 |
| [ADR-004](./0004-kms-encryption-strategy.md) | KMS Encryption Strategy | Accepted | 2024-06-08 |
| [ADR-005](./0005-container-orchestration.md) | Container Orchestration | Accepted | 2024-06-08 |

## How to Create a New ADR

1. Copy the template:
   ```bash
   cp 0000-template.md 000X-short-title.md
   ```
2. Edit the new file with your decision details
3. Update this README with the new ADR entry
4. Commit the changes with a descriptive message

## Template

A template for new ADRs is available at [0000-template.md](./0000-template.md).
