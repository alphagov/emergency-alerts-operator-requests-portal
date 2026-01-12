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
  name               = "${var.environment}-notify-download-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.environment}-notify-download-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem"
        ],
        Resource = aws_dynamodb_table.download_tracking.arn
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

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
