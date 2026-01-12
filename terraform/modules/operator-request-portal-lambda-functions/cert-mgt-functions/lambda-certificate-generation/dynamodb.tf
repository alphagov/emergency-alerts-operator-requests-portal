resource "aws_dynamodb_table" "certificates_table" {
  name         = "operator-request-portal-mno-certificates"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "MnoID"
  range_key    = "CertID"

  attribute {
    name = "MnoID"
    type = "S"
  }
  attribute {
    name = "CertID"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Name        = "operator-request-portal-mno-certificates"
  }
}

resource "aws_dynamodb_table" "mno_config_table" {
  name         = "operator-request-portal-mno-config"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "MnoID"

  attribute {
    name = "MnoID"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Name        = "operator-request-portal-mno-config"
  }
}

resource "aws_dynamodb_table" "mno_contacts_table" {
  name         = "operator-request-portal-mno-contacts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "MnoID"

  attribute {
    name = "MnoID"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Name        = "operator-request-portal-mno-contacts"
  }
}
