resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.certificate_generation.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.csr_bucket_name}"
}

resource "aws_lambda_permission" "allow_bucket_notify_download" {
  statement_id  = "AllowExecutionFromS3BucketForDownload"
  action        = "lambda:InvokeFunction"
  function_name = var.download_notify_lambda_arn
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.csr_bucket_name}"
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = var.csr_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.certificate_generation.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "received/"
    filter_suffix       = ".csr"
  }

  lambda_function {
    lambda_function_arn = var.download_notify_lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "received/logs/"
    filter_suffix       = ".zip"
  }

  depends_on = [
    aws_lambda_permission.allow_bucket
  ]
}
