resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = format("%s-oac", local.bucket_name)
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_request_policy" "upload_token_header" {
  name = format("%s-upload-token-header", local.bucket_name)

  cookies_config {
    cookie_behavior = "none"
  }

  headers_config {
    header_behavior = "whitelist"
    headers {
      items = ["X-Upload-Token"]
    }
  }

  query_strings_config {
    query_string_behavior = "none"
  }
}

resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  comment             = format("CloudFront distribution for %s", local.bucket_name)
  aliases             = [var.domain_name]
  default_root_object = "index.html"
  is_ipv6_enabled     = false

  web_acl_id = aws_wafv2_web_acl.portal.arn

  # Site pages and assets. CloudFront can only read from this bucket.
  origin {
    domain_name = aws_s3_bucket.static_site.bucket_regional_domain_name
    origin_id   = "S3-Endpoint"

    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  # Uploaded logs. CloudFront can only write to this bucket, and only through /log-upload.
  origin {
    domain_name = aws_s3_bucket.logs.bucket_regional_domain_name
    origin_id   = "Logs-Endpoint"

    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  # Log uploads. The upload edge function checks every request and rewrites it to the
  # upload's fixed path in the logs bucket.
  ordered_cache_behavior {
    path_pattern           = "/log-upload"
    target_origin_id       = "Logs-Endpoint"
    viewer_protocol_policy = "https-only"

    allowed_methods = ["GET", "HEAD", "PUT", "OPTIONS", "DELETE", "POST", "PATCH"]
    cached_methods  = ["GET", "HEAD"]

    compress                 = true
    cache_policy_id          = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.upload_token_header.id

    dynamic "lambda_function_association" {
      for_each = var.lambda_log_upload_arn != "" ? [1] : []
      content {
        event_type   = "viewer-request"
        lambda_arn   = var.lambda_log_upload_arn
        include_body = false
      }
    }

    dynamic "lambda_function_association" {
      for_each = var.lambda_log_upload_arn != "" ? [1] : []
      content {
        event_type = "origin-response"
        lambda_arn = var.lambda_log_upload_arn
      }
    }
  }

  # Behavior for *.html: using S3-Endpoint with caching enabled.
  ordered_cache_behavior {
    path_pattern           = "*.html"
    target_origin_id       = "S3-Endpoint"
    viewer_protocol_policy = "https-only"

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]

    compress        = true
    cache_policy_id = data.aws_cloudfront_cache_policy.caching_optimized.id
  }

  # Default behavior: read-only access to the site bucket, uncached.
  default_cache_behavior {
    target_origin_id       = "S3-Endpoint"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    compress        = true
    cache_policy_id = data.aws_cloudfront_cache_policy.caching_disabled.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = aws_acm_certificate_validation.cert_validation.certificate_arn
    ssl_support_method             = "sni-only"
    minimum_protocol_version       = "TLSv1.2_2021"
    cloudfront_default_certificate = false
  }
}
