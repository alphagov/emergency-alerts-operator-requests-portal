variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}

variable "log_bucket" {
  description = "Name of the S3 bucket CloudFront actually writes uploaded CBC logs to (the static-site/origin bucket), used for S3 read access and the S3->Lambda invoke permission"
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
