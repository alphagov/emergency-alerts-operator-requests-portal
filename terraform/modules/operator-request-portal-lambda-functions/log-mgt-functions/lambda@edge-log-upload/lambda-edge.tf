data "aws_caller_identity" "current" {}

data "archive_file" "log_upload_edge_zip" {
  type        = "zip"
  output_path = format("%s/.terraform-assets/lambda_zip_file_log_upload_edge.zip", path.root)
  source_file = format("%s/files/edge-log-upload.py", path.module)
}

resource "aws_lambda_function" "log_upload_edge" {
  provider         = aws.us_east_1
  filename         = data.archive_file.log_upload_edge_zip.output_path
  function_name    = "${var.environment}-log-upload-edge"
  role             = aws_iam_role.edge_role.arn
  handler          = "edge-log-upload.lambda_handler"
  runtime          = "python3.13"
  publish          = true
  source_code_hash = data.archive_file.log_upload_edge_zip.output_base64sha256
}

resource "aws_lambda_permission" "allow_edge_invoke" {
  provider = aws.us_east_1

  statement_id = "PermitEdgeInvoke"
  action       = "lambda:InvokeFunction"

  function_name = aws_lambda_function.log_upload_edge.arn
  qualifier     = aws_lambda_function.log_upload_edge.version

  principal = "edgelambda.amazonaws.com"

  source_arn = "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/${var.cloudfront_distribution_id}"
}

output "log_upload_edge_arn" {
  value = "${aws_lambda_function.log_upload_edge.arn}:${aws_lambda_function.log_upload_edge.version}"
}
