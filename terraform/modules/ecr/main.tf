# ECR Repository
resource "aws_ecr_repository" "main" {
  name                 = var.repository_name
  image_tag_mutability = var.image_tag_mutability
  force_delete         = var.force_delete

  # Enable encryption using KMS
  encryption_configuration {
    encryption_type = "KMS"
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
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "main" {
  repository = aws_ecr_repository.main.name
  policy = jsonencode({
    rules = [
      # Rule 1: Keep last N images
      {
        rulePriority = 1
        description  = "Keep last ${var.max_image_count} images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.max_image_count
        }
        action = {
          type = "expire"
        }
      },
      # Rule 2: Remove untagged images after 1 day
      {
        rulePriority = 2
        description  = "Remove untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      # Rule 3: Keep production images longer (if this is a production environment)
      var.environment == "prod" ? {
        rulePriority = 3
        description  = "Keep production images for 30 days regardless of count"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["prod", "production", "latest"]
          countType     = "sinceImagePushed"
          countUnit     = "days"
          countNumber   = 30
        }
        action = {
          type = "expire"
        }
      } : null
    ]
  })


  depends_on = [aws_ecr_repository.main]
}
