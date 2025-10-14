resource "aws_lambda_layer_version" "notify_layer" {
  layer_name          = "notifications-python-client-layer"
  description         = "Layer containing the GOV.UK Notify Python client"
  filename            = format("%s/files/notify-layer.zip", path.module)
  compatible_runtimes = ["python3.12", "python3.13"]
}
