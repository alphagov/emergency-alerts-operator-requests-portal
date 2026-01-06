data "archive_file" "csr_upload_lambda_zip" {
  type        = "zip"
  output_path = format("%s/.terraform-assets/lambda_zip_file_csr_upload.zip", path.root)
  source_file = format("%s/files/edge-csr-upload.py", path.module)
}

resource "aws_lambda_function" "csr_upload_lambda" {
  provider         = aws.us_east_1
  function_name    = var.lambda_edge_function_name
  filename         = data.archive_file.csr_upload_lambda_zip.output_path
  role             = aws_iam_role.lambda_edge_role.arn
  handler          = "edge-csr-upload.lambda_handler"
  runtime          = "python3.13"
  publish          = true
  timeout          = 30
  source_code_hash = data.archive_file.csr_upload_lambda_zip.output_base64sha256

  tags = {
    Name = "CSR Upload Handler"
    Type = "Lambda@Edge"
  }
}
