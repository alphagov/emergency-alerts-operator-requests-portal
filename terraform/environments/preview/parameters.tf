data "aws_caller_identity" "current" {}

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

resource "aws_ssm_parameter" "mno_email_vodafone" {
  name        = "/operator-portal/mno-emails/vodafone"
  description = "Email address for Vodafone MNO operator"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
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
    ignore_changes = all
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
    ignore_changes = all
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
    ignore_changes = all
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_ee" {
  name        = "/operator-portal/mno-ids/ee"
  description = "UUID portal identifier for EE"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_vodafone" {
  name        = "/operator-portal/mno-ids/vodafone"
  description = "UUID portal identifier for Vodafone"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_three" {
  name        = "/operator-portal/mno-ids/three"
  description = "UUID portal identifier for Three"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_o2" {
  name        = "/operator-portal/mno-ids/o2"
  description = "UUID portal identifier for O2"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_email_test" {
  name        = "/operator-portal/mno-emails/test_mno_001"
  description = "Email address for the TEST_MNO_001 functional test operator — without this, the log-upload-handler Lambda finds no emails and skips the invite entirely (links_generated stays 0)"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "mno_portal_id_test" {
  name        = "/operator-portal/mno-ids/test_mno_001"
  description = "UUID portal identifier for the TEST_MNO_001 functional test operator"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
  }

  tags = var.tags
}
