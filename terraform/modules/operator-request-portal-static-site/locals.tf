locals {
  bucket_name = "${var.project_name}-${var.environment}-static"

  page_configs = {
    "download-logs.html"      = { title = "Download Logs - Operator Portal", content_file = "download-logs.html" }
    "download-success.html"   = { title = "Download Success - Operator Portal", content_file = "download-success.html" }
    "error.html"              = { title = "Error - Operator Portal", content_file = "error.html" }
    "index.html"              = { title = "Welcome to the Operator Portal", content_file = "index.html" }
    "invalid-request.html"    = { title = "Invalid Request - Operator Portal", content_file = "invalid-request.html" }
    "link-expired.html"       = { title = "Link Expired - Operator Portal", content_file = "link-expired.html" }
    "link-invalid.html"       = { title = "Link Invalid - Operator Portal", content_file = "link-invalid.html" }
    "max-limit.html"          = { title = "Maximum Limit Reached - Operator Portal", content_file = "max-limit.html" }
    "method-not-allowed.html" = { title = "Method Not Allowed - Operator Portal", content_file = "method-not-allowed.html" }
    "upload-logs.html"        = { title = "Upload Logs - Operator Portal", content_file = "upload-logs.html" }
    "upload-success.html"     = { title = "Upload Success - Operator Portal", content_file = "upload-success.html" }
    "upload.html"             = { title = "Upload CSR - Operator Portal", content_file = "upload.html" }
  }

  default_html_files_map = {
    for key, config in local.page_configs :
    key => templatefile("${path.module}/files/templates/page.html.tpl", {
      title   = config.title
      content = file("${path.module}/files/content/${config.content_file}")
    })
  }

  resolved_html_files_map = length(var.html_files_map) > 0 ? var.html_files_map : local.default_html_files_map
}