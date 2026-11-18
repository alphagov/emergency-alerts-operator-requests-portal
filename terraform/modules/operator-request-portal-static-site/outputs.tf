output "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.cdn.id
}

output "cloudfront_domain_name" {
  description = "The CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.cdn.domain_name
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket"
  value       = aws_s3_bucket.static_site.id
}

output "website_url" {
  description = "The website URL"
  value       = "https://${var.domain_name}"
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN"
  value       = aws_cloudfront_distribution.cdn.arn
}


output "logs_bucket_name" {
  description = "The name of the private bucket holding uploaded logs"
  value       = aws_s3_bucket.logs.id
}

output "logs_kms_key_arn" {
  description = "ARN of the KMS key encrypting uploaded logs"
  value       = aws_kms_key.logs.arn
}
