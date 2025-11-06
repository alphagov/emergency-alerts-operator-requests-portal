data "archive_file" "notify_service_zip" {
  type        = "zip"
  source_file = format("%s/files/notify-service-lambda.py", path.module)
  output_path = format("%s/.terraform-assets/notify_email.zip", path.root)
}

resource "aws_lambda_function" "notify_service_lambda" {
  function_name = "${var.environment}-NotifyServiceLambda"
  handler       = "notify-service-lambda.lambda_handler"
  runtime       = "python3.13"
  role          = aws_iam_role.notify_lambda_role.arn

  filename    = data.archive_file.notify_service_zip.output_path
  timeout     = 30
  memory_size = 128
  layers      = [aws_lambda_layer_version.notify_layer.arn]

  environment {
    variables = {
      LOG_LEVEL            = "INFO"
      NOTIFY_API_KEY_PARAM = var.notify_api_key_parameter
    }
  }

  depends_on = [aws_iam_role_policy_attachment.notify_lambda_role_attach]
}
