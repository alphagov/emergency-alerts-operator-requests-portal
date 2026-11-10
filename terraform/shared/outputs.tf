output "hosted_zone_id" {
  description = "Route53 hosted zone ID"
  value       = local.hosted_zone_id
}

output "domain_name" {
  description = "Domain name for the application"
  value       = local.domain_name
}

output "notify_api_key_parameter_name" {
  description = "SSM parameter name for Notify API key"
  value       = local.notify_api_key_parameter_name
}

output "notify_api_key_parameter_arn" {
  description = "SSM parameter ARN for Notify API key"
  value       = local.notify_api_key_parameter_arn
}

output "notify_templates" {
  description = "GOV.UK Notify template IDs"
  value       = local.notify_templates
}

output "alerts_team_emails" {
  description = "Emergency Alerts team email addresses"
  value       = local.alerts_team_emails
  sensitive   = true
}
