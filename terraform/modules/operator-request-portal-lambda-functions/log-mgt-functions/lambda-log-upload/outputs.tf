output "log_upload_lambda_arn" {
  description = "ARN of the log-upload Lambda function"
  value       = aws_lambda_function.log_upload.arn
}

output "log_invite_tracking_table_name" {
  description = "Name of the log invite tracking DynamoDB table"
  value       = aws_dynamodb_table.log_invite_tracking.name
}
