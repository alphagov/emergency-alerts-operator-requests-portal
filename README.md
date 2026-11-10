# emergency-alerts-operator-requests-portal

Repository containing Terraform infrastructure code for the Emergency Alerts Operator Request Portal - a secure platform for Mobile Network Operators (MNOs) to upload Cell Broadcast Centre (CBC) logs.

## Links

- [Confluence Docs](https://gds-ea.atlassian.net/wiki/spaces/EA/pages/)
- [Pipeline workflows](/.github)
  - [GitHub Actions interface](https://github.com/alphagov/emergency-alerts-operator-requests-portal/actions)

## Overview

The Operator Request Portal provides Mobile Network Operators with:

- **CBC (Cell Broadcast) log uploads** for compliance and auditing
- **Email notifications** via GOV.UK Notify

### Architecture

The portal uses a serverless architecture with:

- **CloudFront** distribution for global edge delivery
- **Lambda@Edge** functions for authentication and authorization
- **S3 bucket** for the static site and uploaded logs
- **Lambda functions** for upload invites and notifications
- **DynamoDB** tables for metadata and tracking
- **Route53** DNS management

## Pre-commit

- If `pre-commit` and `tflint` are not already installed on your machine, run
  `brew install pre-commit` and
  `brew install tflint`

- In this repository's folder, run
  `pre-commit install` and
  `pre-commit install-hooks`

## Testing changes

### Terraform

To test infrastructure changes locally:

```bash
cd terraform/environments/development

# Plan changes
gds aws emergency-alerts-mno-portal-development-admin -- terraform plan

# Apply changes (after review)
gds aws emergency-alerts-mno-portal-development-admin -- terraform apply
```

Merge the PR corresponding to those changes once testing is complete.

### CI/CD Deployment

The repository uses GitHub Actions with self-hosted runners for automated deployments:

- **Pull Requests**: Automatically runs `terraform plan` and comments results
- **Merges to main**: Automatically runs `terraform apply` to deploy changes

## Maintaining Terraform

### Updating provider versions

To update provider versions, run:

```bash
cd terraform/environments/development

terraform init -upgrade
terraform providers lock -platform=linux_amd64 -platform=darwin_amd64 -platform=darwin_arm64
```

Note that multiple platform options ensure the same provider dependency is pinned on Mac and Linux architectures for both local and GitHub Actions use.
