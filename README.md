# RAG MLOps Assistant

**English** · [Português](README.pt-BR.md)

A question-answering service about MLOps, built on AWS managed services: Bedrock for embeddings and generation, OpenSearch for kNN retrieval, Lambda and API Gateway for serving, and Terraform for the whole stack. The goal is a retrieval-augmented generation (RAG) stack that can be created and destroyed on demand at near-zero cost.

[![CI](https://github.com/tommmdl/rag-mlops-aws/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/tommmdl/rag-mlops-aws/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Terraform](https://img.shields.io/badge/terraform-≥1.6-purple.svg)](https://terraform.io)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              INGESTION PIPELINE (offline)           │
│                                                     │
│  S3 docs → Lambda ingest → Bedrock Titan V2 →       │
│                          OpenSearch (kNN index)     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              INFERENCE PIPELINE (online)            │
│                                                     │
│  User → API Gateway → Lambda RAG                    │
│                │                                    │
│                ├── Bedrock Titan (embed query)      │
│                ├── OpenSearch kNN (retrieve top-k)  │
│                └── Bedrock Claude 3 Haiku (answer)  │
│                                                     │
│  DynamoDB ← chat history                            │
└─────────────────────────────────────────────────────┘
```

The embedding and generation models are Terraform variables (`bedrock_embedding_model`, `bedrock_llm_model`). The IAM policy in `terraform/storage_iam.tf` grants access to those two model ARNs only, so changing a model means updating both.

## Stack and estimated cost

| Service | Role | Estimated cost |
|---------|------|----------------|
| OpenSearch t3.small | Vector store (kNN, HNSW) | Free tier for 12 months |
| Bedrock Titan Embeddings V2 | Embeddings | ~$0.10 per ingestion |
| Bedrock Claude 3 Haiku | Answer generation | ~$0.15/month for 500 queries |
| Lambda | Ingestion and RAG API | Free tier |
| API Gateway | HTTP endpoint | Free tier |
| S3 | Source documents | Free tier |
| DynamoDB | Chat history | Free tier |
| **Estimated total** | | **~$0–0.30/month** |

These are estimates from public pricing, not measured bills. A $10/month AWS Budget (`terraform/budget.tf`) alerts at 50% forecast and at 80% and 100% actual spend; the alert address comes from `alert_email` in `terraform.tfvars`.

> ⚠️ OpenSearch uses free-tier hours even when idle. Run `make down` when you are done.

## Prerequisites

```bash
aws configure          # AWS CLI with credentials
terraform --version    # Terraform >= 1.6
python3 --version      # Python 3.12+
make install           # Python dependencies
```

## Usage cycle

```bash
make up        # 1. provision the stack (terraform apply)
make ingest    # 2. upload and ingest the MLOps documents
make query     # 3. run a test query
make demo      # 4. open the Streamlit UI
make down      # 5. destroy everything (terraform destroy)
```

## Commands

```bash
make help          # list all commands
make build-layer   # build the shared Lambda layer
make up            # terraform apply
make down          # terraform destroy
make status        # current state of the stack
make ingest        # ingest docs (after make up)
make ingest-local  # test ingestion locally, without AWS
make query         # test query
make demo          # Streamlit UI
make logs-api      # tail the API Lambda logs in CloudWatch
make logs-ingest   # tail the ingestion Lambda logs
make install       # install Python dependencies
make lint          # ruff
make clean         # remove caches
```

## Adding documents

Put `.md`, `.txt` or `.rst` files in `docs/` and run `make ingest`. To ingest one file:

```bash
python3 scripts/ingest.py --api-url <URL> --file docs/my-doc.md
```

## CI

[`ci.yml`](.github/workflows/ci.yml) runs on every push and pull request to `master`:

- unit tests with pytest, ruff lint, and local chunking and ingestion checks with no AWS calls;
- `terraform fmt -check`, `init` without a backend and `validate`.

The workflow also defines a deploy job (OIDC credentials, plan, apply, ingestion, health check) behind a protected `production` environment. It is gated on `main` while this repository uses `master`, so it has not run: CI validates the code and the Terraform, and deployment is manual with `make up`.

## Repository layout

```
rag-mlops-aws/
├── Makefile                     # main commands
├── requirements.txt             # Python dependencies
├── terraform/
│   ├── main.tf                  # provider and backend
│   ├── variables.tf             # configurable variables
│   ├── opensearch.tf            # OpenSearch t3.small
│   ├── storage_iam.tf           # S3, DynamoDB, IAM role
│   ├── lambda_apigw.tf          # Lambda and API Gateway
│   ├── budget.tf                # monthly cost alert
│   └── outputs.tf               # endpoints and ARNs
├── src/
│   ├── ingestion/
│   │   ├── handler.py           # ingestion Lambda
│   │   └── chunker.py           # document chunking
│   ├── layers/shared/
│   │   ├── embedder.py          # Bedrock Titan embeddings
│   │   └── opensearch_client.py # OpenSearch client
│   └── api/
│       └── handler.py           # RAG Lambda (retrieval and generation)
├── tests/                       # unit tests (pytest)
├── scripts/
│   ├── build_layer.py           # builds the shared Lambda layer
│   ├── ingest.py                # ingestion CLI
│   └── query.py                 # query CLI with an interactive mode
├── streamlit/
│   └── app.py                   # demo UI
└── docs/                        # knowledge base for ingestion
```

## What it covers

- **RAG** end to end: chunking, embeddings, kNN retrieval and grounded generation.
- **Vector search** with HNSW in OpenSearch.
- **Serverless inference** with on-demand Bedrock, no GPUs to manage.
- **Infrastructure as code** for the whole stack, built to be applied and destroyed repeatedly.
- **FinOps**: free-tier sizing, a budget alert and a destroy-by-default usage cycle.

## Author

Rafael Santiago Silva · [GitHub](https://github.com/tommmdl) · [LinkedIn](https://www.linkedin.com/in/rafael-santiago-silva-68420759/)

## License

MIT. See [LICENSE](LICENSE).
