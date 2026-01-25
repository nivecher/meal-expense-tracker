# Terraform Dependency Order and Architecture

## Overview

This document explains the dependency relationships between Terraform modules and how circular dependencies are avoided in the infrastructure configuration.

## Module Dependency Graph

```
┌─────────────┐
│   KMS Key   │
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│     S3      │   │     IAM     │
└──────┬──────┘   └──────┬──────┘
       │                 │
       │                 │
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│   Lambda    │   │     SNS     │
└──────┬──────┘   └──────┬──────┘
       │                 │
       │                 │
       ├─────────────────┤
       │                 │
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│ API Gateway │   │  CloudFront  │
└─────────────┘   └──────────────┘
```

## Critical Dependencies

### Lambda ↔ API Gateway Circular Dependency

**The Problem:**

- API Gateway needs Lambda's `invoke_arn` to create the integration
- Lambda wants API Gateway's `domain_name` and `execution_arn` for environment variables

**The Solution:**

1. **Domain Name**: Computed independently in `locals.tf` using the same logic as API Gateway module

   - Lambda uses: `local.api_gateway_domain_name = "${local.api_domain_prefix}.${local.domain_name}"`
   - API Gateway computes: `"${var.api_domain_prefix}.${var.domain_name}"`
   - Both use the same inputs, so they match without creating a dependency

2. **Execution ARN**: Omitted from Lambda module call
   - The `api_gateway_execution_arn` variable exists but is not used in the Lambda module
   - It defaults to empty string, which is acceptable
   - This breaks the circular dependency

**Implementation:**

```hcl
# In terraform/main.tf - Lambda module
module "lambda" {
  # ... other config ...

  # Domain name computed independently to avoid circular dependency
  api_gateway_domain_name = local.api_gateway_domain_name

  # Execution ARN omitted - not used in Lambda module, defaults to ""
  # api_gateway_execution_arn = ""  # Not needed
}

# In terraform/main.tf - API Gateway module
module "api_gateway" {
  # ... other config ...

  # API Gateway depends on Lambda for integration
  lambda_invoke_arn    = module.lambda.invoke_arn
  lambda_function_name = module.lambda.name
}
```

## Resource Creation Order

1. **Foundation Resources** (no dependencies)

   - KMS Key
   - Route53 Zone (data source)
   - ACM Certificate (data source)

2. **Supporting Resources**

   - S3 Buckets (depends on KMS)
   - IAM Roles and Policies (depends on KMS)
   - SNS Topics (depends on KMS)

3. **Lambda Function**

   - Depends on: IAM roles, S3, SNS
   - Provides: `invoke_arn`, `function_name`
   - Uses: `local.api_gateway_domain_name` (computed, not from API Gateway module)

4. **API Gateway**

   - Depends on: Lambda (for `invoke_arn`)
   - Provides: `api_execution_arn`, `domain_name` (not used by Lambda)
   - Creates: Custom domain, routes, integrations

5. **CloudFront**
   - Depends on: API Gateway, S3, ACM Certificate
   - Uses: API Gateway custom domain for origin

## Key Design Decisions

### Why Compute Domain Name Locally?

The API Gateway domain name is computed in `locals.tf` rather than referencing the API Gateway module output to avoid circular dependencies:

```hcl
# terraform/locals.tf
locals {
  api_gateway_domain_name = "${local.api_domain_prefix}.${local.domain_name}"
}
```

This ensures:

- Lambda can be created without waiting for API Gateway
- Domain name matches what API Gateway will create (same computation)
- No circular dependency cycle

### Why Omit Execution ARN?

The `api_gateway_execution_arn` variable in the Lambda module is defined but never used in the module's code. It's safe to omit because:

- It defaults to empty string
- Lambda functions correctly without it
- It's only for environment variables (optional)

## Troubleshooting

### Circular Dependency Error

If you see an error like:

```
Error: Cycle: module.api_gateway... module.lambda...
```

**Check:**

1. Lambda module should NOT reference `module.api_gateway` outputs directly
2. Use `local.api_gateway_domain_name` instead of `module.api_gateway.domain_name`
3. Omit `api_gateway_execution_arn` from Lambda module call

### Domain Name Mismatch

If Lambda and API Gateway have different domain names:

**Check:**

1. Both use the same `api_domain_prefix` value
2. Both use the same `domain_name` value
3. Verify `local.api_gateway_domain_name` matches API Gateway's computed domain

## Best Practices

1. **Avoid Circular Dependencies**: Never have module A depend on module B's output while module B depends on module A's output
2. **Use Locals for Shared Computations**: When multiple modules need the same computed value, compute it in `locals.tf`
3. **Document Dependencies**: Use `depends_on` explicitly when order matters
4. **Test Dependency Changes**: After modifying dependencies, run `terraform plan` to verify no cycles

## Related Documentation

- [Terraform README](./README.md) - General Terraform usage
- [Architecture Documentation](../../docs/ARCHITECTURE.md) - High-level system architecture
- [Backend Architecture](../../docs/backend-architecture.md) - Backend design details
