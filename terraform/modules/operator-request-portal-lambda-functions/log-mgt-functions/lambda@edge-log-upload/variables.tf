variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}
variable "upload_domain" {
  description = "Static site domain for uploads"
  type        = string
}
variable "dynamodb_region" {
  description = "Region of the DynamoDB table"
  type        = string
  default     = "eu-west-2"
}
variable "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution that will invoke this Lambda@Edge"
  type        = string
}
