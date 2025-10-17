resource "aws_dynamodb_table" "csr_uploads" {
  name         = "operator-request-portal-csr-tracking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "RequestId"

  attribute {
    name = "RequestId"
    type = "S"
  }

  ttl {
    attribute_name = "ExpiryTime"
    enabled        = true
  }

  tags = {
    Environment = var.environment
    Name        = "operator-request-portal-csr-tracking"
  }
}
