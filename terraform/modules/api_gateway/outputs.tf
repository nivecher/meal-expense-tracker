output "api_id" {
  description = "The ID of the API Gateway"
  value       = aws_apigatewayv2_api.main.id
}

output "api_endpoint" {
  description = "The URI of the API"
  value       = aws_apigatewayv2_stage.main.invoke_url
}

output "api_execution_arn" {
  description = "The ARN of the API Gateway execution"
  value       = aws_apigatewayv2_api.main.execution_arn
}

output "api_stage_arn" {
  description = "The ARN of the API Gateway stage"
  value       = "${aws_apigatewayv2_api.main.execution_arn}/*"
}

output "domain_name" {
  description = "The domain name of the API Gateway"
  value       = length(aws_apigatewayv2_domain_name.main) > 0 ? local.effective_api_domain_name : null
}

output "domain_zone_id" {
  description = "The hosted zone ID of the API Gateway domain name"
  value       = length(aws_apigatewayv2_domain_name.main) > 0 ? one(aws_apigatewayv2_domain_name.main[*].domain_name_configuration[0].hosted_zone_id) : null
}

output "domain_target_domain_name" {
  description = "The target domain name of the API Gateway domain name"
  value       = length(aws_apigatewayv2_domain_name.main) > 0 ? one(aws_apigatewayv2_domain_name.main[*].domain_name_configuration[0].target_domain_name) : null
}

output "effective_api_domain_name" {
  description = "The effective API domain name (constructed or provided)"
  value       = local.effective_api_domain_name
}
