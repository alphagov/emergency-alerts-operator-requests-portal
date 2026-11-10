variable "environment" {
  description = "Environment (e.g. dev, staging, prod)."
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

variable "eas_preview_account_id" {
  type        = string
  description = "EAS Preview account ID for cross-account Lambda invocation"
  default     = "644514520413"
}

variable "eas_staging_account_id" {
  type        = string
  description = "EAS Staging account ID for cross-account Lambda invocation"
  default     = "460715564357"
}

variable "eas_development_account_id" {
  type        = string
  description = "EAS Development account ID for cross-account Lambda invocation"
  default     = "071839617283"
}

variable "mno_email_ssm_prefix" {
  description = "SSM Parameter Store prefix for MNO contact email addresses"
  type        = string
  default     = "/operator-portal/mno-emails"
}

variable "mno_id_ssm_prefix" {
  description = "SSM Parameter Store prefix for MNO 32-character portal identifiers"
  type        = string
  default     = "/operator-portal/mno-ids"
}
