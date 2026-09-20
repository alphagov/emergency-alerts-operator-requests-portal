data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "log_upload_role" {
  name               = "${var.environment}-log-upload-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

resource "aws_iam_role_policy" "log_upload_policy" {
  name = "${var.environment}-log-upload-policy"
  role = aws_iam_role.log_upload_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },

      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.log_bucket_name}/received/logs/*"
        ]
      },

      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:PutItem"
        ]
        Resource = aws_dynamodb_table.log_invite_tracking.arn
      },

      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:PutItem"
        ]
        Resource = aws_dynamodb_table.log_upload_tracking.arn
      },

      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = var.notify_lambda_arn
      },

      {
        Effect = "Allow"
        Action = ["ssm:GetParameter"]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/operator-portal/mno-emails/*",
          "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/operator-portal/mno-ids/*"
        ]
      }
    ]
  })
}

locals {
  eas_invoking_account_ids = {
    "mno-portal-development" = "071839617283"             # eas-development
    "mno-portal-preview"     = var.eas_preview_account_id # eas-preview
  }
}

resource "aws_lambda_permission" "allow_eas_api_invoke" {
  count         = contains(keys(local.eas_invoking_account_ids), var.environment) ? 1 : 0
  statement_id  = "AllowEASAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.log_upload.function_name
  principal     = local.eas_invoking_account_ids[var.environment]
}


moved {
  from = aws_lambda_permission.allow_eas_api_invoke_development
  to   = aws_lambda_permission.allow_eas_api_invoke[0]
}
