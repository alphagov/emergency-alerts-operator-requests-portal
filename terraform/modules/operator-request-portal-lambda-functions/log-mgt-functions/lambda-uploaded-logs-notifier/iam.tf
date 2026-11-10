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

resource "aws_iam_role" "lambda_role" {
  name               = "${var.environment}-uploaded-logs-notifier-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.environment}-uploaded-logs-notifier-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.environment}-uploaded-logs-notifier:*"
      },
      {
        Effect   = "Allow",
        Action   = ["dynamodb:GetItem"],
        Resource = "arn:aws:dynamodb:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:table/${var.log_invite_tracking_table}"
      },
      {
        Effect   = "Allow",
        Action   = ["dynamodb:UpdateItem"],
        Resource = "arn:aws:dynamodb:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:table/${var.log_upload_tracking_table}"
      },
      {
        Effect   = "Allow",
        Action   = ["lambda:InvokeFunction"],
        Resource = var.notify_lambda_arn
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:GetObjectMetadata",
          "s3:HeadObject",
          "s3:ListBucket"
        ],
        Resource = [
          "arn:aws:s3:::${var.log_bucket}",
          "arn:aws:s3:::${var.log_bucket}/*"
        ]
      }
    ]
  })
}
