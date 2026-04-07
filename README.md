# RAG MLOps Assistant 🤖

Sistema de perguntas e respostas sobre MLOps construído 100% na AWS.
Projeto de portfólio demonstrando a combinação de **MLOps + FinOps + Cloud Engineering**.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Terraform](https://img.shields.io/badge/terraform-≥1.6-purple.svg)](https://terraform.io)
[![AWS](https://img.shields.io/badge/cloud-AWS-orange.svg)](https://aws.amazon.com)

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│              PIPELINE DE INGESTÃO (offline)          │
│                                                     │
│  S3 Docs → Lambda Ingest → Bedrock Titan V2 →       │
│                         OpenSearch (kNN index)       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              PIPELINE DE INFERÊNCIA (online)         │
│                                                     │
│  Usuário → API Gateway → Lambda RAG                 │
│                │                                    │
│                ├── Bedrock Titan (embed query)       │
│                ├── OpenSearch kNN (retrieve top-k)   │
│                └── Bedrock Claude 3 Haiku (gerar)   │
│                                                     │
│  DynamoDB ← histórico de chat                       │
└─────────────────────────────────────────────────────┘
```

## Stack

| Serviço | Uso | Custo estimado |
|---------|-----|----------------|
| OpenSearch t3.small | Vector store (kNN) | Free tier 12 meses |
| Bedrock Titan Embeddings V2 | Geração de embeddings | ~$0.10 (ingestão) |
| Bedrock Claude 3 Haiku | Geração de respostas | ~$0.15/mês (500 queries) |
| Lambda | Ingestão + API RAG | Free tier |
| API Gateway | HTTP endpoint | Free tier |
| S3 | Armazenamento de docs | Free tier |
| DynamoDB | Histórico de chat | Free tier |
| **Total estimado** | | **~$0–$0.30/mês** |

> ⚠️ O OpenSearch consome horas do free tier mesmo parado. Use `make down` quando não estiver usando.

## Pré-requisitos

```bash
# AWS CLI configurado
aws configure

# Terraform >= 1.6
terraform --version

# Python 3.12+
python3 --version

# Dependências Python
make install
```

## Ciclo de uso (portfólio)

```bash
# 1. Provisiona toda a infra na AWS
make up

# 2. Faz upload e ingestão dos documentos MLOps
make ingest

# 3. Testa uma query
make query

# 4. Abre interface Streamlit para demo/gravação
make demo

# 5. Destroi tudo — custo zerado
make down
```

## Comandos disponíveis

```bash
make help       # lista todos os comandos
make up         # terraform apply — sobe infra
make down       # terraform destroy — destrói tudo
make status     # estado atual da infra
make ingest     # ingestão de docs (após make up)
make ingest-local # testa ingestão localmente (sem AWS)
make query      # query de teste
make demo       # abre Streamlit
make logs-api   # CloudWatch logs da API em tempo real
make logs-ingest # CloudWatch logs da ingestão
make install    # instala dependências Python
make lint       # ruff no código
make clean      # limpa cache
```

## Adicionando documentos

Coloque arquivos `.md`, `.txt` ou `.rst` na pasta `docs/` e rode:

```bash
make ingest
```

Para ingerir um arquivo específico:
```bash
python3 scripts/ingest.py --api-url <URL> --file docs/meu-doc.md
```

## Estrutura do repositório

```
rag-mlops-aws/
├── Makefile                    # comandos principais
├── requirements.txt            # dependências Python
├── terraform/
│   ├── main.tf                 # provider + backend
│   ├── variables.tf            # variáveis configuráveis
│   ├── opensearch.tf           # OpenSearch t3.small (free tier)
│   ├── storage_iam.tf          # S3, DynamoDB, IAM Role
│   ├── lambda_apigw.tf         # Lambda + API Gateway
│   └── outputs.tf              # endpoints e ARNs
├── src/
│   ├── ingestion/
│   │   ├── handler.py          # Lambda ingestão
│   │   ├── chunker.py          # document chunking
│   │   ├── embedder.py         # Bedrock Titan embeddings
│   │   └── opensearch_client.py # cliente OpenSearch
│   └── api/
│       └── handler.py          # Lambda RAG (query + geração)
├── scripts/
│   ├── ingest.py               # CLI ingestão
│   └── query.py                # CLI queries + modo interativo
├── streamlit/
│   └── app.py                  # interface visual (portfólio)
└── docs/
    └── mlops-fundamentals.md   # base de conhecimento inicial
```

## Conceitos demonstrados

- **RAG** (Retrieval-Augmented Generation) — arquitetura completa end-to-end
- **Vector Search** — kNN com HNSW no OpenSearch
- **Serverless ML inference** — Bedrock on-demand, sem gestão de GPU
- **IaC** — Terraform para toda a stack, destroy/apply seguro
- **FinOps** — custo controlado, free tier maximizado, ciclo destroy/apply
- **CI/CD ready** — estrutura modular para GitHub Actions

## Autor

Rafael — Cloud Operator Sênior | FinOps | MLOps  
[GitHub](https://github.com/tommmdl) | [LinkedIn](https://linkedin.com)
