variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}

variable "log_bucket" {
  description = "Name of the S3 bucket CloudFront actually writes uploaded CBC logs to (the static-site/origin bucket), used for S3 read access and the S3->Lambda invoke permission"
  type        = string
}

variable "download_domain" {
  description = "Domain for downloads (CloudFront alias)"
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

variable "download_link_expiry_days" {
  description = "Validity of download links in days"
  type        = number
  default     = 30
}

variable "log_upload_tracking_table" {
  description = "Name of the DynamoDB table used to track log upload invites (for MNO name lookup)"
  type        = string
}
