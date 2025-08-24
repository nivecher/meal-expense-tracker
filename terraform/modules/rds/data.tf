# Get current AWS region and account info for IAM policies
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
