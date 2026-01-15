variable "notify_api_key_parameter" {
  description = "SSM parameter name holding the GOV.UK Notify API key"
  type        = string
}

variable "environment" {
  description = "Environment (e.g. dev, staging, prod)."
  type        = string
}
