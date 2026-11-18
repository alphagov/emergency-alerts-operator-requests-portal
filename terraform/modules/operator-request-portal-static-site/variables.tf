variable "project_name" {
  type        = string
  description = "Name of the project."
}

variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}

variable "domain_name" {
  type        = string
  description = "The full custom domain for the CloudFront distribution."
}

variable "hosted_zone_id" {
  type        = string
  description = "The Route53 Hosted Zone ID for the domain_name."
}

variable "tags" {
  type        = map(string)
  description = "Common tags applied to all resources."
  default     = {}
}

variable "lambda_log_upload_arn" {
  description = "Lambda@Edge ARN for handling Log uploads (with version appended)"
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "Days uploaded logs are kept before deletion."
  type        = number
  default     = 365
}

variable "waf_allowed_country_codes" {
  description = "Countries allowed through the WAF."
  type        = list(string)
  default     = ["GB"]
}

variable "waf_rate_limit_per_minute" {
  description = "Requests allowed per IP address per minute before the WAF blocks that IP."
  type        = number
  default     = 600
}

variable "log_reader_role_names" {
  description = "IAM role names that can decrypt uploaded logs."
  type        = list(string)
}
