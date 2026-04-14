"""
test_ingest_handler.py — testes unitários para src/ingestion/handler.py

Fluxo testado: payload → chunk → embeddings → OpenSearch index
Todas as dependências externas (boto3, OpenSearch, Bedrock) são mockadas.
"""
import json
import sys
import os
import importlib.util
from unittest.mock import MagicMock
import pytest

# ── Carrega src/ingestion/handler.py com nome único ───────────────────────────
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_spec = importlib.util.spec_from_file_location(
    "ingest_handler",
    os.path.join(_repo_root, "src", "ingestion", "handler.py"),
)
ingest_handler = importlib.util.module_from_spec(_spec)
sys.modules["ingest_handler"] = ingest_handler
_spec.loader.exec_module(ingest_handler)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_password_cache():
    """Reseta cache da senha do OpenSearch entre testes."""
    ingest_handler._opensearch_password = None
    yield
    ingest_handler._opensearch_password = None


@pytest.fixture(autouse=True)
def mock_ssm():
    """SSM sempre retorna senha de teste."""
    ingest_handler.ssm.get_parameter.return_value = {
        "Parameter": {"Value": "test-password"}
    }


@pytest.fixture
def mock_opensearch():
    """Mock do OpenSearchClient com bulk_index retornando contagem padrão."""
    instance = MagicMock()
    instance.bulk_index.return_value = 1
    ingest_handler.OpenSearchClient = MagicMock(return_value=instance)
    return instance


# ── Testes ────────────────────────────────────────────────────────────────────

def test_empty_text_returns_400(lambda_context):
    """Payload com text vazio deve retornar 400."""
    event = {"body": json.dumps({"text": "", "doc_id": "test-doc"})}
    response = ingest_handler.lambda_handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


def test_successful_ingest(lambda_context, mock_opensearch):
    """Payload válido deve retornar 200 com doc_id, chunks, indexed e status success."""
    text = " ".join(["mlops"] * 300)  # 300 palavras — cabe num único chunk (size=512)
    ingest_handler.get_embeddings = MagicMock(
        side_effect=lambda texts, model_id: [[0.1] * 1024] * len(texts)
    )
    mock_opensearch.bulk_index.return_value = 1

    event = {
        "body": json.dumps({
            "text": text,
            "doc_id": "test-doc-001",
            "title": "Test Document",
        })
    }
    response = ingest_handler.lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "success"
    assert body["doc_id"] == "test-doc-001"
    assert "chunks" in body
    assert "indexed" in body


def test_chunk_count_in_response(lambda_context, mock_opensearch):
    """O campo 'chunks' na resposta deve ser maior que zero para qualquer texto válido."""
    # 600 palavras com chunk_size=512 (default) produz 2 chunks
    text = " ".join([f"word{i}" for i in range(600)])
    ingest_handler.get_embeddings = MagicMock(
        side_effect=lambda texts, model_id: [[0.1] * 1024] * len(texts)
    )
    mock_opensearch.bulk_index.return_value = len(text.split()) // 512 + 1

    event = {
        "body": json.dumps({
            "text": text,
            "doc_id": "test-doc-002",
        })
    }
    response = ingest_handler.lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["chunks"] > 0
