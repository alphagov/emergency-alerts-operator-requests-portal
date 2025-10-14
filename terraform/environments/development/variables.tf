variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "infra_mgt_state_bucket" {
  description = "S3 bucket where infra-mgt stores its state"
  type        = string
}

variable "infra_mgt_state_key" {
  description = "State key for infra-mgt account outputs"
  type        = string
}

variable "infra_mgt_state_region" {
  description = "Region where infra-mgt state bucket lives"
  type        = string
}

variable "download_link_expiry_days" {
  description = "Number of days download links remain valid"
  type        = number
}

variable "upload_link_expiry_seconds" {
  description = "Number of seconds upload links remain valid"
  type        = number
}

variable "html_files_map" {
  description = "Map of HTML files to upload to static site"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}