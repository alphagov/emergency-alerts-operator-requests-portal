variable "lambda_edge_function_name" {
  description = "Name of the Lambda@Edge function"
  type        = string
  default     = "csr-upload-handler"
}

variable "lambda_edge_zip_file" {
  description = "Path to the zipped Lambda@Edge deployment package"
  type        = string
  default     = "lambda-function.zip"
}

variable "environment" {
  type        = string
  description = "Environment (e.g. dev, staging, prod)."
}
