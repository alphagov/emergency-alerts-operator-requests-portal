resource "aws_s3_bucket" "static_site" {
  bucket = local.bucket_name

  tags = merge(var.tags, { Name = local.bucket_name })
}

resource "aws_s3_bucket_server_side_encryption_configuration" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.site.arn
    }
    bucket_key_enabled = true
  }

  depends_on = [aws_kms_key_policy.site]
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
  for_each      = local.html_files_map
  bucket        = aws_s3_bucket.static_site.bucket
  key           = each.key
  content       = each.value
  content_type  = "text/html"
  cache_control = "no-cache"

  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.site.arn
  bucket_key_enabled     = true

  depends_on = [aws_kms_key_policy.site]
}

resource "null_resource" "build_assets" {
  triggers = {
    gulpfile     = filesha1("${path.module}/files/gulpfile.js")
    package_json = filesha1("${path.module}/files/package.json")
    package_lock = fileexists("${path.module}/files/package-lock.json") ? filesha1("${path.module}/files/package-lock.json") : ""
  }

  provisioner "local-exec" {
    command = "cd ${path.module}/files && npm install && npm run build"
  }
}

resource "aws_s3_object" "assets" {
  for_each = toset(try(fileset("${path.module}/files/assets", "**/*"), []))

  bucket      = aws_s3_bucket.static_site.bucket
  key         = "assets/${each.value}"
  source      = "${path.module}/files/assets/${each.value}"
  source_hash = filemd5("${path.module}/files/assets/${each.value}")
  content_type = lookup(
    {
      "css"   = "text/css"
      "js"    = "application/javascript"
      "json"  = "application/manifest+json"
      "ico"   = "image/x-icon"
      "svg"   = "image/svg+xml"
      "png"   = "image/png"
      "jpg"   = "image/jpeg"
      "jpeg"  = "image/jpeg"
      "gif"   = "image/gif"
      "woff"  = "font/woff"
      "woff2" = "font/woff2"
      "ttf"   = "font/ttf"
      "eot"   = "application/vnd.ms-fontobject"
    },
    element(split(".", each.value), length(split(".", each.value)) - 1),
    "application/octet-stream"
  )

  # Asset names don't change between releases, so browsers must also revalidate these
  cache_control = "no-cache"

  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.site.arn
  bucket_key_enabled     = true

  depends_on = [null_resource.build_assets, aws_kms_key_policy.site]
}
