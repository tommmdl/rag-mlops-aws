"""
Lambda API RAG — RAG MLOps AWS
Fluxo: pergunta → embed → kNN OpenSearch → prompt → Bedrock Claude → resposta
"""
import json
import os
import boto3
import logging
from datetime import datetime, timezone
from typing import Any

from shared.embedder import get_embedding
from shared.opensearch_client import OpenSearchClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm      = boto3.client("ssm")
bedrock  = boto3.client("bedrock-runtime")
dynamodb = boto3.resource("dynamodb")

_os_client: OpenSearchClient | None = None  # reutiliza entre invocações


def _get_opensearch_password() -> str:
    resp = ssm.get_parameter(
        Name=os.environ["SSM_PASSWORD_PATH"],
        WithDecryption=True,
    )
    return resp["Parameter"]["Value"]


def _get_os_client() -> OpenSearchClient:
    global _os_client
    if _os_client is None:
        _os_client = OpenSearchClient(
            endpoint=os.environ["OPENSEARCH_ENDPOINT"],
            index=os.environ["OPENSEARCH_INDEX"],
            username=os.environ["OPENSEARCH_USER"],
            password=_get_opensearch_password(),
        )
    return _os_client


def _build_prompt(question: str, contexts: list[dict]) -> str:
    ctx_text = "\n\n---\n\n".join(
        f"[Fonte: {c['metadata'].get('title', c['doc_id'])} | Score: {c['score']:.3f}]\n{c['text']}"
        for c in contexts
    )
    return f"""You are an MLOps expert assistant. Answer the question based ONLY on the provided context.
If the context doesn't contain enough information, say so clearly.
Always cite which source(s) you used.

<context>
{ctx_text}
</context>

<question>
{question}
</question>

Provide a clear, technical, and concise answer in the same language as the question:"""


def _save_history(session_id: str, question: str, answer: str, contexts: list) -> None:
    try:
        table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        table.put_item(Item={
            "session_id": session_id,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "question":   question,
            "answer":     answer,
            "sources":    [c["doc_id"] for c in contexts],
            "expires_at": str(int(datetime.now(timezone.utc).timestamp()) + 86400 * 30),
        })
    except Exception as e:
        logger.warning("Falha ao salvar histórico: %s", e)


def lambda_handler(event: dict, context: Any) -> dict:
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path   = event.get("rawPath", "/")

    # Health check
    if path == "/health" or method == "GET":
        return _response(200, {"status": "ok", "service": "rag-mlops-api"})

    body       = json.loads(event.get("body") or "{}")
    question   = body.get("question", "").strip()
    session_id = body.get("session_id", "anonymous")
    top_k      = int(os.environ.get("TOP_K", 5))

    if not question:
        return _response(400, {"error": "Campo 'question' é obrigatório"})

    logger.info("Query | session=%s | question=%s", session_id, question[:80])

    # 1. Embed da pergunta
    query_embedding = get_embedding(
        text=question,
        model_id=os.environ["BEDROCK_EMBEDDING_MODEL"],
    )

    # 2. Busca semântica no OpenSearch
    os_client = _get_os_client()
    contexts  = os_client.semantic_search(embedding=query_embedding, top_k=top_k)
    logger.info("Chunks recuperados: %d", len(contexts))

    if not contexts:
        return _response(200, {
            "answer":   "Não encontrei informações relevantes na base de conhecimento.",
            "sources":  [],
            "contexts": [],
        })

    # 3. Geração com Claude via Bedrock
    prompt = _build_prompt(question, contexts)
    bedrock_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    })

    bedrock_resp = bedrock.invoke_model(
        modelId=os.environ["BEDROCK_LLM_MODEL"],
        body=bedrock_body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(bedrock_resp["body"].read())
    answer = result["content"][0]["text"]

    # 4. Persiste no DynamoDB
    _save_history(session_id, question, answer, contexts)

    return _response(200, {
        "answer":   answer,
        "sources":  list({c["metadata"].get("title", c["doc_id"]) for c in contexts}),
        "contexts": [{"text": c["text"][:200] + "...", "score": c["score"]} for c in contexts],
        "model":    os.environ["BEDROCK_LLM_MODEL"],
    })


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
