"""embedder.py — gera embeddings via Amazon Bedrock Titan Embeddings V2"""
import json
import boto3
import logging
from typing import List

logger = logging.getLogger(__name__)
bedrock = boto3.client("bedrock-runtime")


def get_embedding(text: str, model_id: str) -> List[float]:
    """Gera embedding para um único texto."""
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    response = bedrock.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def get_embeddings(texts: List[str], model_id: str) -> List[List[float]]:
    """Gera embeddings em batch (sequencial — Titan não tem batch nativo)."""
    embeddings = []
    for i, text in enumerate(texts):
        if i % 10 == 0:
            logger.info("Embedding %d/%d...", i + 1, len(texts))
        embeddings.append(get_embedding(text[:8192], model_id))  # limite Titan V2
    return embeddings
