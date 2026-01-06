variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}

variable "download_tracking_table" {
  description = "Name of the DynamoDB table tracking download tokens"
  type        = string
}

variable "dynamodb_region" {
  description = "Region where the DynamoDB table lives"
  type        = string
  default     = "eu-west-2"
}

variable "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution to allow invoke"
  type        = string
}

variable "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution that should invoke this Lambda@Edge"
  type        = string
}
