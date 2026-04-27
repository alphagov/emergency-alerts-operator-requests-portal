variable "environment" {
  description = "Environment (e.g. dev, staging, prod)."
  type        = string
}

variable "log_bucket_name" {
  description = "S3 bucket to hold uploaded logs"
  type        = string
}

variable "upload_domain" {
  description = "The CloudFront/S3 domain used for upload URLs"
  type        = string
}

variable "notify_lambda_arn" {
  description = "ARN of the Notify‐sending Lambda to invoke"
  type        = string
}

variable "notify_log_template_id" {
  description = "Notify template ID for log upload invites"
  type        = string
}

variable "upload_link_expiry_seconds" {
  description = "Seconds until the upload link expires"
  type        = number
  default     = 604800
}

variable "dynamodb_region" {
  description = "Region of the DynamoDB table"
  type        = string
  default     = "eu-west-2"
}

variable "eas_preview_account_id" {
  type        = string
  description = "EAS Preview account ID for cross-account Lambda invocation"
  default     = "644514520413"
}

variable "mno_email_ssm_prefix" {
  description = "SSM Parameter Store prefix for MNO contact email addresses"
  type        = string
  default     = "/operator-portal/mno-emails"
}
