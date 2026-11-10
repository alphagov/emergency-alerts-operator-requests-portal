variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}
variable "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution that will invoke this Lambda@Edge"
  type        = string
}
variable "log_upload_tracking_table_arn" {
  description = "ARN of the log upload tracking DynamoDB table (owned by the lambda-log-upload module)"
  type        = string
}
