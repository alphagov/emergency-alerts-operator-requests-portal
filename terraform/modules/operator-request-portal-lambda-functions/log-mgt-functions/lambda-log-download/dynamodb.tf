resource "aws_dynamodb_table" "download_tracking" {
  name         = "operator-request-portal-download-tracking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "RequestId"

  attribute {
    name = "RequestId"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Name        = "operator-request-portal-download-tracking"
  }
}
