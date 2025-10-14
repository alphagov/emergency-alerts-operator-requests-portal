resource "aws_lambda_permission" "lambda_invoke_permission" {
  for_each = toset([
    "${var.environment}-log-upload-handler",
    "${var.environment}-notify-on-upload",
    "${var.environment}-certificate-generation-lambda"
  ])

  statement_id  = "AllowInvokeFrom-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notify_service_lambda.function_name
  principal     = "lambda.amazonaws.com"
  source_arn    = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${each.key}"
}
