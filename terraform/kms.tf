# Primary KMS key for encrypting resources
resource "aws_kms_key" "primary_encryption_key" {
  description             = "KMS key for ${var.app_name} ${var.environment} environment"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow use of the key by AWS services"
        Effect = "Allow"
        Principal = {
          Service = [
            "logs.amazonaws.com",
            "lambda.amazonaws.com",
            "rds.amazonaws.com",
            "secretsmanager.amazonaws.com",
            "sns.amazonaws.com",
            "ecr.amazonaws.com",
            "events.amazonaws.com"
          ]
        },
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:ListGrants",
          "kms:DescribeKey"
        ],
        Resource = "*"
      },
      {
        Sid    = "Allow attachment of persistent resources"
        Effect = "Allow"
        Principal = {
          Service = [
            "logs.amazonaws.com",
            "lambda.amazonaws.com",
            "rds.amazonaws.com",
            "secretsmanager.amazonaws.com"
          ]
        },
        Action = [
          "kms:CreateGrant"
        ],
        Resource = "*",
        Condition = {
          StringLike = {
            "kms:ViaService" = [
              "logs.${var.aws_region}.amazonaws.com",
              "lambda.${var.aws_region}.amazonaws.com",
              "rds.${var.aws_region}.amazonaws.com",
              "secretsmanager.${var.aws_region}.amazonaws.com"
            ]
          }
        }
      }
    ]
  })

  tags = merge(
    {
      Name        = "${var.app_name}-primary-encryption-key"
      Environment = var.environment
    },
    var.tags
  )
}

resource "aws_kms_alias" "primary_encryption_alias" {
  name          = "alias/${var.app_name}-primary-encryption-key"
  target_key_id = aws_kms_key.primary_encryption_key.key_id
}
