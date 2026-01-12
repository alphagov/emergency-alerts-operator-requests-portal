data "archive_file" "download_edge_zip" {
  type        = "zip"
  output_path = format("%s/.terraform-assets/lambda_zip_file_download_edge.zip", path.root)
  source_file = format("%s/files/edge-log-download.py", path.module)
}

resource "aws_lambda_function" "download_edge" {
  provider         = aws.us_east_1
  function_name    = "${var.environment}-edge-log-download"
  filename         = data.archive_file.download_edge_zip.output_path
  handler          = "edge-log-download.lambda_handler"
  runtime          = "python3.13"
  role             = aws_iam_role.edge_role.arn
  publish          = true
  source_code_hash = data.archive_file.download_edge_zip.output_base64sha256
}

output "download_edge_lambda_arn" {
  description = "ARN:Version for Lambda@Edge"
  value       = "${aws_lambda_function.download_edge.arn}:${aws_lambda_function.download_edge.version}"
}
