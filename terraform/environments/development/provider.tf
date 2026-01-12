terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.14.1"
    }
  }
}

provider "aws" {
  region              = "eu-west-2"
  allowed_account_ids = ["435684131547"]

  default_tags {
    tags = merge(
      var.tags,
      {
        Environment = var.environment
        Project     = var.project_name
        ManagedBy   = "Terraform"
        Repository  = "operator-requests"
      }
    )
  }
}

provider "aws" {
  alias               = "us_east_1"
  region              = "us-east-1"
  allowed_account_ids = ["435684131547"]

  default_tags {
    tags = merge(
      var.tags,
      {
        Environment = var.environment
        Project     = var.project_name
        ManagedBy   = "Terraform"
        Repository  = "operator-requests"
      }
    )
  }
}
