removed {
  from = aws_dynamodb_table.log_upload_tracking

  lifecycle {
    destroy = false
  }
}
