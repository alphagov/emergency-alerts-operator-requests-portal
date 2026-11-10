# Remote state configuration
variable "infra_mgt_state_bucket" {
  description = "S3 bucket where infra-mgt stores its state"
  type        = string
  default     = "eas-infra-mgt-tfstate"
}

variable "infra_mgt_state_key" {
  description = "State key for infra-mgt account outputs"
  type        = string
  default     = "eas-mno-portal-development/account.tfstate"
}

variable "infra_mgt_state_region" {
  description = "Region where infra-mgt state bucket lives"
  type        = string
  default     = "eu-west-2"
}

variable "notify_api_key_parameter_name" {
  description = "SSM Parameter name for Notify API key"
  type        = string
}

variable "notify_api_key_parameter_arn" {
  description = "SSM Parameter ARN for Notify API key"
  type        = string
}
