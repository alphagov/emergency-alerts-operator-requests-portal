data "aws_region" "current" {}

data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_iam_policy_document" "static_site_policy_doc" {
  statement {
    sid    = "AllowCloudFrontRead"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions = [
      "s3:GetObject"
    ]
    resources = [
      format("arn:aws:s3:::%s/*.html", aws_s3_bucket.static_site.bucket),
      format("arn:aws:s3:::%s/download/*", aws_s3_bucket.static_site.bucket)
    ]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.cdn.arn]
    }
  }

  statement {
    sid    = "AllowCloudFrontWrite"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions = [
      "s3:PutObject"
    ]
    resources = [
      format("arn:aws:s3:::%s/received/*", aws_s3_bucket.static_site.bucket)
    ]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.cdn.arn]
    }
  }

  statement {
    sid    = "AllowCloudFrontReadUploadedLogs"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions = [
      "s3:GetObject"
    ]
    resources = [
      format("arn:aws:s3:::%s/received/logs/*", aws_s3_bucket.static_site.bucket)
    ]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.cdn.arn]
    }
  }
}
