# IAM policy for RDS IAM authentication
resource "aws_iam_policy" "rds_iam_auth" {
  name        = "${var.app_name}-${var.environment}-rds-iam-auth"
  description = "Policy to allow IAM authentication to RDS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rds-db:connect"
        ]
        Resource = [
          "arn:aws:rds-db:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:dbuser:${aws_db_instance.main.resource_id}/*"
        ]
      }
    ]
  })
}

# Extract the role name from the ARN (the part after the last /)
locals {
  lambda_role_name = var.lambda_iam_role_arn != null ? element(split("/", var.lambda_iam_role_arn), length(split("/", var.lambda_iam_role_arn)) - 1) : ""
}

# Attach the RDS IAM auth policy to the Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_rds_iam_auth" {
  count      = var.lambda_iam_role_arn != null ? 1 : 0
  role       = local.lambda_role_name
  policy_arn = aws_iam_policy.rds_iam_auth.arn
}
