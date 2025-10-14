resource "aws_iam_role" "notify_lambda_role" {
  name = "NotifyServiceLambdaRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Effect = "Allow"
        Sid    = ""
      }
    ]
  })
}

resource "aws_iam_policy" "notify_lambda_policy" {
  name = "NotifyServiceLambdaPolicy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*",
        Effect   = "Allow"
      },
      {
        Action = [
          "ssm:GetParameter"
        ],
        Resource = "arn:${data.aws_partition.current.partition}:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter${var.notify_api_key_parameter}",
        Effect   = "Allow"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "notify_lambda_role_attach" {
  role       = aws_iam_role.notify_lambda_role.name
  policy_arn = aws_iam_policy.notify_lambda_policy.arn
}
