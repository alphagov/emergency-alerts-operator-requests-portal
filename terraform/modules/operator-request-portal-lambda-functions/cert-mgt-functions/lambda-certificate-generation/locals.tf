locals {
  base_host     = "emergency-alerts.service.gov.uk"
  app_subdomain = "operator-requests"
  env_segment   = var.environment == "prod" ? "" : "${var.environment}."
  fqdn          = "${local.app_subdomain}.${local.env_segment}${local.base_host}"

  certificate_domain = local.fqdn
}
