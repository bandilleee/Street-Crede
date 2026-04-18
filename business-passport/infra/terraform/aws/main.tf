terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── S3 ──────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "passport" {
  bucket = var.s3_bucket_name
}

resource "aws_s3_bucket_versioning" "passport" {
  bucket = aws_s3_bucket.passport.id
  versioning_configuration { status = "Enabled" }
}

# ── DynamoDB ─────────────────────────────────────────────────────────────────
resource "aws_dynamodb_table" "jobs" {
  name         = var.dynamodb_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"
  attribute { name = "job_id"; type = "S" }
}

# ── SNS ──────────────────────────────────────────────────────────────────────
resource "aws_sns_topic" "notifications" {
  name = "passport-notifications"
}

# ── Secrets Manager (placeholder) ────────────────────────────────────────────
resource "aws_secretsmanager_secret" "gcp_sa" {
  name        = var.gcp_sa_secret_name
  description = "GCP service account JSON for Cloud Run + Vertex AI auth"
}

# ── IAM: shared Lambda role ───────────────────────────────────────────────────
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { type = "Service"; identifiers = ["lambda.amazonaws.com"] }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "passport-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "lambda_perms" {
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow"; Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]; Resource = "*" },
      { Effect = "Allow"; Action = ["s3:GetObject", "s3:PutObject"]; Resource = "${aws_s3_bucket.passport.arn}/*" },
      { Effect = "Allow"; Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]; Resource = aws_dynamodb_table.jobs.arn },
      { Effect = "Allow"; Action = ["secretsmanager:GetSecretValue"]; Resource = aws_secretsmanager_secret.gcp_sa.arn },
      { Effect = "Allow"; Action = ["sns:Publish"]; Resource = aws_sns_topic.notifications.arn },
    ]
  })
}

# ── Lambda functions ──────────────────────────────────────────────────────────
locals {
  lambda_env = {
    S3_BUCKET          = var.s3_bucket_name
    DYNAMODB_TABLE     = var.dynamodb_table
    SNS_TOPIC_ARN      = aws_sns_topic.notifications.arn
    GCP_SA_SECRET_NAME = var.gcp_sa_secret_name
    CLOUD_RUN_URL      = var.cloud_run_url
    VERTEX_PROJECT     = var.vertex_project
    VERTEX_REGION      = var.vertex_region
    VERTEX_ENDPOINT_ID = var.vertex_endpoint_id
  }
  lambdas = {
    ingest       = "../../../aws/lambdas/ingest"
    presign      = "../../../aws/lambdas/presign"
    gcp_proxy    = "../../../aws/lambdas/gcp_proxy"
    scrape       = "../../../aws/lambdas/scrape"
    vertex_proxy = "../../../aws/lambdas/vertex_proxy"
    score        = "../../../aws/lambdas/score"
    passport     = "../../../aws/lambdas/passport"
    notify       = "../../../aws/lambdas/notify"
  }
}

data "archive_file" "lambda_zips" {
  for_each    = local.lambdas
  type        = "zip"
  source_dir  = each.value
  output_path = "${path.module}/.build/${each.key}.zip"
}

resource "aws_lambda_function" "fns" {
  for_each         = local.lambdas
  function_name    = "passport-${each.key}"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zips[each.key].output_path
  source_code_hash = data.archive_file.lambda_zips[each.key].output_base64sha256
  timeout          = 120
  memory_size      = 512
  environment { variables = local.lambda_env }
}

# ── Step Functions ────────────────────────────────────────────────────────────
data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { type = "Service"; identifiers = ["states.amazonaws.com"] }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "passport-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

resource "aws_iam_role_policy" "sfn_invoke" {
  role = aws_iam_role.sfn.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = [for fn in aws_lambda_function.fns : fn.arn]
    }]
  })
}

resource "aws_sfn_state_machine" "passport" {
  name     = "passport-pipeline"
  role_arn = aws_iam_role.sfn.arn
  type     = "EXPRESS"
  definition = templatefile("${path.root}/../../../statemachine/definition.asl.json", {
    PresignFunctionArn      = aws_lambda_function.fns["presign"].arn
    GcpProxyFunctionArn     = aws_lambda_function.fns["gcp_proxy"].arn
    ScrapeFunctionArn       = aws_lambda_function.fns["scrape"].arn
    VertexProxyFunctionArn  = aws_lambda_function.fns["vertex_proxy"].arn
    ScoreFunctionArn        = aws_lambda_function.fns["score"].arn
    PassportFunctionArn     = aws_lambda_function.fns["passport"].arn
    NotifyFunctionArn       = aws_lambda_function.fns["notify"].arn
    MarkFailedFunctionArn   = aws_lambda_function.fns["notify"].arn  # reuse notify as fallback
  })
}

# ── EventBridge: S3 → Step Functions ─────────────────────────────────────────
resource "aws_s3_bucket_notification" "jobs" {
  bucket      = aws_s3_bucket.passport.id
  eventbridge = true
}

resource "aws_iam_role" "eb" {
  name               = "passport-eb-role"
  assume_role_policy = data.aws_iam_policy_document.eb_assume.json
}

data "aws_iam_policy_document" "eb_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { type = "Service"; identifiers = ["events.amazonaws.com"] }
  }
}

resource "aws_iam_role_policy" "eb_sfn" {
  role = aws_iam_role.eb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow"; Action = ["states:StartExecution"]; Resource = aws_sfn_state_machine.passport.arn }]
  })
}

resource "aws_cloudwatch_event_rule" "s3_jobs" {
  name = "passport-s3-jobs-trigger"
  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [var.s3_bucket_name] }
      object = { key = [{ prefix = "jobs/" }] }
    }
  })
}

resource "aws_cloudwatch_event_target" "sfn" {
  rule     = aws_cloudwatch_event_rule.s3_jobs.name
  arn      = aws_sfn_state_machine.passport.arn
  role_arn = aws_iam_role.eb.arn
  input_transformer {
    input_paths    = { job_key = "$.detail.object.key" }
    input_template = "{\"job_id\": \"<job_key>\"}"
  }
}

# ── API Gateway ───────────────────────────────────────────────────────────────
resource "aws_apigatewayv2_api" "passport" {
  name          = "passport-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "ingest" {
  api_id                 = aws_apigatewayv2_api.passport.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.fns["ingest"].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "submit" {
  api_id    = aws_apigatewayv2_api.passport.id
  route_key = "POST /submit"
  target    = "integrations/${aws_apigatewayv2_integration.ingest.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.passport.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw_ingest" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fns["ingest"].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.passport.execution_arn}/*/*"
}
