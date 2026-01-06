data "archive_file" "notify_on_upload_zip" {
  type        = "zip"
  output_path = format("%s/.terraform-assets/lambda_zip_file_notify_on_upload.zip", path.root)
  source_file = format("%s/files/lambda-log-download.py", path.module)
}

resource "aws_lambda_function" "notify_on_upload" {
  function_name    = "${var.environment}-lambda-log-download"
  filename         = data.archive_file.notify_on_upload_zip.output_path
  handler          = "lambda-log-download.lambda_handler"
  runtime          = "python3.13"
  role             = aws_iam_role.lambda_role.arn
  source_code_hash = data.archive_file.notify_on_upload_zip.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      LOG_BUCKET                = var.log_bucket
      DOWNLOAD_DOMAIN           = var.download_domain
      NOTIFY_LAMBDA_ARN         = var.notify_lambda_arn
      NOTIFY_TEMPLATE_ID        = var.notify_template_id
      DOWNLOAD_TRACKING_TABLE   = aws_dynamodb_table.download_tracking.name
      ALERTS_TEAM_EMAILS        = var.alerts_team_emails
      DOWNLOAD_LINK_EXPIRY_DAYS = tostring(var.download_link_expiry_days)
    }
  }
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notify_on_upload.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.log_bucket}"
}
