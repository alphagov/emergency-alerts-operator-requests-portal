output "lambda_edge_function_arn" {
  description = "ARN of the Lambda@Edge function"
  value       = aws_lambda_function.csr_upload_lambda.arn
}

output "csr_upload_lambda_arn" {
  description = "ARN of the CSR Upload Lambda function (with version)"
  value       = "${aws_lambda_function.csr_upload_lambda.arn}:${aws_lambda_function.csr_upload_lambda.version}"
}

output "csr_uploads_table_name" {
  description = "Name of the CSR uploads tracking DynamoDB table"
  value       = aws_dynamodb_table.csr_uploads.name
}
