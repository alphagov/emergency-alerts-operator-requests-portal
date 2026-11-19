terraform {
  backend "s3" {
    bucket  = "eas-infra-mgt-tfstate"
    key     = "operator-requests/prod/terraform.tfstate"
    region  = "eu-west-2"
    encrypt = true
  }
}
