# ADR 0003: AWS Service Selection

- Status: Accepted
- Deciders: Engineering Team
- Date: 2024-06-08

## Context and Problem Statement

We needed to select appropriate AWS services for our application's backend infrastructure, considering factors like
scalability, cost, maintenance overhead, and team expertise.

## Decision Drivers

- **Scalability**: Handle variable loads
- **Cost-effectiveness**: Minimize operational costs
- **Maintainability**: Reduce operational overhead
- **Security**: Ensure data protection and compliance
- **Performance**: Meet application response time requirements

## Considered Options

For each component, we considered the following options:

1. **Compute**:

- AWS Lambda
  - Amazon ECS
  - Amazon EC2
  - AWS App Runner

1. **Database**:

- Amazon RDS (PostgreSQL) **[SELECTED]**
  - Amazon DynamoDB **[REJECTED - not suitable for relational data]**
  - Amazon Aurora **[REJECTED - unnecessary complexity for this use case]**
  - Self-managed PostgreSQL on EC2 **[REJECTED - operational complexity]**

1. **API Gateway**:

- Amazon API Gateway (HTTP API)
  - Amazon API Gateway (REST API)
  - Application Load Balancer
  - Self-maned API server

1. **Storage**:

- Amazon S3
  - Amazon EBS
  - Amazon EFS

## Decision Outcome

### Compute: AWS Lambda

- **Why**: Serverless architecture for cost efficiency and automatic scaling
- **Details**:
  - Pay-per-use pricing model
  - Automatic scaling to zero when not in use
  - Integrated with API Gateway

### Database: Amazon RDS (PostgreSQL)

- **Why**: Managed relational database with PostgreSQL compatibility
- **Details**:
  - Managed backups and updates
  - Multi-AZ deployment for high availability
  - Point-in-time recovery

### API: Amazon API Gateway (HTTP API)

- **Why**: Lightweight, low-latency API layer
- **Details**:
  - Lower cost than REST API
  - Built-in JWT authorizer
  - Automatic scaling

### Storage: Amazon S3

- **Why**: Highly durable object storage
- **Details**:
  - Versioning support
  - Lifecycle policies for cost optimization
  - Fine-grained access control

## Positive Consequences

- **Reduced operational overhead**: Managed services reduce maintenance
- **Scalability**: Automatic scaling based on demand
- **Cost-effective**: Pay only for what we use
- **High availability**: Built-in redundancy and failover

## Negative Consequences

- **Vendor lock-in**: AWS-specific implementations
- **Cold starts**: Lambda functions may have initial latency
- **Learning curve**: Team needs to learn multiple AWS services

## Alternative Analysis

### Compute Alternatives

**Amazon ECS**

- ✅ More control over runtime environment
- ❌ Higher operational overhead
- ❌ More expensive for variable workloads

**Amazon EC2**

- ✅ Full control
- ❌ Requires manual scaling
- ❌ Higher maintenance

### Database Alternatives

**Aurora**

- ✅ High performance
- ❌ Higher cost
- ❌ Overkill for current needs

## Links

- [AWS Lambda](https://aws.amazon.com/lambda/)
- [Amazon RDS](https://aws.amazon.com/rds/)
- [API Gateway](https://aws.amazon.com/api-gateway/)
