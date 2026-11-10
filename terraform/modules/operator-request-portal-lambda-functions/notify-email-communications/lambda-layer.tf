resource "archive_file" "notify_layer_zip" {
  type        = "zip"
  output_path = "${path.module}/files/zip/notify-layer.zip"
  source_dir  = "${path.module}/files/notify_layer_package"
}

resource "aws_lambda_layer_version" "notify_layer" {
  layer_name          = "notifications-python-client-layer"
  description         = "Layer containing the GOV.UK Notify Python client"
  filename            = archive_file.notify_layer_zip.output_path
  source_code_hash    = archive_file.notify_layer_zip.output_base64sha256
  compatible_runtimes = ["python3.12", "python3.13"]

  depends_on = [archive_file.notify_layer_zip]
}