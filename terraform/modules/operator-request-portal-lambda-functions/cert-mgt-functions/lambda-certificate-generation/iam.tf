resource "aws_iam_role" "certificate_generation_role" {
  name = "${var.environment}-certificate-generation-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "certificate_generation_policy" {
  name        = "${var.environment}-certificate-generation-policy"
  description = "Policy for the Certificate Generation Lambda"
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
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ],
        Resource = [
          "arn:aws:s3:::${var.csr_bucket_name}",
          "arn:aws:s3:::${var.csr_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ],
        Resource = [
          aws_dynamodb_table.certificates_table.arn,
          aws_dynamodb_table.mno_config_table.arn,
          aws_dynamodb_table.mno_contacts_table.arn
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "acm-pca:IssueCertificate",
          "acm-pca:GetCertificate"
        ],
        Resource = var.pca_arn
      },
      {
        Effect   = "Allow",
        Action   = ["lambda:InvokeFunction"],
        Resource = var.notify_lambda_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "certificate_generation_policy_attachment" {
  role       = aws_iam_role.certificate_generation_role.name
  policy_arn = aws_iam_policy.certificate_generation_policy.arn
}
