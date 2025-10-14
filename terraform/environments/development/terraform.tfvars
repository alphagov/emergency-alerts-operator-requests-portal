environment  = "mno-portal-development"
project_name = "operator-request-portal"

infra_mgt_state_bucket = "eas-infra-mgt-tfstate"
infra_mgt_state_key    = "eas-mno-portal-development/account.tfstate"
infra_mgt_state_region = "eu-west-2"

download_link_expiry_days  = 30
upload_link_expiry_seconds = 604800  # 7 days

# HTML files to upload (can override defaults)
html_files_map = {}  # Empty means use module defaults

tags = {
  Team       = "Emergency Alerts"
}