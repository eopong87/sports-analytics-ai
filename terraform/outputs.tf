output "api_gateway_url" {
  value = "https://${aws_apigatewayv2_api.api.id}.execute-api.${var.aws_region}.amazonaws.com"
}

output "cloudfront_url" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "s3_website_url" {
  value = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda_role.arn
}
