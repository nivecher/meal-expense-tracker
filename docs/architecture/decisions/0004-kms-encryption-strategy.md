# ADR 0004: KMS Encryption Strategy

- Status: Accepted
- Deciders: Engineering Team, Security Team
- Date: 2024-06-08

## Context and Problem Statement

<!-- markdownlint-disable MD044 -->

We needed to implement encryption at rest for sensitive data in our AWS infrastructure. After initial implementation
with optional KMS encryption, we decided to simplify the approach by always using KMS encryption for all environments to
ensure consistent security posture and reduce configuration complexity.

## Decision Drivers

- **Security**: Strong encryption for all sensitive data across all environments
- **Compliance**: Meet regulatory requirements consistently
- **Simplicity**: Reduce configuration complexity and potential for misconfiguration
- **Operational Overhead**: Streamline key management and monitoring
- **Consistency**: Ensure uniform security controls across all environments

## Considered Options

1. **Always Use AWS KMS Customer Managed Keys (CMK)**

- Create and manage our own encryption keys for all environments
  - Consistent security controls across all environments
  - Simplified configuration and maintenance

1. **AWS KMS AWS Managed Keys**

- Use AWS-managed keys
  - Simpler management but less control
  - Limited customization options

1. **Configurable KMS (Previous Approach)**

- Optional KMS encryption via feature flag
  - More complex configuration
  - Risk of inconsistent security controls

## Decision Outcome

Chosen option: **Always Use AWS KMS Customer Managed Keys (CMK)**

### Implementation Details

1. **KMS Key Management**:

- Single Customer Managed Key (CMK) for all encryption needs
  - Automatic key rotation enabled (30 days)
  - Granular key policies following principle of least privilege
  - No conditional logic for key creation or usage

1. **Service Integration**:

<!-- markdownlint-disable MD044 -->

- **RDS**: Encryption at rest using KMS CMK
  - **S3**: Server-side encryption with KMS (SSE-KMS)
  - **CloudWatch Logs**: KMS encryption for all log groups
  - **Lambda Environment Variables**: Encrypted using KMS
  - **Secrets Manager**: Automatic KMS encryption
  - **SNS Topics**: KMS encryption for all topics
  - **ECR Repositories**: KMS encryption for container images

1. **Configuration**:

- Removed `enable_kms_encryption` variable
  - Simplified IAM policies and key references
  - Consistent security posture across all environments

### Positive Consequences

- **Simplified Configuration**: No conditional logic for KMS key usage
- **Consistent Security**: Uniform encryption across all environments
- **Reduced Risk**: Eliminates possibility of accidentally disabling encryption
- **Easier Auditing**: Clear, consistent encryption patterns
- **Simplified Compliance**: Easier to demonstrate consistent security controls

### Negative Consequences

- **Increased Cost**: KMS usage costs for all environments
- **Less Flexibility**: Cannot disable encryption for non-sensitive environments
- **Migration Required**: Existing resources may need re-encryption

## Alternative Analysis

### AWS KMS Customer Managed Keys (CMK)

- ✅ Full control over keys
- ✅ Custom key policies
- ❌ Higher operational overhead
- ❌ Additional cost

### AWS KMS AWS Managed Keys

- ✅ No key management required
- ✅ Lower operational overhead
- ❌ Limited customization
- ❌ Less control over key policies

### No Encryption

- ✅ No additional cost
- ✅ Simplest to implement
- ❌ Security and compliance risks
- ❌ Not acceptable for sensitive data

## Security Considerations

1. **Key Rotation**:

- Automatic yearly rotation
  - Previous key versions retained for data decryption

1. **Access Control**:

- Least privilege IAM policies
  - Key policies restrict access to authorized roles
  - Cross-account access explicitly denied

1. **Monitoring**:

- CloudTrail logging for all KMS operations
  - CloudWatch Alerts for suspicious activity
  - Regular access reviews

## Links

- [AWS KMS Documentation](https://docs.aws.amazon.com/kms/)
- [AWS KMS Best Practices](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html)
- [Terraform AWS KMS Resources](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key)
