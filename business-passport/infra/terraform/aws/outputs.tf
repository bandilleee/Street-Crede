output "api_gateway_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}

output "state_machine_arn" {
  value = aws_sfn_state_machine.passport.arn
}

output "s3_bucket" {
  value = aws_s3_bucket.passport.bucket
}

output "dynamodb_table" {
  value = aws_dynamodb_table.jobs.name
}

output "sns_topic_arn" {
  value = aws_sns_topic.notifications.arn
}
