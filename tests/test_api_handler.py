"""
test_api_handler.py — testes unitários para src/api/handler.py

Fluxo testado: pergunta → embed → kNN OpenSearch → prompt → Bedrock Claude → resposta
Todas as dependências externas (boto3, OpenSearch, Bedrock) são mockadas.
"""
import json
import sys
import os
import importlib.util
from unittest.mock import MagicMock, patch
import pytest

# ── Carrega src/api/handler.py com nome único para evitar conflito ─────────────
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_spec = importlib.util.spec_from_file_location(
    "api_handler",
    os.path.join(_repo_root, "src", "api", "handler.py"),
)
api_handler = importlib.util.module_from_spec(_spec)
sys.modules["api_handler"] = api_handler
_spec.loader.exec_module(api_handler)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bedrock_response(answer: str) -> dict:
    """Constrói resposta fake do bedrock.invoke_model."""
    body = MagicMock()
    body.read.return_value = json.dumps(
        {"content": [{"text": answer}]}
    ).encode()
    return {"body": body}


def _mock_opensearch(contexts: list):
    """Retorna instância mock do OpenSearchClient com semantic_search configurado."""
    instance = MagicMock()
    instance.semantic_search.return_value = contexts
    return instance


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_os_client():
    """Reseta o cache do OpenSearch client entre testes."""
    api_handler._os_client = None
    yield
    api_handler._os_client = None


@pytest.fixture(autouse=True)
def mock_ssm():
    """SSM sempre retorna senha de teste."""
    api_handler.ssm.get_parameter.return_value = {
        "Parameter": {"Value": "test-password"}
    }


# ── Testes ────────────────────────────────────────────────────────────────────

def test_health_check(lambda_context):
    """GET /health deve retornar 200 com status 'ok'."""
    event = {
        "requestContext": {"http": {"method": "GET"}},
        "rawPath": "/health",
    }
    response = api_handler.lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "ok"


def test_missing_question(lambda_context):
    """POST /query sem campo 'question' deve retornar 400."""
    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/query",
        "body": json.dumps({"session_id": "test"}),
    }
    response = api_handler.lambda_handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


def test_successful_query(lambda_context):
    """POST /query com question válida deve retornar 200 com answer, sources e contexts."""
    contexts = [
        {
            "text": "MLOps combines ML development with operations practices.",
            "metadata": {"title": "MLOps Guide"},
            "doc_id": "doc-001",
            "score": 0.95,
        }
    ]
    api_handler.get_embedding = MagicMock(return_value=[0.1] * 1024)
    api_handler.OpenSearchClient = MagicMock(return_value=_mock_opensearch(contexts))
    api_handler.bedrock.invoke_model.return_value = _bedrock_response(
        "MLOps is the practice of combining ML development and operations."
    )
    api_handler.dynamodb.Table.return_value.put_item = MagicMock()

    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/query",
        "body": json.dumps({"question": "What is MLOps?", "session_id": "test-session"}),
    }
    response = api_handler.lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "answer" in body
    assert "sources" in body
    assert "contexts" in body
    assert len(body["contexts"]) == 1


def test_empty_contexts(lambda_context):
    """Quando OpenSearch retorna lista vazia, resposta deve indicar que não há informações."""
    api_handler.get_embedding = MagicMock(return_value=[0.1] * 1024)
    api_handler.OpenSearchClient = MagicMock(return_value=_mock_opensearch([]))

    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/query",
        "body": json.dumps({"question": "Something very obscure?"}),
    }
    response = api_handler.lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["sources"] == []
    assert body["contexts"] == []
    assert "Não encontrei" in body["answer"]
