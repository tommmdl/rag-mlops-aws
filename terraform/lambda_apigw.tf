# ─── LAMBDA LAYER: dependências Python ───────────────────────────────────────

resource "null_resource" "build_layer" {
  triggers = {
    requirements = filemd5("${path.module}/../requirements.txt")
  }

  provisioner "local-exec" {
    command = <<EOT
      rm -rf /tmp/rag-layer && mkdir -p /tmp/rag-layer/python
      pip3 install -r ${path.module}/../requirements.txt \
        --target /tmp/rag-layer/python \
        --platform manylinux2014_x86_64 \
        --only-binary=:all: \
        --break-system-packages -q
      cd /tmp/rag-layer && zip -r ${path.module}/layer.zip python -x "*.pyc" -x "*/__pycache__/*"
    EOT
  }
}

resource "aws_lambda_layer_version" "deps" {
  filename            = "${path.module}/layer.zip"
  layer_name          = "${var.project_name}-deps"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = fileexists("${path.module}/layer.zip") ? filebase64sha256("${path.module}/layer.zip") : null

  depends_on = [null_resource.build_layer]
}

# ─── LAMBDA: ingestão de documentos ──────────────────────────────────────────

data "archive_file" "lambda_ingest" {
  type        = "zip"
  source_dir  = "${path.module}/../src/ingestion"
  output_path = "${path.module}/lambda_ingest.zip"
}

resource "aws_lambda_function" "ingest" {
  function_name    = "${var.project_name}-ingest-${var.environment}"
  filename         = data.archive_file.lambda_ingest.output_path
  source_code_hash = data.archive_file.lambda_ingest.output_base64sha256
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 300 # 5 min — ingestão pode demorar
  memory_size      = 512

  layers = [aws_lambda_layer_version.deps.arn]

  environment {
    variables = {
      OPENSEARCH_ENDPOINT    = "https://${aws_opensearch_domain.main.endpoint}"
      OPENSEARCH_INDEX       = "mlops-docs"
      OPENSEARCH_USER        = "admin"
      SSM_PASSWORD_PATH      = aws_ssm_parameter.opensearch_password.name
      BEDROCK_EMBEDDING_MODEL = var.bedrock_embedding_model
      CHUNK_SIZE             = tostring(var.chunk_size)
      CHUNK_OVERLAP          = tostring(var.chunk_overlap)
      S3_DOCS_BUCKET         = aws_s3_bucket.docs.bucket
      AWS_REGION_NAME        = var.aws_region
    }
  }

  tags = { Name = "${var.project_name}-ingest" }
}

resource "aws_cloudwatch_log_group" "ingest" {
  name              = "/aws/lambda/${aws_lambda_function.ingest.function_name}"
  retention_in_days = 7
}

# ─── LAMBDA: API RAG (query + geração) ───────────────────────────────────────

data "archive_file" "lambda_api" {
  type        = "zip"
  source_dir  = "${path.module}/../src/api"
  output_path = "${path.module}/lambda_api.zip"
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.project_name}-api-${var.environment}"
  filename         = data.archive_file.lambda_api.output_path
  source_code_hash = data.archive_file.lambda_api.output_base64sha256
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30
  memory_size      = 256

  layers = [aws_lambda_layer_version.deps.arn]

  environment {
    variables = {
      OPENSEARCH_ENDPOINT     = "https://${aws_opensearch_domain.main.endpoint}"
      OPENSEARCH_INDEX        = "mlops-docs"
      OPENSEARCH_USER         = "admin"
      SSM_PASSWORD_PATH       = aws_ssm_parameter.opensearch_password.name
      BEDROCK_EMBEDDING_MODEL = var.bedrock_embedding_model
      BEDROCK_LLM_MODEL       = var.bedrock_llm_model
      DYNAMODB_TABLE          = aws_dynamodb_table.chat_history.name
      TOP_K                   = tostring(var.top_k_results)
      AWS_REGION_NAME         = var.aws_region
    }
  }

  tags = { Name = "${var.project_name}-api" }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7
}

# ─── API GATEWAY ──────────────────────────────────────────────────────────────

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "api" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.api.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_integration" "ingest" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.ingest.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "query" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /query"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_route" "ingest" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /ingest"
  target    = "integrations/${aws_apigatewayv2_integration.ingest.id}"
}

resource "aws_lambda_permission" "api_gw_api" {
  statement_id  = "AllowAPIGatewayInvokeAPI"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_ingest" {
  statement_id  = "AllowAPIGatewayInvokeIngest"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
