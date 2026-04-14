"""
conftest.py — fixtures e configuração global para todos os testes.

Responsabilidades:
  - Mock de dependências pesadas (boto3, opensearch-py) antes de qualquer import
  - Variáveis de ambiente Lambda para os handlers
  - Fixtures reutilizáveis: sample_text, lambda_context
"""
import os
import sys
from unittest.mock import MagicMock

# ── Variáveis de ambiente exigidas pelos handlers ────────────────────────────
os.environ.setdefault("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
os.environ.setdefault("BEDROCK_LLM_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")
os.environ.setdefault("OPENSEARCH_ENDPOINT", "https://test.opensearch.example.com")
os.environ.setdefault("OPENSEARCH_INDEX", "test-index")
os.environ.setdefault("OPENSEARCH_USER", "admin")
os.environ.setdefault("SSM_PASSWORD_PATH", "/test/opensearch/password")
os.environ.setdefault("DYNAMODB_TABLE", "test-table")
os.environ.setdefault("TOP_K", "5")
os.environ.setdefault("CHUNK_SIZE", "512")
os.environ.setdefault("CHUNK_OVERLAP", "50")

# ── Mock de dependências externas pesadas ────────────────────────────────────
# Precisam estar em sys.modules antes que qualquer módulo os importe.
sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("opensearchpy", MagicMock())
sys.modules.setdefault("opensearchpy.helpers", MagicMock())
sys.modules.setdefault("requests_aws4auth", MagicMock())

# ── sys.path — permite imports dos módulos do projeto ────────────────────────
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_layers_path = os.path.join(_repo_root, "src", "layers")
_ingestion_path = os.path.join(_repo_root, "src", "ingestion")

for _p in (_layers_path, _ingestion_path):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Fixtures ──────────────────────────────────────────────────────────────────
import pytest


@pytest.fixture
def sample_text():
    """Texto MLOps de ~200 palavras para reuso entre testes."""
    return (
        "MLOps is the practice of combining machine learning development and operations. "
        "It encompasses the end-to-end lifecycle of machine learning models from data ingestion "
        "through model deployment and monitoring. Feature engineering transforms raw data into "
        "meaningful inputs for algorithms. Model training requires careful hyperparameter tuning "
        "and validation strategies. Continuous integration and deployment pipelines automate "
        "the testing and release of new model versions. Data drift detection monitors for "
        "distribution changes between training and production data. Model versioning allows "
        "teams to track experiments and reproduce results reliably. Containerization with Docker "
        "and orchestration with Kubernetes enables scalable model serving infrastructure. "
        "Automated retraining pipelines ensure models stay performant as data evolves. "
        "Observability tools provide insights into prediction quality and system health. "
        "A/B testing frameworks enable controlled rollout of new model versions to production. "
        "Infrastructure as code tools like Terraform manage cloud resources consistently. "
        "Monitoring dashboards track latency throughput and error rates for deployed models. "
        "Model explainability techniques help teams understand and audit predictions. "
        "Data lineage tracking ensures reproducibility and compliance across pipelines. "
        "Experiment tracking tools like MLflow capture metrics parameters and artifacts. "
        "Model registries centralize the storage and lifecycle management of trained models. "
        "Automated testing of data quality prevents corrupt data from entering training pipelines. "
        "Collaboration between data scientists engineers and operations teams drives successful MLOps."
    )


@pytest.fixture
def lambda_context():
    """Mock do objeto context do AWS Lambda."""
    ctx = MagicMock()
    ctx.function_name = "test-lambda"
    ctx.aws_request_id = "test-request-123"
    ctx.memory_limit_in_mb = 256
    return ctx
