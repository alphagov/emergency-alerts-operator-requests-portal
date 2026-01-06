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
