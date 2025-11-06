variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "operator-request-portal"
}

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

# Application-specific configuration
variable "download_link_expiry_days" {
  description = "Number of days download links remain valid"
  type        = number
  default     = 30
}

variable "upload_link_expiry_seconds" {
  description = "Number of seconds upload links remain valid"
  type        = number
  default     = 604800 # 7 days
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}