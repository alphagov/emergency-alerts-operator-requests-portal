locals {
  base_host     = "emergency-alerts.service.gov.uk"
  app_subdomain = "operator-requests"
  env_segment   = var.environment == "prod" ? "" : "${var.environment}."
  fqdn          = "${local.app_subdomain}.${local.env_segment}${local.base_host}"

  default_log_bucket_name = local.fqdn
  default_upload_domain   = local.fqdn
}
