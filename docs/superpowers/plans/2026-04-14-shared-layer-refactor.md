# Shared Layer Refactor — embedder & opensearch_client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mover `embedder.py` e `opensearch_client.py` para `src/layers/shared/` e empacotar esse diretório em ambos os zips Lambda (Ingest e API), eliminando o hack de `sys.path.insert` e a duplicação manual de arquivos no Terraform.

**Architecture:** Criar `src/layers/shared/` como pacote Python com os módulos compartilhados. Ambos os `archive_file` do Terraform listam explicitamente cada arquivo-fonte usando blocos `source {}`, incluindo `shared/embedder.py` e `shared/opensearch_client.py` com seus caminhos relativos preservados. No Lambda, `/var/task/shared/` fica acessível e os handlers importam via `from shared.embedder import ...`.

**Tech Stack:** Python 3.12, Terraform `archive_file` (hashicorp/archive), AWS Lambda

---

### Task 1: Criar `src/layers/shared/` com os módulos movidos

**Files:**
- Create: `src/layers/shared/__init__.py`
- Create: `src/layers/shared/embedder.py`
- Create: `src/layers/shared/opensearch_client.py`

- [ ] **Step 1: Escrever teste de importação que deve falhar antes de existir o pacote**

```python
# tests/test_shared_imports.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "layers"))

from shared.embedder import get_embedding, get_embeddings
from shared.opensearch_client import OpenSearchClient

def test_get_embedding_is_callable():
    assert callable(get_embedding)

def test_get_embeddings_is_callable():
    assert callable(get_embeddings)

def test_opensearch_client_is_class():
    assert isinstance(OpenSearchClient, type)
```

- [ ] **Step 2: Rodar teste para confirmar que falha**

```bash
cd C:/Users/rafael.santiago/Documents/rag-mlops-aws
python -m pytest tests/test_shared_imports.py -v
```
Expected: `ModuleNotFoundError: No module named 'shared'`

- [ ] **Step 3: Criar o diretório e o `__init__.py`**

```bash
mkdir -p src/layers/shared
touch src/layers/shared/__init__.py
```

Conteúdo de `src/layers/shared/__init__.py`: arquivo vazio.

- [ ] **Step 4: Criar `src/layers/shared/embedder.py`**

Conteúdo idêntico ao atual `src/ingestion/embedder.py`:

```python
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
```

- [ ] **Step 5: Criar `src/layers/shared/opensearch_client.py`**

Conteúdo idêntico ao atual `src/ingestion/opensearch_client.py`:

```python
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
```

- [ ] **Step 6: Rodar teste — deve passar agora**

```bash
python -m pytest tests/test_shared_imports.py -v
```
Expected: 3 PASSED (boto3 está disponível; opensearchpy pode não estar — se falhar com ImportError de opensearchpy, instale `pip install opensearch-py requests-aws4auth` ou mocke o import no teste com `unittest.mock.patch`).

> **Nota:** Se o ambiente local não tiver `opensearch-py`, ajuste o teste para mockar o módulo:
> ```python
> import sys
> from unittest.mock import MagicMock
> sys.modules['opensearchpy'] = MagicMock()
> sys.modules['requests_aws4auth'] = MagicMock()
> ```
> Adicione essas linhas antes do import `from shared.opensearch_client`.

- [ ] **Step 7: Commit**

```bash
git add src/layers/shared/
git add tests/test_shared_imports.py
git commit -m "feat: criar src/layers/shared com embedder e opensearch_client"
```

---

### Task 2: Atualizar `src/ingestion/handler.py` — trocar imports

**Files:**
- Modify: `src/ingestion/handler.py:11-13`

- [ ] **Step 1: Escrever teste de sintaxe para o handler de ingestão**

```python
# tests/test_ingest_handler_imports.py
import sys, os, ast

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
```

- [ ] **Step 2: Rodar para confirmar que falha**

```bash
python -m pytest tests/test_ingest_handler_imports.py -v
```
Expected: FAILED — `shared.embedder` não está nos imports atuais.

- [ ] **Step 3: Editar `src/ingestion/handler.py` — substituir imports**

Substituir as linhas:
```python
from chunker import chunk_document
from embedder import get_embeddings
from opensearch_client import OpenSearchClient
```
Por:
```python
from chunker import chunk_document
from shared.embedder import get_embeddings
from shared.opensearch_client import OpenSearchClient
```

- [ ] **Step 4: Rodar teste — deve passar**

```bash
python -m pytest tests/test_ingest_handler_imports.py -v
```
Expected: PASSED

- [ ] **Step 5: Commit**

```bash
git add src/ingestion/handler.py tests/test_ingest_handler_imports.py
git commit -m "refactor: ingestion handler importa de shared.embedder e shared.opensearch_client"
```

---

### Task 3: Atualizar `src/api/handler.py` — trocar imports

**Files:**
- Modify: `src/api/handler.py:12-13`

- [ ] **Step 1: Escrever teste de sintaxe para o handler de API**

```python
# tests/test_api_handler_imports.py
import sys, os, ast

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
```

- [ ] **Step 2: Rodar para confirmar que falha**

```bash
python -m pytest tests/test_api_handler_imports.py -v
```
Expected: FAILED

- [ ] **Step 3: Editar `src/api/handler.py` — substituir imports**

Substituir as linhas:
```python
from embedder import get_embedding
from opensearch_client import OpenSearchClient
```
Por:
```python
from shared.embedder import get_embedding
from shared.opensearch_client import OpenSearchClient
```

- [ ] **Step 4: Rodar teste — deve passar**

```bash
python -m pytest tests/test_api_handler_imports.py -v
```
Expected: PASSED

- [ ] **Step 5: Commit**

```bash
git add src/api/handler.py tests/test_api_handler_imports.py
git commit -m "refactor: api handler importa de shared.embedder e shared.opensearch_client"
```

---

### Task 4: Remover `embedder.py` e `opensearch_client.py` de `src/ingestion/`

**Files:**
- Delete: `src/ingestion/embedder.py`
- Delete: `src/ingestion/opensearch_client.py`

- [ ] **Step 1: Confirmar que nenhum arquivo restante em src/ importa dos caminhos antigos**

```bash
grep -r "from embedder import\|from opensearch_client import" src/
```
Expected: nenhuma saída (zero matches).

- [ ] **Step 2: Deletar os arquivos antigos**

```bash
git rm src/ingestion/embedder.py src/ingestion/opensearch_client.py
```

- [ ] **Step 3: Confirmar estrutura resultante**

```bash
find src/ -name "*.py" | sort
```
Expected:
```
src/api/handler.py
src/ingestion/chunker.py
src/ingestion/handler.py
src/layers/shared/__init__.py
src/layers/shared/embedder.py
src/layers/shared/opensearch_client.py
```

- [ ] **Step 4: Rodar todos os testes**

```bash
python -m pytest tests/ -v
```
Expected: todos os testes de importação passando.

- [ ] **Step 5: Commit**

```bash
git commit -m "refactor: remover embedder.py e opensearch_client.py de src/ingestion (movidos para shared)"
```

---

### Task 5: Atualizar `terraform/lambda_apigw.tf` — reempacotar ambos os Lambdas

**Files:**
- Modify: `terraform/lambda_apigw.tf:13-17` (archive_file lambda_ingest)
- Modify: `terraform/lambda_apigw.tf:55-71` (archive_file lambda_api)

**Contexto:** O `archive_file` do Terraform preserva o caminho do `filename` dentro do zip. Ao definir `filename = "shared/embedder.py"`, o arquivo ficará em `/var/task/shared/embedder.py` no Lambda — exatamente onde `from shared.embedder import ...` espera encontrá-lo.

- [ ] **Step 1: Substituir `data "archive_file" "lambda_ingest"` — de source_dir para source blocks explícitos**

Substituir o bloco atual:
```hcl
data "archive_file" "lambda_ingest" {
  type        = "zip"
  source_dir  = "${path.module}/../src/ingestion"
  output_path = "${path.module}/lambda_ingest.zip"
}
```

Por:
```hcl
data "archive_file" "lambda_ingest" {
  type        = "zip"
  output_path = "${path.module}/lambda_ingest.zip"

  source {
    content  = file("${path.module}/../src/ingestion/handler.py")
    filename = "handler.py"
  }
  source {
    content  = file("${path.module}/../src/ingestion/chunker.py")
    filename = "chunker.py"
  }
  source {
    content  = file("${path.module}/../src/layers/shared/embedder.py")
    filename = "shared/embedder.py"
  }
  source {
    content  = file("${path.module}/../src/layers/shared/opensearch_client.py")
    filename = "shared/opensearch_client.py"
  }
  source {
    content  = ""
    filename = "shared/__init__.py"
  }
}
```

- [ ] **Step 2: Substituir `data "archive_file" "lambda_api"` — atualizar source blocks**

Substituir o bloco atual:
```hcl
data "archive_file" "lambda_api" {
  type        = "zip"
  output_path = "${path.module}/lambda_api.zip"

  source {
    content  = file("${path.module}/../src/api/handler.py")
    filename = "handler.py"
  }
  source {
    content  = file("${path.module}/../src/ingestion/embedder.py")
    filename = "embedder.py"
  }
  source {
    content  = file("${path.module}/../src/ingestion/opensearch_client.py")
    filename = "opensearch_client.py"
  }
}
```

Por:
```hcl
data "archive_file" "lambda_api" {
  type        = "zip"
  output_path = "${path.module}/lambda_api.zip"

  source {
    content  = file("${path.module}/../src/api/handler.py")
    filename = "handler.py"
  }
  source {
    content  = file("${path.module}/../src/layers/shared/embedder.py")
    filename = "shared/embedder.py"
  }
  source {
    content  = file("${path.module}/../src/layers/shared/opensearch_client.py")
    filename = "shared/opensearch_client.py"
  }
  source {
    content  = ""
    filename = "shared/__init__.py"
  }
}
```

- [ ] **Step 3: Validar o Terraform**

```bash
cd terraform
terraform fmt
terraform validate
```
Expected: `Success! The configuration is valid.`

- [ ] **Step 4: Verificar que o zip da API não referencia mais src/ingestion/embedder.py**

```bash
grep -n "ingestion/embedder\|ingestion/opensearch" terraform/lambda_apigw.tf
```
Expected: nenhuma saída.

- [ ] **Step 5: Commit**

```bash
cd ..
git add terraform/lambda_apigw.tf
git commit -m "terraform: reempacotar lambdas incluindo shared/ em vez de copiar de ingestion"
```

---

### Task 6: Verificação final — rodar todos os testes e checar estrutura do zip

**Files:** nenhum arquivo novo.

- [ ] **Step 1: Rodar toda a suite de testes**

```bash
python -m pytest tests/ -v
```
Expected: todos PASSED.

- [ ] **Step 2: Verificar conteúdo dos zips gerados pelo Terraform**

```bash
cd terraform
terraform plan -out=tfplan 2>&1 | head -40
```
Expected: plano menciona `lambda_ingest.zip` e `lambda_api.zip` com hash atualizado.

- [ ] **Step 3: Inspecionar o zip da API para confirmar estrutura shared/**

```bash
cd terraform
python -c "
import zipfile
with zipfile.ZipFile('lambda_api.zip') as z:
    for name in sorted(z.namelist()):
        print(name)
"
```
Expected:
```
handler.py
shared/__init__.py
shared/embedder.py
shared/opensearch_client.py
```

- [ ] **Step 4: Inspecionar o zip de Ingest**

```bash
python -c "
import zipfile
with zipfile.ZipFile('lambda_ingest.zip') as z:
    for name in sorted(z.namelist()):
        print(name)
"
```
Expected:
```
chunker.py
handler.py
shared/__init__.py
shared/embedder.py
shared/opensearch_client.py
```

- [ ] **Step 5: Commit final**

```bash
cd ..
git add .
git commit -m "chore: verificação final — shared layer empacotado corretamente em ambos os lambdas"
```
