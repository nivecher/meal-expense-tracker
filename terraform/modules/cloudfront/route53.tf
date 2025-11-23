# Route53 record for CloudFront distribution
# This overwrites the API Gateway Route53 record

resource "aws_route53_record" "cloudfront" {
  count = length(var.domain_aliases) > 0 && var.route53_zone_id != "" ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.domain_aliases[0]
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }

  allow_overwrite = true

  lifecycle {
    create_before_destroy = true
    # Note: Removed ignore_changes to allow updates when CloudFront distribution changes
  }
}
