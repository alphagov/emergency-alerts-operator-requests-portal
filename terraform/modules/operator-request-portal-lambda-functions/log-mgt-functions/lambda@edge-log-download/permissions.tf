data "aws_caller_identity" "current" {}

resource "aws_lambda_permission" "allow_edge_invoke" {
  provider     = aws.us_east_1
  statement_id = "PermitEdgeInvoke"
  action       = "lambda:InvokeFunction"

  function_name = aws_lambda_function.download_edge.arn
  qualifier     = aws_lambda_function.download_edge.version

  principal  = "edgelambda.amazonaws.com"
  source_arn = "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/${var.cloudfront_distribution_id}"
}
