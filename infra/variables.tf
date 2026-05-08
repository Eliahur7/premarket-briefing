variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "premarket-briefing"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "schedule_expression" {
  description = "EventBridge cron schedule (UTC). 7:30 AM CT = 13:30 UTC (CDT) / 14:30 UTC (CST)"
  type        = string
  default     = "cron(30 13 ? * MON-FRI *)"
}

variable "watchlist" {
  description = "Comma-separated ticker watchlist"
  type        = string
  default     = "NVDA,AMD,GOOGL,MSFT,PLTR,AVGO,UBER,BAC"
}

variable "sector_etfs" {
  description = "Comma-separated sector ETFs to track"
  type        = string
  default     = "XLK,XLF,XLE,XLV,XLU,XLY,XLI,XLB,XLRE,XLC,XLP"
}

variable "ses_from_email" {
  description = "Verified SES sender email address"
  type        = string
}

variable "ses_to_email" {
  description = "Recipient email address"
  type        = string
}
