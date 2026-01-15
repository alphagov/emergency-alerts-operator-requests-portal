data "archive_file" "log_upload_zip" {
  type        = "zip"
  output_path = format("%s/.terraform-assets/lambda_zip_file_log_upload.zip", path.root)
  source_file = format("%s/files/log-upload-handler.py", path.module)
}

resource "aws_lambda_function" "log_upload" {
  function_name = "${var.environment}-log-upload-handler"
  handler       = "log-upload-handler.lambda_handler"
  runtime       = "python3.13"
  role          = aws_iam_role.log_upload_role.arn

  filename         = data.archive_file.log_upload_zip.output_path
  source_code_hash = data.archive_file.log_upload_zip.output_base64sha256

  environment {
    variables = {
      LOG_BUCKET_NAME            = var.log_bucket_name
      UPLOAD_DOMAIN              = local.default_upload_domain
      NOTIFY_LAMBDA_ARN          = var.notify_lambda_arn
      NOTIFY_LOG_TEMPLATE_ID     = var.notify_log_template_id
      UPLOAD_LINK_EXPIRY_SECONDS = tostring(var.upload_link_expiry_seconds)
      LOG_INVITE_TRACKING_TABLE  = aws_dynamodb_table.log_invite_tracking.name
      LOG_UPLOAD_TRACKING_TABLE  = aws_dynamodb_table.log_upload_tracking.name
    }
  }

  timeout     = 30
  memory_size = 256
}
