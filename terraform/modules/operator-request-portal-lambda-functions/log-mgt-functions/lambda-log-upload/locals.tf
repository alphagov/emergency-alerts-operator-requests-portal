locals {
  base_host     = "emergency-alerts.service.gov.uk"
  app_subdomain = "operator-requests"
  env_segment   = var.environment == "prod" ? "" : "${var.environment}."
  fqdn          = "${local.app_subdomain}.${local.env_segment}${local.base_host}"

  env_map = {
      "mno-portal-development" = "dev"
      "mno-portal-staging"     = "staging"
      "prod"                   = "prod"
    }
  short_env           = lookup(local.env_map, var.environment, "dev")
  upload_env_segment  = local.short_env == "prod" ? "" : "${local.short_env}."
  upload_domain       = "${local.app_subdomain}.${local.upload_env_segment}${local.base_host}"


  default_log_bucket_name = local.fqdn
  default_upload_domain   = local.upload_domain
}
