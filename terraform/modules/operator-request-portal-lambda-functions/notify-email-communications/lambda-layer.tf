resource "null_resource" "notify_layer_package" {
  triggers = {
    requirements = filemd5("${path.module}/files/notify-layer-requirements.txt")
  }

  provisioner "local-exec" {
    command = "python -c \"import os; os.makedirs('${path.module}/files/notify_layer_package/python', exist_ok=True); os.makedirs('${path.module}/files/zip', exist_ok=True)\""
  }

  provisioner "local-exec" {
    command = "python -m pip install -r ${path.module}/files/notify-layer-requirements.txt -t ${path.module}/files/notify_layer_package/python --upgrade"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "python -c \"import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['${path.module}/files/notify_layer_package', '${path.module}/files/zip']]\""
  }
}

resource "archive_file" "notify_layer_zip" {
  depends_on = [null_resource.notify_layer_package]
  
  type        = "zip"
  output_path = "${path.module}/files/zip/notify-layer.zip"
  source_dir  = "${path.module}/files/notify_layer_package"
  
  lifecycle {
    replace_triggered_by = [null_resource.notify_layer_package]
  }
}

resource "aws_lambda_layer_version" "notify_layer" {
  layer_name          = "notifications-python-client-layer"
  description         = "Layer containing the GOV.UK Notify Python client"
  filename            = archive_file.notify_layer_zip.output_path
  source_code_hash    = archive_file.notify_layer_zip.output_base64sha256
  compatible_runtimes = ["python3.12", "python3.13"]
  
  depends_on = [archive_file.notify_layer_zip]
}