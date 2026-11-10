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
