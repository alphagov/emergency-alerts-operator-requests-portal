resource "aws_dynamodb_table" "log_invite_tracking" {
  name         = "operator-request-portal-log-invites"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "AlertRef"

  attribute {
    name = "AlertRef"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Name        = "operator-request-portal-log-invites"
  }
}

resource "aws_dynamodb_table" "log_upload_tracking" {
  name         = "operator-request-portal-log-uploads"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "RequestId"

  attribute {
    name = "RequestId"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Name        = "operator-request-portal-log-uploads"
  }
}
