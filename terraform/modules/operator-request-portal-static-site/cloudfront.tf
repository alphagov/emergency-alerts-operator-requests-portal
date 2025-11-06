resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = format("%s-oac", local.bucket_name)
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  comment             = format("CloudFront distribution for %s", local.bucket_name)
  aliases             = [var.domain_name]
  default_root_object = "index.html"
  is_ipv6_enabled     = false

  # Origin 1: S3-Endpoint
  origin {
    domain_name = aws_s3_bucket.static_site.bucket_regional_domain_name
    origin_id   = "S3-Endpoint"

    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  # Origin 2: S3-Web-Endpoint
  origin {
    domain_name = format("%s.s3-website.%s.amazonaws.com", aws_s3_bucket.static_site.bucket, data.aws_region.current.id)
    origin_id   = "S3-Web-Endpoint"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  ordered_cache_behavior {
    path_pattern           = "/received/logs/*"
    target_origin_id       = "S3-Endpoint"
    viewer_protocol_policy = "https-only"

    allowed_methods = ["GET", "HEAD", "PUT", "OPTIONS", "DELETE", "POST", "PATCH"]
    cached_methods  = ["GET", "HEAD"]

    compress        = true
    cache_policy_id = data.aws_cloudfront_cache_policy.caching_disabled.id

    dynamic "lambda_function_association" {
      for_each = var.lambda_log_upload_arn != "" ? [1] : []
      content {
        event_type   = "viewer-request"
        lambda_arn   = var.lambda_log_upload_arn
        include_body = true
      }
    }
  }

  ordered_cache_behavior {
    path_pattern           = "/received/*"
    target_origin_id       = "S3-Endpoint"
    viewer_protocol_policy = "https-only"

    allowed_methods = ["GET", "HEAD", "PUT", "OPTIONS", "DELETE", "POST", "PATCH"]
    cached_methods  = ["GET", "HEAD"]

    compress        = true
    cache_policy_id = data.aws_cloudfront_cache_policy.caching_disabled.id

    dynamic "lambda_function_association" {
      for_each = var.lambda_log_upload_arn != "" ? [1] : []
      content {
        event_type   = "viewer-request"
        lambda_arn   = var.lambda_log_upload_arn
        include_body = true
      }
    }
  }

  # Behavior for downloads (no caching)
  ordered_cache_behavior {
    path_pattern           = "download/*"
    target_origin_id       = "S3-Endpoint"
    viewer_protocol_policy = "https-only"

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]

    compress        = true
    cache_policy_id = data.aws_cloudfront_cache_policy.caching_disabled.id

    dynamic "lambda_function_association" {
      for_each = var.lambda_log_download_arn != "" ? [1] : []
      content {
        event_type   = "viewer-request"
        lambda_arn   = var.lambda_log_download_arn
        include_body = true
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

  # Default behavior: use the S3-Web-Endpoint.
  # Because S3 website endpoints only support HTTP, accessing this via HTTPS will fail,
  # ensuring that only the defined behaviors are allowed.
  default_cache_behavior {
    target_origin_id       = "S3-Web-Endpoint"
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
