data "terraform_remote_state" "infra_mgt" {
  backend = "s3"

  config = {
    bucket  = var.infra_mgt_state_bucket
    key     = var.infra_mgt_state_key
    region  = var.infra_mgt_state_region
  }
}

locals {
  state_bucket          = data.terraform_remote_state.infra_mgt.outputs.terraform_state_bucket
  state_region          = data.terraform_remote_state.infra_mgt.outputs.terraform_state_region
  deploy_role_arn       = data.terraform_remote_state.infra_mgt.outputs.operator_portal_deploy_role_arn
  state_reader_role_arn = data.terraform_remote_state.infra_mgt.outputs.infra_mgt_state_reader_role_arn

  aws_account_id = data.terraform_remote_state.infra_mgt.outputs.aws_account_id
  aws_region     = data.terraform_remote_state.infra_mgt.outputs.aws_region

  hosted_zone_id = data.terraform_remote_state.infra_mgt.outputs.operator_portal_hosted_zone_id
  domain_name    = data.terraform_remote_state.infra_mgt.outputs.operator_portal_domain_name

  notify_api_key_parameter_name = data.terraform_remote_state.infra_mgt.outputs.notify_api_key_parameter_name
  notify_api_key_parameter_arn  = data.terraform_remote_state.infra_mgt.outputs.notify_api_key_parameter_arn

  pca_arn = data.terraform_remote_state.infra_mgt.outputs.pca_arn

  notify_templates    = data.terraform_remote_state.infra_mgt.outputs.notify_template_ids
  alerts_team_emails  = data.terraform_remote_state.infra_mgt.outputs.alerts_team_emails
}