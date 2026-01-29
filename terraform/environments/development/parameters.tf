resource "aws_ssm_parameter" "notify_api_key" {
  name        = "/operator-portal/notify-client-api-key"
  description = "GOV.UK Notify API key for sending emails from the operator portal"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
  }

  tags = var.tags
}