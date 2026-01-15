data "aws_iam_policy_document" "edge_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"
      identifiers = [
        "lambda.amazonaws.com",
        "edgelambda.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role" "edge_role" {
  provider           = aws.us_east_1
  name               = "${var.environment}-log-edge-role"
  assume_role_policy = data.aws_iam_policy_document.edge_assume.json
}

resource "aws_iam_role_policy" "edge_policy" {
  provider = aws.us_east_1
  name     = "${var.environment}-log-edge-policy"
  role     = aws_iam_role.edge_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ],
        Resource = aws_dynamodb_table.log_upload_tracking.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "edge_basic_execution" {
  provider   = aws.us_east_1
  role       = aws_iam_role.edge_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
