module "shared" {
  source = "../../shared"

  environment                = var.environment
  project_name               = var.project_name
  infra_mgt_state_bucket     = var.infra_mgt_state_bucket
  infra_mgt_state_key        = var.infra_mgt_state_key
  infra_mgt_state_region     = var.infra_mgt_state_region
  download_link_expiry_days  = var.download_link_expiry_days
  upload_link_expiry_seconds = var.upload_link_expiry_seconds
  tags                       = var.tags
}

locals {
  hosted_zone_id           = module.shared.hosted_zone_id
  domain_name              = module.shared.domain_name
  pca_arn                  = module.shared.pca_arn
  notify_api_key_parameter = module.shared.notify_api_key_parameter_name
  notify_templates         = module.shared.notify_templates
  alerts_team_emails       = module.shared.alerts_team_emails

  environment               = var.environment
  project_name              = var.project_name
  csr_bucket_name           = "${var.project_name}-csr-${var.environment}"
  log_bucket_name           = "${var.project_name}-logs-${var.environment}"
  static_bucket_name        = "${var.project_name}-static-${var.environment}"
  download_tracking_table   = "${var.project_name}-download-tracking-${var.environment}"
  log_invite_tracking_table = "${var.project_name}-log-invite-tracking-${var.environment}"
  log_upload_tracking_table = "${var.project_name}-log-upload-tracking-${var.environment}"
  csr_uploads_table         = "${var.project_name}-csr-uploads-${var.environment}"
  certificates_table        = "${var.project_name}-certificates-${var.environment}"
  mno_config_table          = "${var.project_name}-mno-config-${var.environment}"
  mno_contacts_table        = "${var.project_name}-mno-contacts-${var.environment}"
}

resource "aws_s3_bucket" "csr_bucket" {
  bucket = local.csr_bucket_name

  tags = merge(
    var.tags,
    {
      Name    = local.csr_bucket_name
      Purpose = "CSR Storage"
    }
  )
}

resource "aws_s3_bucket_versioning" "csr_bucket_versioning" {
  bucket = aws_s3_bucket.csr_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "csr_bucket_public_access_block" {
  bucket = aws_s3_bucket.csr_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "csr_bucket_encryption" {
  bucket = aws_s3_bucket.csr_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Log Bucket
resource "aws_s3_bucket" "log_bucket" {
  bucket = local.log_bucket_name

  tags = merge(
    var.tags,
    {
      Name    = local.log_bucket_name
      Purpose = "Log Storage"
    }
  )
}

resource "aws_s3_bucket_versioning" "log_bucket_versioning" {
  bucket = aws_s3_bucket.log_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "log_bucket_public_access_block" {
  bucket = aws_s3_bucket.log_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "log_bucket_encryption" {
  bucket = aws_s3_bucket.log_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Notify email communications service
module "notify_email_communications" {
  source = "../../modules/operator-request-portal-lambda-functions/notify-email-communications"

  notify_api_key_parameter = local.notify_api_key_parameter
  environment              = local.environment
}

# Certificate generation Lambda
# module "lambda_certificate_generation" {
#   source = "../../modules/operator-request-portal-lambda-functions/cert-mgt-functions/lambda-certificate-generation"

#   aws_region                           = "eu-west-2"
#   environment                          = local.environment
#   csr_bucket_name                      = local.csr_bucket_name
#   certificate_domain                   = local.domain_name
#   pca_arn                              = local.pca_arn
#   notify_lambda_arn                    = module.notify_email_communications.notify_lambda_function_arn
#   notify_valid_csr_template_id         = local.notify_templates.valid_csr
#   notify_invalid_first_csr_template_id = local.notify_templates.invalid_first_csr
#   notify_invalid_retry_csr_template_id = local.notify_templates.invalid_retry_csr
#   download_notify_lambda_arn           = module.lambda_log_download.notify_on_upload_lambda_arn
# }

# Log download Lambda
module "lambda_log_download" {
  source = "../../modules/operator-request-portal-lambda-functions/log-mgt-functions/lambda-log-download"

  environment               = local.environment
  log_bucket                = local.log_bucket_name
  download_domain           = local.domain_name
  notify_lambda_arn         = module.notify_email_communications.notify_lambda_function_arn
  notify_template_id        = local.notify_templates.log_download
  alerts_team_emails        = local.alerts_team_emails
  download_link_expiry_days = var.download_link_expiry_days
}

# Log upload Lambda
module "lambda_log_upload" {
  source = "../../modules/operator-request-portal-lambda-functions/log-mgt-functions/lambda-log-upload"

  environment                = local.environment
  log_bucket_name            = local.log_bucket_name
  upload_domain              = local.domain_name
  notify_lambda_arn          = module.notify_email_communications.notify_lambda_function_arn
  notify_log_template_id     = local.notify_templates.log_upload_invite
  upload_link_expiry_seconds = var.upload_link_expiry_seconds
  dynamodb_region            = "eu-west-2"
}

# Lambda@Edge for CSR upload
# module "lambda_edge_csr_upload" {
#   source = "../../modules/operator-request-portal-lambda-functions/cert-mgt-functions/lambda@edge-csr-upload"

#   environment               = local.environment
#   lambda_edge_function_name = "${local.project_name}-csr-upload-${local.environment}"
#   lambda_edge_zip_file      = "lambda-function.zip"

#   providers = {
#     aws.us_east_1 = aws.us_east_1
#   }
# }

# Lambda@Edge for log download
module "lambda_edge_log_download" {
  source = "../../modules/operator-request-portal-lambda-functions/log-mgt-functions/lambda@edge-log-download"

  environment                 = local.environment
  download_tracking_table     = local.download_tracking_table
  dynamodb_region             = "eu-west-2"
  cloudfront_distribution_arn = module.operator_request_portal_static_site.cloudfront_distribution_arn
  cloudfront_distribution_id  = module.operator_request_portal_static_site.cloudfront_distribution_id

  providers = {
    aws.us_east_1 = aws.us_east_1
  }
}

# Lambda@Edge for log upload
module "lambda_edge_log_upload" {
  source = "../../modules/operator-request-portal-lambda-functions/log-mgt-functions/lambda@edge-log-upload"

  environment                = local.environment
  upload_domain              = local.domain_name
  dynamodb_region            = "eu-west-2"
  cloudfront_distribution_id = module.operator_request_portal_static_site.cloudfront_distribution_id

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
  region         = "eu-west-2"
  tags           = var.tags

  # HTML files will be uploaded from files/ directory
  html_files_map = var.html_files_map

  # Pass Lambda@Edge ARNs with versions
  lambda_csr_upload_arn   = module.lambda_edge_csr_upload.lambda_edge_function_arn
  lambda_log_upload_arn   = module.lambda_edge_log_upload.log_upload_edge_arn
  lambda_log_download_arn = module.lambda_edge_log_download.download_edge_lambda_arn
}