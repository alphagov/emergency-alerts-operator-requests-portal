output "certificate_generation_lambda_arn" {
  description = "ARN of the Certificate Generation Lambda function"
  value       = aws_lambda_function.certificate_generation.arn
}

output "certificate_generation_lambda_name" {
  description = "Name of the Certificate Generation Lambda function"
  value       = aws_lambda_function.certificate_generation.function_name
}

output "certificates_table_name" {
  description = "Name of the MNO certificates DynamoDB table"
  value       = aws_dynamodb_table.certificates_table.name
}

output "mno_config_table_name" {
  description = "Name of the MNO config DynamoDB table"
  value       = aws_dynamodb_table.mno_config_table.name
}

output "mno_contacts_table_name" {
  description = "Name of the MNO contacts DynamoDB table"
  value       = aws_dynamodb_table.mno_contacts_table.name
}
