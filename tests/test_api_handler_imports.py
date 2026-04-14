# tests/test_api_handler_imports.py
import sys
import os
import ast


def test_api_handler_uses_shared_imports():
    path = os.path.join(
        os.path.dirname(__file__), "..", "src", "api", "handler.py"
    )
    source = open(path).read()
    tree = ast.parse(source)
    import_froms = [
        (n.module, [a.name for a in n.names])
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
    ]
    assert ("shared.embedder", ["get_embedding"]) in import_froms, \
        "handler.py deve importar get_embedding de shared.embedder"
    assert ("shared.opensearch_client", ["OpenSearchClient"]) in import_froms, \
        "handler.py deve importar OpenSearchClient de shared.opensearch_client"
