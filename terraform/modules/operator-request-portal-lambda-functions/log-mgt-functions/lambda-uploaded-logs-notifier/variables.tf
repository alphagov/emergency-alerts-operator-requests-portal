variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}

variable "log_bucket" {
  description = "Name of the private bucket uploaded CBC logs are written to, used for S3 read access and the S3->Lambda trigger"
  type        = string
}

variable "gds_aws_profile" {
  description = "GDS AWS profile name used in the CLI download command sent to the alerts team"
  type        = string
}

variable "notify_lambda_arn" {
  description = "ARN of the Lambda that sends Notify emails"
  type        = string
}

variable "notify_template_id" {
  description = "GOV.UK Notify template ID for download emails"
  type        = string
}

variable "alerts_team_emails" {
  description = "Email address for Emergency Alerts team"
  type        = string
}

variable "log_invite_tracking_table" {
  description = "Name of the DynamoDB table used to track log upload invites (for MNO name and alert time lookup)"
  type        = string
}

variable "log_upload_tracking_table" {
  description = "Name of the DynamoDB table holding upload links, so a link can be released when an upload is rejected"
  type        = string
}

variable "notify_rejected_template_id" {
  description = "GOV.UK Notify template ID for the Alerts team email about a rejected upload. Empty skips the email."
  type        = string
  default     = ""
}

variable "log_bucket_kms_key_arn" {
  description = "ARN of the KMS key encrypting the logs bucket, so the notifier can read uploads"
  type        = string
}
