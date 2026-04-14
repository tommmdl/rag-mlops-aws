# tests/test_ingest_handler_imports.py
import sys
import os
import ast


def test_ingest_handler_uses_shared_imports():
    path = os.path.join(
        os.path.dirname(__file__), "..", "src", "ingestion", "handler.py"
    )
    source = open(path).read()
    tree = ast.parse(source)
    import_froms = [
        (n.module, [a.name for a in n.names])
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
    ]
    assert ("shared.embedder", ["get_embeddings"]) in import_froms, \
        "handler.py deve importar get_embeddings de shared.embedder"
    assert ("shared.opensearch_client", ["OpenSearchClient"]) in import_froms, \
        "handler.py deve importar OpenSearchClient de shared.opensearch_client"
    # chunker permanece local
    assert ("chunker", ["chunk_document"]) in import_froms, \
        "handler.py deve importar chunk_document de chunker (local)"
