# Route53 record for CloudFront distribution
# Creates A record pointing to CloudFront distribution
resource "aws_route53_record" "cloudfront" {
  for_each = toset(var.aliases)

  zone_id = var.route53_zone_id
  name    = each.value
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }

  allow_overwrite = true

  lifecycle {
    create_before_destroy = true
  }
}
