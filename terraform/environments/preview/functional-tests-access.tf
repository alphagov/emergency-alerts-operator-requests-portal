locals {
  functional_tests_codebuild_role_arn = "arn:aws:iam::267739986477:role/eas-mno-portal-functional-tests-image-build-role"
}

data "aws_iam_policy_document" "functional_tests_access_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [local.functional_tests_codebuild_role_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = ["eas-mno-portal-preview-functional-tests-access"]
    }
  }
}

resource "aws_iam_role" "functional_tests_access" {
  name               = "mno-portal-functional-tests-access"
  assume_role_policy = data.aws_iam_policy_document.functional_tests_access_assume_role.json
}

data "aws_iam_policy_document" "functional_tests_access_permissions" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [module.lambda_log_upload.log_upload_lambda_arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
    ]
    resources = [
      module.lambda_log_upload.log_upload_tracking_table_arn,
      "arn:aws:dynamodb:${local.aws_region}:${data.aws_caller_identity.current.account_id}:table/operator-request-portal-log-invites",
    ]
  }

  statement {
    effect  = "Allow"
    actions = ["logs:FilterLogEvents"]
    resources = [
      "arn:aws:logs:${local.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/mno-portal-preview-log-upload-handler:*",
      "arn:aws:logs:${local.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/mno-portal-preview-lambda-log-download:*",
    ]
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${module.operator_request_portal_static_site.s3_bucket_name}"]
  }

  statement {
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:DeleteObject"]
    resources = [
      "arn:aws:s3:::${module.operator_request_portal_static_site.s3_bucket_name}/received/logs/*",
    ]
  }
}

resource "aws_iam_role_policy" "functional_tests_access_permissions" {
  name   = "functional-tests-access-permissions"
  role   = aws_iam_role.functional_tests_access.id
  policy = data.aws_iam_policy_document.functional_tests_access_permissions.json
}
