data "aws_iam_policy_document" "edge_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com", "edgelambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "edge_role" {
  provider           = aws.us_east_1
  name               = "${var.environment}-download-edge-role"
  assume_role_policy = data.aws_iam_policy_document.edge_assume.json
}

resource "aws_iam_role_policy" "edge_policy" {
  provider = aws.us_east_1
  name     = "${var.environment}-download-edge-policy"
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
        Resource = "arn:aws:dynamodb:${var.dynamodb_region}:*:table/${var.download_tracking_table}"
      },

      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "basic_exec" {
  provider   = aws.us_east_1
  role       = aws_iam_role.edge_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_permission" "allow_replicator" {
  provider      = aws.us_east_1
  statement_id  = "AllowReplicatorGetFunction"
  action        = "lambda:GetFunction"
  function_name = aws_lambda_function.download_edge.function_name
  principal     = "replicator.lambda.amazonaws.com"
}

resource "aws_lambda_permission" "allow_cf_invoke" {
  provider      = aws.us_east_1
  statement_id  = "AllowEdgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.download_edge.function_name
  principal     = "edgelambda.amazonaws.com"
  source_arn    = var.cloudfront_distribution_arn
}
