data "archive_file" "certificate_dependencies_zip" {
  type        = "zip"
  output_path = format("%s/.terraform-assets/lambda_layer_certificate_dependencies.zip", path.root)
  source_dir  = format("%s/files/certificate_dependencies", path.module)
}

data "archive_file" "certificate_generation_zip" {
  type        = "zip"
  output_path = format("%s/.terraform-assets/lambda_zip_file_certificate_generation.zip", path.root)
  source_file = format("%s/files/lambda-cert-generation.py", path.module)
}

resource "aws_lambda_layer_version" "certificate_dependencies" {
  layer_name          = "certificate-generation-dependencies"
  description         = "Dependencies for the Certificate Generation Lambda"
  filename            = data.archive_file.certificate_dependencies_zip.output_path
  compatible_runtimes = ["python3.9"]
  source_code_hash    = data.archive_file.certificate_dependencies_zip.output_base64sha256
}

resource "aws_lambda_function" "certificate_generation" {
  function_name = "${var.environment}-certificate-generation-lambda"
  filename      = data.archive_file.certificate_generation_zip.output_path
  handler       = "lambda.lambda_handler"
  runtime       = "python3.9"
  role          = aws_iam_role.certificate_generation_role.arn
  timeout       = 300
  memory_size   = 256

  layers = [aws_lambda_layer_version.certificate_dependencies.arn]

  environment {
    variables = {
      CSR_BUCKET_NAME               = var.csr_bucket_name
      CERT_TABLE_NAME               = aws_dynamodb_table.certificates_table.name
      MNO_CONFIG_TABLE_NAME         = aws_dynamodb_table.mno_config_table.name
      CONTACTS_TABLE_NAME           = aws_dynamodb_table.mno_contacts_table.name
      CERTIFICATE_DOMAIN            = local.certificate_domain
      PCA_ARN                       = var.pca_arn
      NOTIFY_LAMBDA_ARN             = var.notify_lambda_arn
      VALID_CSR_TEMPLATE_ID         = var.notify_valid_csr_template_id
      INVALID_FIRST_CSR_TEMPLATE_ID = var.notify_invalid_first_csr_template_id
      INVALID_RETRY_CSR_TEMPLATE_ID = var.notify_invalid_retry_csr_template_id
    }
  }

  source_code_hash = data.archive_file.certificate_generation_zip.output_base64sha256

  depends_on = [
    aws_iam_role_policy_attachment.certificate_generation_policy_attachment
  ]
}
