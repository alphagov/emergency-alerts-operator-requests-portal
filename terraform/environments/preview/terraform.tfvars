environment  = "mno-portal-preview"
project_name = "operator-request-portal"

infra_mgt_state_bucket = "eas-infra-mgt-tfstate"
infra_mgt_state_key    = "eas-mno-portal-preview/account.tfstate"
infra_mgt_state_region = "eu-west-2"

gds_aws_profile            = "emergency-alerts-mno-portal-preview"
upload_link_expiry_seconds = 172800 # 2 days from the broadcast start

tags = {
  Team = "Emergency Alerts"
}
