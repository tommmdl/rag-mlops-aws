.PHONY: help up down ingest query status logs clean

AWS_PROFILE ?= default
AWS_REGION  ?= us-east-1

help: ## Mostra os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── INFRA ────────────────────────────────────────────────────────────────────

build-layer: ## Compila o Lambda Layer (cross-platform — Windows/Mac/Linux)
	@echo "\n📦 Compilando Lambda Layer...\n"
	python3 scripts/build_layer.py

up: build-layer ## Provisiona toda a infra na AWS (OpenSearch + Lambda + API GW + S3)
	@echo "\n🚀 Provisionando infra RAG MLOps na AWS...\n"
	cd terraform && terraform init -upgrade && terraform apply -auto-approve
	@echo "\n✅ Infra provisionada! Endpoints disponíveis:\n"
	cd terraform && terraform output

down: ## Destroi TODA a infra (custo zero após isso)
	@echo "\n💣 Destruindo infra RAG MLOps...\n"
	cd terraform && terraform destroy -auto-approve
	@echo "\n✅ Infra destruída. Custo zerado.\n"

status: ## Mostra o estado atual da infra
	cd terraform && terraform show | grep -E "(id|arn|endpoint|status)" | head -30

# ─── DADOS ────────────────────────────────────────────────────────────────────

ingest: ## Faz ingestão dos docs MLOps no OpenSearch (roda após 'make up')
	@echo "\n📚 Iniciando ingestão de documentos MLOps...\n"
	@API_URL=$$(cd terraform && terraform output -raw api_gateway_url) && \
	python3 scripts/ingest.py --api-url $$API_URL --docs-dir docs/
	@echo "\n✅ Ingestão concluída!\n"

ingest-local: ## Testa ingestão localmente (sem AWS)
	@echo "\n📚 Ingestão local (modo teste)...\n"
	python3 scripts/ingest.py --local --docs-dir docs/

# ─── USO ──────────────────────────────────────────────────────────────────────

query: ## Faz uma query de teste no sistema RAG
	@API_URL=$$(cd terraform && terraform output -raw api_gateway_url) && \
	python3 scripts/query.py --api-url $$API_URL \
		--question "What are the key principles of MLOps?"

demo: ## Abre o Streamlit (interface visual para demo/portfólio)
	@API_URL=$$(cd terraform && terraform output -raw api_gateway_url 2>/dev/null || echo "http://localhost:8000") && \
	RAG_API_URL=$$API_URL streamlit run streamlit/app.py

# ─── LOGS & DEBUG ─────────────────────────────────────────────────────────────

logs-ingest: ## CloudWatch logs do Lambda de ingestão (últimas 50 linhas)
	aws logs tail /aws/lambda/rag-mlops-ingest \
		--follow --format short --profile $(AWS_PROFILE) --region $(AWS_REGION)

logs-api: ## CloudWatch logs do Lambda da API RAG
	aws logs tail /aws/lambda/rag-mlops-api \
		--follow --format short --profile $(AWS_PROFILE) --region $(AWS_REGION)

# ─── DEV ──────────────────────────────────────────────────────────────────────

install: ## Instala dependências Python
	pip3 install -r requirements.txt --break-system-packages

lint: ## Roda ruff no código Python
	ruff check src/ scripts/ streamlit/

clean: ## Remove arquivos temporários e cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".terraform.lock.hcl" -delete 2>/dev/null || true
	@echo "✅ Cache limpo"
