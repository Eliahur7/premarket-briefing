output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.briefing_bot.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function"
  value       = aws_lambda_function.briefing_bot.arn
}

output "schedule_rule_arn" {
  description = "ARN of the EventBridge schedule rule"
  value       = aws_cloudwatch_event_rule.daily_schedule.arn
}

output "log_group_name" {
  description = "CloudWatch log group for Lambda logs"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "invoke_command" {
  description = "AWS CLI command to manually trigger the Lambda"
  value       = "aws lambda invoke --function-name ${aws_lambda_function.briefing_bot.function_name} --region ${var.aws_region} /tmp/response.json && cat /tmp/response.json"
}
