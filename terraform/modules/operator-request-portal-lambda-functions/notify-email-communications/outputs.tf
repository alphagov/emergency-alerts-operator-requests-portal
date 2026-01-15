output "notify_lambda_function_arn" {
  description = "ARN of the Notify Service Lambda function"
  value       = aws_lambda_function.notify_service_lambda.arn
}
