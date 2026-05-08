terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to use S3 backend for team/production use
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "premarket-briefing/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

# ── IAM Role for Lambda ────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["ses:SendEmail", "ses:SendRawEmail"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/*"
      }
    ]
  })
}

# ── Lambda Function ────────────────────────────────────────────────────────────

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../"
  output_path = "${path.module}/lambda_package.zip"

  excludes = [
    ".git",
    ".venv",
    "infra",
    "tests",
    "__pycache__",
    "*.pyc",
    ".env",
  ]
}

resource "aws_lambda_function" "briefing_bot" {
  function_name    = var.project_name
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  role             = aws_iam_role.lambda_role.arn
  handler          = "src.orchestrator.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120
  memory_size      = 512

  environment {
    variables = {
      WATCHLIST      = var.watchlist
      SECTOR_ETFS    = var.sector_etfs
      SES_FROM_EMAIL = var.ses_from_email
      SES_TO_EMAIL   = var.ses_to_email
      AWS_REGION_VAR = var.aws_region
      DRY_RUN        = "false"
      # Sensitive vars loaded from SSM at runtime — see src/orchestrator.py
    }
  }

  tags = {
    Project = var.project_name
    Env     = var.environment
  }
}

# ── CloudWatch Log Group ───────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 14
}

# ── EventBridge Schedule (cron) ───────────────────────────────────────────────

resource "aws_cloudwatch_event_rule" "daily_schedule" {
  name                = "${var.project_name}-schedule"
  description         = "Trigger pre-market briefing at 7:30 AM CT on weekdays"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_schedule.name
  target_id = "BriefingLambda"
  arn       = aws_lambda_function.briefing_bot.arn
}

resource "aws_lambda_permission" "eventbridge_invoke" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.briefing_bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_schedule.arn
}

# ── SSM Parameters (create manually or via CLI, Terraform just references) ────
# aws ssm put-parameter --name /premarket-briefing/ANTHROPIC_API_KEY \
#   --value "sk-ant-..." --type SecureString
# aws ssm put-parameter --name /premarket-briefing/NEWS_API_KEY \
#   --value "your-key" --type SecureString
