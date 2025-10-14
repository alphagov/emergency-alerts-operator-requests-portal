output "domain_name" {
  description = "The domain name of the deployed application"
  value       = local.domain_name
}

output "website_url" {
  description = "The full HTTPS URL to the website"
  value       = "https://${local.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.operator_request_portal_static_site.cloudfront_distribution_id
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN"
  value       = module.operator_request_portal_static_site.cloudfront_distribution_arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = module.operator_request_portal_static_site.cloudfront_domain_name
}

# Lambda function ARNs
output "notify_lambda_arn" {
  description = "Notify email communications Lambda ARN"
  value       = module.notify_email_communications.notify_lambda_function_arn
}

output "certificate_generation_lambda_arn" {
  description = "Certificate generation Lambda ARN"
  value       = module.lambda_certificate_generation.certificate_generation_lambda_arn
}

output "log_upload_lambda_arn" {
  description = "Log upload Lambda ARN"
  value       = module.lambda_log_upload.log_upload_lambda_arn
}

# DynamoDB tables
output "dynamodb_tables" {
  description = "Names of all DynamoDB tables"
  value = {
    certificates          = module.lambda_certificate_generation.certificates_table_name
    mno_config            = module.lambda_certificate_generation.mno_config_table_name
    mno_contacts          = module.lambda_certificate_generation.mno_contacts_table_name
    download_tracking     = module.lambda_log_download.download_tracking_table_name
    log_invite_tracking   = module.lambda_log_upload.log_invite_tracking_table_name
    log_upload_tracking   = module.lambda_edge_log_upload.log_upload_tracking_table_name
    csr_uploads           = module.lambda_edge_csr_upload.csr_uploads_table_name
  }
}