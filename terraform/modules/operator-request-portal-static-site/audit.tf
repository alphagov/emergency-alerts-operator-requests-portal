data "aws_region" "current" {}

locals {
  audit_bucket_name = "${var.project_name}-audit-${var.environment}"
  access_trail_name = "${local.logs_bucket_name}-access"
  access_trail_arn  = "arn:aws:cloudtrail:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:trail/${local.access_trail_name}"
}

resource "aws_s3_bucket" "audit" {
  bucket = local.audit_bucket_name

  tags = merge(var.tags, { Name = local.audit_bucket_name })
}

resource "aws_s3_bucket_public_access_block" "audit" {
  bucket = aws_s3_bucket.audit.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.logs.arn
    }
    bucket_key_enabled = true
  }

  depends_on = [aws_kms_key_policy.logs]
}

resource "aws_s3_bucket_lifecycle_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    id     = "delete-access-records-after-retention-period"
    status = "Enabled"

    filter {
      prefix = "AWSLogs/"
    }

    expiration {
      days = var.log_retention_days
    }
  }
}

data "aws_iam_policy_document" "audit_bucket_policy_doc" {
  statement {
    sid    = "AllowAccessTrailAclCheck"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.audit.arn]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [local.access_trail_arn]
    }
  }

  statement {
    sid    = "AllowAccessTrailWrite"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.audit.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [local.access_trail_arn]
    }
  }
}

resource "aws_s3_bucket_policy" "audit" {
  bucket = aws_s3_bucket.audit.id
  policy = data.aws_iam_policy_document.audit_bucket_policy_doc.json

  depends_on = [aws_s3_bucket_public_access_block.audit]
}

resource "aws_cloudtrail" "logs_access" {
  name                          = local.access_trail_name
  s3_bucket_name                = aws_s3_bucket.audit.id
  kms_key_id                    = aws_kms_key.logs.arn
  enable_log_file_validation    = true
  include_global_service_events = false
  is_multi_region_trail         = false

  advanced_event_selector {
    name = "Reads, writes and deletes of uploaded logs"

    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }

    field_selector {
      field  = "resources.type"
      equals = ["AWS::S3::Object"]
    }

    field_selector {
      field       = "resources.ARN"
      starts_with = ["${aws_s3_bucket.logs.arn}/"]
    }
  }

  tags = var.tags

  depends_on = [aws_s3_bucket_policy.audit, aws_kms_key_policy.logs]
}
