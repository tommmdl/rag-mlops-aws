"""
Lambda de ingestão — RAG MLOps AWS
Fluxo: S3/payload → chunk → Bedrock Titan embeddings → OpenSearch index
"""
import json
import os
import boto3
import logging
from typing import Any

from chunker import chunk_document
from shared.embedder import get_embeddings
from shared.opensearch_client import OpenSearchClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client("ssm")
s3  = boto3.client("s3")

_opensearch_password: str | None = None


def _get_opensearch_password() -> str:
    global _opensearch_password
    if _opensearch_password is None:
        resp = ssm.get_parameter(
            Name=os.environ["SSM_PASSWORD_PATH"],
            WithDecryption=True,
        )
        _opensearch_password = resp["Parameter"]["Value"]
    return _opensearch_password


def lambda_handler(event: dict, context: Any) -> dict:
    logger.info("Ingestão iniciada | event keys: %s", list(event.keys()))

    body = json.loads(event.get("body") or "{}")
    source = body.get("source", "payload")  # "payload" | "s3"

    # Carrega o texto a ser ingerido
    if source == "s3":
        bucket = body["bucket"]
        key    = body["key"]
        obj    = s3.get_object(Bucket=bucket, Key=key)
        text   = obj["Body"].read().decode("utf-8")
        doc_id = key
    else:
        text   = body.get("text", "")
        doc_id = body.get("doc_id", "doc-unknown")

    if not text.strip():
        return _response(400, {"error": "Texto vazio"})

    metadata = {
        "doc_id":   doc_id,
        "source":   source,
        "title":    body.get("title", doc_id),
        "category": body.get("category", "mlops"),
        "tags":     body.get("tags", []),
    }

    # 1. Chunking
    chunks = chunk_document(
        text=text,
        chunk_size=int(os.environ.get("CHUNK_SIZE", 512)),
        overlap=int(os.environ.get("CHUNK_OVERLAP", 50)),
    )
    logger.info("Chunks gerados: %d", len(chunks))

    # 2. Embeddings via Bedrock Titan
    embeddings = get_embeddings(
        texts=[c["text"] for c in chunks],
        model_id=os.environ["BEDROCK_EMBEDDING_MODEL"],
    )
    logger.info("Embeddings gerados: %d", len(embeddings))

    # 3. Index no OpenSearch
    password = _get_opensearch_password()
    os_client = OpenSearchClient(
        endpoint=os.environ["OPENSEARCH_ENDPOINT"],
        index=os.environ["OPENSEARCH_INDEX"],
        username=os.environ["OPENSEARCH_USER"],
        password=password,
    )

    os_client.ensure_index()

    docs_to_index = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        docs_to_index.append({
            "doc_id":    f"{doc_id}::chunk-{i}",
            "text":      chunk["text"],
            "embedding": embedding,
            "metadata":  {**metadata, "chunk_index": i, "chunk_total": len(chunks)},
        })

    indexed = os_client.bulk_index(docs_to_index)
    logger.info("Documentos indexados: %d", indexed)

    return _response(200, {
        "doc_id":   doc_id,
        "chunks":   len(chunks),
        "indexed":  indexed,
        "status":   "success",
    })


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
