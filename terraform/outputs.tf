output "api_gateway_url" {
  description = "URL base da API RAG"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "opensearch_endpoint" {
  description = "Endpoint do OpenSearch"
  value       = "https://${aws_opensearch_domain.main.endpoint}"
}

output "s3_docs_bucket" {
  description = "Bucket S3 para documentos"
  value       = aws_s3_bucket.docs.bucket
}

output "query_endpoint" {
  description = "Endpoint para queries RAG"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/query"
}

output "ingest_endpoint" {
  description = "Endpoint para ingestão de documentos"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/ingest"
}

output "health_endpoint" {
  description = "Endpoint de health check"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/health"
}

output "cost_alert" {
  description = "Lembrete de custo"
  value       = "⚠️  OpenSearch t3.small roda 24h. Execute 'make down' quando não estiver usando!"
}

output "budget_alert" {
  description = "Resumo do AWS Budget configurado"
  value       = "Budget mensal: ${aws_budgets_budget.monthly.limit_amount} USD — alertas em 50% (forecast), 80% e 100% (actual)"
}
