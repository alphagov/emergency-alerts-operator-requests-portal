resource "aws_s3_bucket" "logs" {
  bucket = local.logs_bucket_name

  tags = merge(var.tags, { Name = local.logs_bucket_name })
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.logs.arn
    }
    bucket_key_enabled = true
  }

  depends_on = [aws_kms_key_policy.logs]
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "delete-uploaded-logs-after-retention-period"
    status = "Enabled"

    filter {
      prefix = "received/logs/"
    }

    expiration {
      days = var.log_retention_days
    }
  }
}

data "aws_iam_policy_document" "logs_bucket_policy_doc" {
  statement {
    sid    = "AllowCloudFrontUploadOnly"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions = [
      "s3:PutObject"
    ]
    resources = [
      format("arn:aws:s3:::%s/received/logs/*", aws_s3_bucket.logs.bucket)
    ]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.cdn.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs_bucket_policy_doc.json

  depends_on = [aws_s3_bucket_public_access_block.logs]
}
