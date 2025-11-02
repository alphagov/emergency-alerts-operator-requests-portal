resource "aws_s3_bucket" "static_site" {
  bucket = local.bucket_name

  tags = merge(var.tags, { Name = local.bucket_name })
}

resource "aws_s3_bucket_website_configuration" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

resource "aws_s3_bucket_public_access_block" "static_site_block" {
  bucket = aws_s3_bucket.static_site.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "static_site_policy" {
  bucket = aws_s3_bucket.static_site.id
  policy = data.aws_iam_policy_document.static_site_policy_doc.json
}

resource "aws_s3_object" "html_files" {
  for_each     = local.resolved_html_files_map
  bucket       = aws_s3_bucket.static_site.bucket
  key          = each.key
  content      = each.value
  content_type = "text/html"
  etag         = md5(each.value)
}
