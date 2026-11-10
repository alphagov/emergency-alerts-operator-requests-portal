resource "aws_ssm_parameter" "notify_api_key" {
  name        = "/operator-portal/notify-client-api-key"
  description = "GOV.UK Notify API key for sending emails from the operator portal"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_email_vodafone" {
  name        = "/operator-portal/mno-emails/vodafone"
  description = "Email address for Vodafone MNO operator"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_email_o2" {
  name        = "/operator-portal/mno-emails/o2"
  description = "Email address for O2 MNO operator"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_email_three" {
  name        = "/operator-portal/mno-emails/three"
  description = "Email address for three MNO operator"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_email_ee" {
  name        = "/operator-portal/mno-emails/ee"
  description = "Email address for EE MNO operator"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_ee" {
  name        = "/operator-portal/mno-ids/ee"
  description = "32-character portal identifier for EE"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_vodafone" {
  name        = "/operator-portal/mno-ids/vodafone"
  description = "32-character portal identifier for Vodafone"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_three" {
  name        = "/operator-portal/mno-ids/three"
  description = "32-character portal identifier for Three"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_o2" {
  name        = "/operator-portal/mno-ids/o2"
  description = "32-character portal identifier for O2"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}
