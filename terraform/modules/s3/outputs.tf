output "bucket_id" {
  description = "The ID of the receipts bucket"
  value       = aws_s3_bucket.receipts.id
}

output "bucket_arn" {
  description = "The ARN of the receipts bucket"
  value       = aws_s3_bucket.receipts.arn
}

output "bucket_name" {
  description = "The name of the receipts bucket"
  value       = aws_s3_bucket.receipts.id
}

output "bucket_domain_name" {
  description = "The domain name of the receipts bucket"
  value       = aws_s3_bucket.receipts.bucket_domain_name
}

output "bucket_regional_domain_name" {
  description = "The regional domain name of the receipts bucket"
  value       = aws_s3_bucket.receipts.bucket_regional_domain_name
}

output "logs_bucket_id" {
  description = "The ID of the logs bucket (if access logging is enabled)"
  value       = try(aws_s3_bucket.logs[0].id, "")
}

output "logs_bucket_arn" {
  description = "The ARN of the logs bucket (if access logging is enabled)"
  value       = try(aws_s3_bucket.logs[0].arn, "")
}
