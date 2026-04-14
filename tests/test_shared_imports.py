# tests/test_shared_imports.py
import sys
import os
from unittest.mock import MagicMock

# Mock heavy deps so test runs without installing them
sys.modules['boto3'] = MagicMock()
sys.modules['opensearchpy'] = MagicMock()
sys.modules['opensearchpy.helpers'] = MagicMock()
sys.modules['requests_aws4auth'] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "layers"))

from shared.embedder import get_embedding, get_embeddings
from shared.opensearch_client import OpenSearchClient


def test_get_embedding_is_callable():
    assert callable(get_embedding)


def test_get_embeddings_is_callable():
    assert callable(get_embeddings)


def test_opensearch_client_is_class():
    assert isinstance(OpenSearchClient, type)
