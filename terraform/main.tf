terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── DynamoDB Tables ─────────────────────────────────────────

resource "aws_dynamodb_table" "live_games" {
  name         = "${var.project}-live-games"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "gameId"

  attribute {
    name = "gameId"
    type = "S"
  }

  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_dynamodb_table" "player_stats" {
  name         = "${var.project}-player-stats"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "playerId"

  attribute {
    name = "playerId"
    type = "S"
  }

  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_dynamodb_table" "ai_insights" {
  name         = "${var.project}-ai-insights"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sport"
  range_key    = "timestamp"

  attribute {
    name = "sport"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_dynamodb_table" "betting_odds" {
  name         = "${var.project}-betting-odds"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "oddsId"

  attribute {
    name = "oddsId"
    type = "S"
  }

  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_dynamodb_table" "team_stats" {
  name         = "${var.project}-team-stats"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "teamId"

  attribute {
    name = "teamId"
    type = "S"
  }

  tags = { Project = var.project, Environment = var.environment }
}

# ── Kinesis Stream ───────────────────────────────────────────

resource "aws_kinesis_stream" "live_stream" {
  name             = "${var.project}-live-stream"
  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  tags = { Project = var.project, Environment = var.environment }
}

# ── Secrets Manager ──────────────────────────────────────────

resource "aws_secretsmanager_secret" "api_keys" {
  name = "${var.project}/${var.environment}/api-keys"
  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    sportradar_master_key = var.sportradar_api_key
    odds_api_key          = var.odds_api_key
    groq_api_key          = var.groq_api_key
  })
}

# ── IAM Role for Lambda ───────────────────────────────────────

resource "aws_iam_role" "lambda_role" {
  name = "${var.project}-lambda-role"

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
  name = "${var.project}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Scan",
          "dynamodb:Query", "dynamodb:UpdateItem"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:${var.account_id}:table/${var.project}-*"
      },
      {
        Effect   = "Allow"
        Action   = ["kinesis:PutRecord", "kinesis:PutRecords"]
        Resource = aws_kinesis_stream.live_stream.arn
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.api_keys.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# ── Lambda Functions ──────────────────────────────────────────

resource "aws_lambda_function" "nba_fetcher" {
  filename         = "../backend/lambdas/nba/lambda.zip"
  function_name    = "${var.project}-nba-fetcher"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      PROJECT = var.project
    }
  }

  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_lambda_function" "nfl_fetcher" {
  filename         = "../backend/lambdas/nfl/lambda.zip"
  function_name    = "${var.project}-nfl-fetcher"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30

  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_lambda_function" "mlb_fetcher" {
  filename         = "../backend/lambdas/mlb/lambda.zip"
  function_name    = "${var.project}-mlb-fetcher"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30

  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_lambda_function" "odds_fetcher" {
  filename         = "../backend/lambdas/odds/lambda.zip"
  function_name    = "${var.project}-odds-fetcher"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      GROQ_API_KEY = var.groq_api_key
    }
  }

  tags = { Project = var.project, Environment = var.environment }
}

resource "aws_lambda_function" "ai_analysis" {
  filename         = "../backend/lambdas/ai_analysis/lambda.zip"
  function_name    = "${var.project}-ai-analysis"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 60

  environment {
    variables = {
      GROQ_API_KEY = var.groq_api_key
    }
  }

  tags = { Project = var.project, Environment = var.environment }
}

# ── EventBridge Schedules ─────────────────────────────────────

resource "aws_cloudwatch_event_rule" "nba_schedule" {
  name                = "${var.project}-nba-schedule"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "nba_target" {
  rule = aws_cloudwatch_event_rule.nba_schedule.name
  arn  = aws_lambda_function.nba_fetcher.arn
}

resource "aws_lambda_permission" "nba_eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.nba_fetcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nba_schedule.arn
}

resource "aws_cloudwatch_event_rule" "ai_schedule" {
  name                = "${var.project}-ai-schedule"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "ai_target" {
  rule = aws_cloudwatch_event_rule.ai_schedule.name
  arn  = aws_lambda_function.ai_analysis.arn
}

resource "aws_lambda_permission" "ai_eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ai_analysis.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ai_schedule.arn
}

# ── API Gateway ───────────────────────────────────────────────

resource "aws_apigatewayv2_api" "api" {
  name          = "${var.project}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET"]
    allow_headers = ["Content-Type"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

# ── S3 Frontend Bucket ────────────────────────────────────────

resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project}-frontend-${var.account_id}"
  tags   = { Project = var.project, Environment = var.environment }
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document { suffix = "index.html" }
  error_document { key    = "index.html" }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })
}

# ── CloudFront ────────────────────────────────────────────────

resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name = aws_s3_bucket_website_configuration.frontend.website_endpoint
    origin_id   = "S3Origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
    }
  }

  enabled             = true
  default_root_object = "index.html"
  comment             = "${var.project} frontend"

  default_cache_behavior {
    target_origin_id       = "S3Origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = { Project = var.project, Environment = var.environment }
}
