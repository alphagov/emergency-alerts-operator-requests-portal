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

variable "region" {
  type        = string
  description = "AWS region where the S3 bucket will be created (e.g. eu-west-2)."
}

variable "tags" {
  type        = map(string)
  description = "Common tags applied to all resources."
  default     = {}
}

variable "html_files_map" {
  type        = map(string)
  description = "Map of filenames to local file paths for HTML files."
  default     = {}
}

variable "lambda_csr_upload_arn" {
  description = "Lambda@Edge ARN for handling CSR uploads (with version appended)"
  type        = string
  default     = ""
}

variable "lambda_log_upload_arn" {
  description = "Lambda@Edge ARN for handling Log uploads (with version appended)"
  type        = string
  default     = ""
}

variable "lambda_log_download_arn" {
  description = "Lambda@Edge ARN for handling Log Downloads (with version appended)"
  type        = string
  default     = ""
}
