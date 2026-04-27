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

resource "aws_ssm_parameter" "functional_test_account_id" {
  name        = "/operator-portal/functional-tests/account-id"
  description = "AWS account ID for the MNO portal — used by CodeBuild to assume the eas-terraformer role"
  type        = "String"
  value       = data.aws_caller_identity.current.account_id

  tags = var.tags
}

resource "aws_ssm_parameter" "functional_test_environment" {
  name        = "/operator-portal/functional-tests/environment"
  description = "Environment name — used by CodeBuild to construct the eas-terraformer external ID"
  type        = "String"
  value       = var.environment

  tags = var.tags
}

resource "aws_ssm_parameter" "functional_test_log_upload_lambda_name" {
  name        = "/operator-portal/functional-tests/log-upload-lambda-name"
  description = "Name of the log upload handler Lambda invoked by the functional tests"
  type        = "String"
  value       = "mno-portal-${var.environment}-log-upload-handler"

  tags = var.tags
}

resource "aws_ssm_parameter" "functional_test_log_bucket_name" {
  name        = "/operator-portal/functional-tests/log-bucket-name"
  description = "Name of the S3 bucket the functional tests assert log files land in"
  type        = "String"
  value       = "operator-request-portal-${var.environment}"

  tags = var.tags
}

resource "aws_ssm_parameter" "functional_test_mno_id" {
  name        = "/operator-portal/functional-tests/test-mno-id"
  description = "MNO ID used by the functional tests when invoking the log upload handler"
  type        = "String"
  value       = "TEST_MNO_001"

  tags = var.tags
}

resource "aws_ssm_parameter" "functional_test_notify_api_key" {
  name        = "/operator-portal/functional-tests/notify-api-key"
  description = "GOV.UK Notify API key used by the functional tests to poll for delivered emails"
  type        = "SecureString"
  key_id      = "alias/aws/ssm"
  value       = "dummy"

  lifecycle {
    ignore_changes = all
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "functional_test_mno_email" {
  name        = "/operator-portal/functional-tests/test-mno-email"
  description = "Email address the functional tests expect the log upload invite to be delivered to"
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

resource "aws_ssm_parameter" "mno_email_bt" {
  name        = "/operator-portal/mno-emails/bt"
  description = "Email address for BT MNO operator"
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