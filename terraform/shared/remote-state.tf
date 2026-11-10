data "terraform_remote_state" "infra_mgt" {
  backend = "s3"

  config = {
    bucket = var.infra_mgt_state_bucket
    key    = var.infra_mgt_state_key
    region = var.infra_mgt_state_region
  }
}

locals {
  hosted_zone_id = data.terraform_remote_state.infra_mgt.outputs.operator_portal_hosted_zone_id
  domain_name    = data.terraform_remote_state.infra_mgt.outputs.operator_portal_domain_name

  notify_api_key_parameter_name = var.notify_api_key_parameter_name
  notify_api_key_parameter_arn  = var.notify_api_key_parameter_arn

  notify_templates   = data.terraform_remote_state.infra_mgt.outputs.notify_template_ids
  alerts_team_emails = data.terraform_remote_state.infra_mgt.outputs.alerts_team_emails
}