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
          "arn:aws:s3:::${var.log_bucket_name}/logs/*"
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
      }
    ]
  })
}

# resource "aws_lambda_permission" "allow_eas_api_invoke" {
#   statement_id  = "AllowEASAPIInvoke"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.log_upload.function_name
#   principal     = "arn:aws:iam::${var.eas_preview_account_id}:role/eas-app-api-task-role"
# }

resource "aws_lambda_permission" "allow_eas_api_invoke_development" {
  statement_id  = "AllowEASAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.log_upload.function_name
  principal     = "071839617283"
}