variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}

variable "csr_bucket_name" {
  description = "Name of the S3 bucket for CSR storage"
  type        = string
}

variable "certificate_domain" {
  description = "Domain for certificate download URLs"
  type        = string
}

variable "pca_arn" {
  description = "ARN of the Private Certificate Authority"
  type        = string
}

variable "notify_lambda_arn" {
  description = "ARN of the Notify Lambda"
  type        = string
}

variable "notify_valid_csr_template_id" {
  description = "GOV.UK Notify template ID for valid CSR notifications"
  type        = string
}

variable "notify_invalid_first_csr_template_id" {
  description = "GOV.UK Notify template ID for invalid first CSR notifications"
  type        = string
}

variable "notify_invalid_retry_csr_template_id" {
  description = "GOV.UK Notify template ID for invalid retry CSR notifications"
  type        = string
}

variable "download_notify_lambda_arn" {
  description = "ARN of the Lambda that sends download notifications when a log is uploaded"
  type        = string
}
