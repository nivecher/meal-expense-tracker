# ECR Repository
resource "aws_ecr_repository" "main" {
  name                 = var.repository_name
  image_tag_mutability = var.image_tag_mutability
  force_delete         = var.force_delete

  # Enable encryption using KMS
  encryption_configuration {
    encryption_type = var.kms_key_arn == null ? "AES256" : "KMS"
    kms_key         = var.kms_key_arn
  }

  # Enable image scanning on push
  image_scanning_configuration {
    scan_on_push = true # Always enable scanning for security
  }

  tags = merge({
    Name        = var.repository_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = var.repository_name
  }, var.tags)

  # Prevent replace/destroy when encryption differs from state (e.g. after import or provider change)
  lifecycle {
    ignore_changes = [encryption_configuration]
  }
}
