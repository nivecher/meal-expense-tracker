# SNS Topic for Lambda Dead Letter Queue
resource "aws_sns_topic" "lambda_dlq" {
  name              = "${var.app_name}-${var.environment}-lambda-dlq"
  kms_master_key_id = aws_kms_key.main.arn

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-lambda-dlq"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Allow Lambda service to publish to the DLQ
resource "aws_sns_topic_policy" "lambda_dlq_policy" {
  arn    = aws_sns_topic.lambda_dlq.arn
  policy = data.aws_iam_policy_document.lambda_dlq_policy.json
}

data "aws_iam_policy_document" "lambda_dlq_policy" {
  statement {
    effect  = "Allow"
    actions = ["SNS:Publish"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }


    resources = [aws_sns_topic.lambda_dlq.arn]
  }
}
