output "notify_on_upload_lambda_arn" {
  description = "ARN of the S3-triggered notify-on-upload Lambda"
  value       = aws_lambda_function.notify_on_upload.arn
}

output "notify_on_upload_permission_id" {
  value = aws_lambda_permission.allow_s3.statement_id
}

output "download_tracking_table_name" {
  description = "Name of the download tracking DynamoDB table"
  value       = aws_dynamodb_table.download_tracking.name
}
