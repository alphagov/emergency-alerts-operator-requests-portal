output "log_upload_tracking_table_name" {
  description = "Name of the log upload tracking DynamoDB table"
  value       = aws_dynamodb_table.log_upload_tracking.name
}
