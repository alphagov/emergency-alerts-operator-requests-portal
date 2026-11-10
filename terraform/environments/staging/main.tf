module "shared" {
  source = "../../shared"

  environment                = var.environment
  project_name               = var.project_name
  infra_mgt_state_bucket     = var.infra_mgt_state_bucket
  infra_mgt_state_key        = var.infra_mgt_state_key
  infra_mgt_state_region     = var.infra_mgt_state_region
  upload_link_expiry_seconds = var.upload_link_expiry_seconds
  tags                       = var.tags

  notify_api_key_parameter_name = aws_ssm_parameter.notify_api_key.name
  notify_api_key_parameter_arn  = aws_ssm_parameter.notify_api_key.arn
}

locals {
  hosted_zone_id           = module.shared.hosted_zone_id
  domain_name              = module.shared.domain_name
  notify_api_key_parameter = module.shared.notify_api_key_parameter_name
  notify_templates         = module.shared.notify_templates
  alerts_team_emails       = module.shared.alerts_team_emails

  environment  = var.environment
  project_name = var.project_name
  aws_region   = var.aws_region

  download_tracking_table = "${var.project_name}-download-tracking"
}

# Notify email communications service
module "notify_email_communications" {
  source = "../../modules/operator-request-portal-lambda-functions/notify-email-communications"

  notify_api_key_parameter = local.notify_api_key_parameter
  environment              = local.environment
}

# Log download Lambda
module "lambda_log_download" {
  source = "../../modules/operator-request-portal-lambda-functions/log-mgt-functions/lambda-log-download"

  environment = local.environment
  # CloudFront's upload cache behaviors target the static-site bucket as their origin
  # (see cloudfront.tf), so uploaded CBC logs land there. This must point at that
  # bucket, both for S3 read access and for the S3->Lambda invoke permission to match
  # the real bucket notification.
  log_bucket                = module.operator_request_portal_static_site.s3_bucket_name
  gds_aws_profile           = var.gds_aws_profile
  notify_lambda_arn         = module.notify_email_communications.notify_lambda_function_arn
  notify_template_id        = local.notify_templates.log_download
  alerts_team_emails        = "alec.ashmore@digital.cabinet-office.gov.uk"
  log_invite_tracking_table = module.lambda_log_upload.log_invite_tracking_table_name
}

# Log upload Lambda
module "lambda_log_upload" {
  source = "../../modules/operator-request-portal-lambda-functions/log-mgt-functions/lambda-log-upload"

  environment                = local.environment
  upload_domain              = local.domain_name
  notify_lambda_arn          = module.notify_email_communications.notify_lambda_function_arn
  notify_log_template_id     = local.notify_templates.log_upload_invite
  upload_link_expiry_seconds = var.upload_link_expiry_seconds
}

# Lambda@Edge for log download
module "lambda_edge_log_download" {
  source = "../../modules/operator-request-portal-lambda-functions/log-mgt-functions/lambda@edge-log-download"

  environment                 = local.environment
  download_tracking_table     = local.download_tracking_table
  dynamodb_region             = local.aws_region
  cloudfront_distribution_arn = module.operator_request_portal_static_site.cloudfront_distribution_arn
  cloudfront_distribution_id  = module.operator_request_portal_static_site.cloudfront_distribution_id

  providers = {
    aws.us_east_1 = aws.us_east_1
  }
}

# Lambda@Edge for log upload
module "lambda_edge_log_upload" {
  source = "../../modules/operator-request-portal-lambda-functions/log-mgt-functions/lambda@edge-log-upload"

  environment                    = local.environment
  cloudfront_distribution_id     = module.operator_request_portal_static_site.cloudfront_distribution_id
  log_upload_tracking_table_name = module.lambda_log_upload.log_upload_tracking_table_name
  log_upload_tracking_table_arn  = module.lambda_log_upload.log_upload_tracking_table_arn

  providers = {
    aws.us_east_1 = aws.us_east_1
  }
}

module "operator_request_portal_static_site" {
  source = "../../modules/operator-request-portal-static-site"

  project_name   = local.project_name
  environment    = local.environment
  domain_name    = local.domain_name
  hosted_zone_id = local.hosted_zone_id
  tags           = var.tags

  # Pass Lambda@Edge ARN with version
  lambda_log_upload_arn = module.lambda_edge_log_upload.log_upload_edge_arn
}