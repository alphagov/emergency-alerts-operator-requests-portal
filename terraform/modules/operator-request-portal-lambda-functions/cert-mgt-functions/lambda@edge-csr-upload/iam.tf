resource "aws_iam_role" "lambda_edge_role" {
  provider = aws.us_east_1
  name     = "csr-upload-lambda-edge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = ["lambda.amazonaws.com", "edgelambda.amazonaws.com"]
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_edge_cloudwatch" {
  provider = aws.us_east_1
  name     = "csr-upload-lambda-edge-cloudwatch"
  role     = aws_iam_role.lambda_edge_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_edge_dynamodb" {
  provider = aws.us_east_1
  name     = "csr-upload-lambda-edge-dynamodb"
  role     = aws_iam_role.lambda_edge_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ],
        Effect   = "Allow",
        Resource = aws_dynamodb_table.csr_uploads.arn
      }
    ]
  })
}
