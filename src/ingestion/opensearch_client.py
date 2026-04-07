"""opensearch_client.py — abstração do OpenSearch para ingestão e busca"""
import json
import logging
from typing import List

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers
from requests_aws4auth import AWS4Auth

logger = logging.getLogger(__name__)

INDEX_MAPPING = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100,
        }
    },
    "mappings": {
        "properties": {
            "doc_id":    {"type": "keyword"},
            "text":      {"type": "text", "analyzer": "english"},
            "embedding": {
                "type":      "knn_vector",
                "dimension": 1024,
                "method": {
                    "name":       "hnsw",
                    "engine":     "faiss",
                    "space_type": "cosinesimil",
                    "parameters": {"ef_construction": 128, "m": 24},
                },
            },
            "metadata": {"type": "object", "dynamic": True},
        }
    },
}


class OpenSearchClient:
    def __init__(self, endpoint: str, index: str, username: str, password: str):
        self.index = index
        host = endpoint.replace("https://", "")

        self.client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=(username, password),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )

    def ensure_index(self) -> None:
        """Cria o índice se não existir."""
        if not self.client.indices.exists(index=self.index):
            self.client.indices.create(index=self.index, body=INDEX_MAPPING)
            logger.info("Índice '%s' criado.", self.index)
        else:
            logger.info("Índice '%s' já existe.", self.index)

    def bulk_index(self, documents: List[dict]) -> int:
        """Indexa documentos em bulk."""
        actions = [
            {
                "_index": self.index,
                "_id":    doc["doc_id"],
                "_source": {
                    "doc_id":    doc["doc_id"],
                    "text":      doc["text"],
                    "embedding": doc["embedding"],
                    "metadata":  doc["metadata"],
                },
            }
            for doc in documents
        ]
        success, errors = helpers.bulk(self.client, actions, raise_on_error=False)
        if errors:
            logger.warning("Erros no bulk index: %s", errors[:3])
        return success

    def semantic_search(self, embedding: List[float], top_k: int = 5) -> List[dict]:
        """Busca semântica por similaridade de vetor (kNN)."""
        query = {
            "size": top_k,
            "_source": ["text", "metadata", "doc_id"],
            "query": {
                "knn": {
                    "embedding": {
                        "vector": embedding,
                        "k": top_k,
                    }
                }
            },
        }
        response = self.client.search(index=self.index, body=query)
        hits = response["hits"]["hits"]
        return [
            {
                "text":     h["_source"]["text"],
                "metadata": h["_source"].get("metadata", {}),
                "doc_id":   h["_source"].get("doc_id", ""),
                "score":    h["_score"],
            }
            for h in hits
        ]
