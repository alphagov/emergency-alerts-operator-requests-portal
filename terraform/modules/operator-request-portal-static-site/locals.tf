locals {
  bucket_name = "${var.project_name}-${var.environment}-static"

  default_html_files_map = {
    "download-logs.html"      = format("%s/files/download-logs.html", path.module)
    "download-success.html"   = format("%s/files/download-success.html", path.module)
    "error.html"              = format("%s/files/error.html", path.module)
    "index.html"              = format("%s/files/index.html", path.module)
    "invalid-request.html"    = format("%s/files/invalid-request.html", path.module)
    "link-expired.html"       = format("%s/files/link-expired.html", path.module)
    "link-invalid.html"       = format("%s/files/link-invalid.html", path.module)
    "max-limit.html"          = format("%s/files/max-limit.html", path.module)
    "method-not-allowed.html" = format("%s/files/method-not-allowed.html", path.module)
    "upload-logs.html"        = format("%s/files/upload-logs.html", path.module)
    "upload-success.html"     = format("%s/files/upload-success.html", path.module)
    "upload.html"             = format("%s/files/upload.html", path.module)
  }

  resolved_html_files_map = length(var.html_files_map) > 0 ? var.html_files_map : local.default_html_files_map
}
