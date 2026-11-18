data "aws_caller_identity" "current" {}

locals {
  account_root_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"

  log_reader_role_arns = [
    for name in var.log_reader_role_names :
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${name}"
  ]
}

resource "aws_kms_key" "site" {
  description             = "Encrypts the Operator Request Portal site bucket (${local.bucket_name})"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(var.tags, { Name = "${local.bucket_name}-key" })
}

resource "aws_kms_alias" "site" {
  name          = "alias/${local.bucket_name}"
  target_key_id = aws_kms_key.site.key_id
}

resource "aws_kms_key_policy" "site" {
  key_id = aws_kms_key.site.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowAccountAdministration"
        Effect    = "Allow"
        Principal = { AWS = local.account_root_arn }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AllowCloudFrontToReadSitePages"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "kms:Decrypt"
        Resource  = "*"
        Condition = {
          StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.cdn.arn }
        }
      }
    ]
  })
}

resource "aws_kms_key" "logs" {
  description             = "Encrypts uploaded MNO logs in ${local.logs_bucket_name}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(var.tags, { Name = "${local.logs_bucket_name}-key" })
}

resource "aws_kms_alias" "logs" {
  name          = "alias/${local.logs_bucket_name}"
  target_key_id = aws_kms_key.logs.key_id
}

resource "aws_kms_key_policy" "logs" {
  key_id = aws_kms_key.logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Sid       = "AllowAccountAdministration"
        Effect    = "Allow"
        Principal = { AWS = local.account_root_arn }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AllowCloudFrontToEncryptUploads"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = ["kms:Encrypt", "kms:GenerateDataKey*"]
        Resource  = "*"
        Condition = {
          StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.cdn.arn }
        }
      }
      ], length(local.log_reader_role_arns) == 0 ? [] : [
      {
        Sid       = "AllowNamedLogReadersToDecrypt"
        Effect    = "Allow"
        Principal = { AWS = "*" }
        Action    = "kms:Decrypt"
        Resource  = "*"
        Condition = {
          StringEquals = { "aws:PrincipalAccount" = data.aws_caller_identity.current.account_id }
          ArnLike      = { "aws:PrincipalArn" = local.log_reader_role_arns }
        }
      }
    ])
  })
}
