#!/usr/bin/env python3
"""
scripts/ingest.py — CLI para ingestão de documentos no RAG MLOps
Uso:
  python3 scripts/ingest.py --api-url <URL> --docs-dir docs/
  python3 scripts/ingest.py --local --docs-dir docs/
"""
import argparse
import json
import os
import sys
import time
import glob
import requests
from pathlib import Path

SUPPORTED_EXTENSIONS = [".txt", ".md", ".rst"]


def load_document(filepath: str) -> dict:
    path  = Path(filepath)
    text  = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "doc_id":   path.stem,
        "title":    path.stem.replace("-", " ").replace("_", " ").title(),
        "text":     text,
        "category": "mlops",
        "tags":     [path.suffix.strip(".")],
        "source":   "payload",
    }


def ingest_via_api(api_url: str, doc: dict) -> bool:
    url = f"{api_url.rstrip('/')}/ingest"
    try:
        resp = requests.post(url, json=doc, timeout=300)
        resp.raise_for_status()
        result = resp.json()
        print(f"  ✅ {doc['doc_id']} → {result.get('chunks', '?')} chunks indexados")
        return True
    except Exception as e:
        print(f"  ❌ {doc['doc_id']} → Erro: {e}")
        return False


def ingest_local(doc: dict) -> bool:
    """Modo local: só valida chunking sem AWS."""
    words = doc["text"].split()
    print(f"  📝 {doc['doc_id']} → {len(words)} palavras (~{len(words)//512 + 1} chunks estimados) [LOCAL]")
    return True


def main():
    parser = argparse.ArgumentParser(description="Ingestão de documentos RAG MLOps")
    parser.add_argument("--api-url",  help="URL base da API Gateway")
    parser.add_argument("--docs-dir", default="docs/", help="Diretório com documentos")
    parser.add_argument("--local",    action="store_true", help="Modo local (sem AWS)")
    parser.add_argument("--file",     help="Ingerir um único arquivo")
    args = parser.parse_args()

    if not args.local and not args.api_url:
        print("❌ Forneça --api-url ou use --local")
        sys.exit(1)

    # Coleta arquivos
    if args.file:
        files = [args.file]
    else:
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(glob.glob(f"{args.docs_dir}/**/*{ext}", recursive=True))
            files.extend(glob.glob(f"{args.docs_dir}/*{ext}"))
        files = list(set(files))

    if not files:
        print(f"⚠️  Nenhum documento encontrado em '{args.docs_dir}'")
        print(f"   Extensões suportadas: {SUPPORTED_EXTENSIONS}")
        sys.exit(0)

    print(f"\n📚 Ingerindo {len(files)} documento(s)...\n")
    success, failed = 0, 0

    for filepath in sorted(files):
        doc = load_document(filepath)
        if len(doc["text"].strip()) < 50:
            print(f"  ⏭️  {doc['doc_id']} → Muito curto, ignorado")
            continue

        if args.local:
            ok = ingest_local(doc)
        else:
            ok = ingest_via_api(args.api_url, doc)
            time.sleep(0.5)  # rate limit gentil

        if ok:
            success += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"✅ Sucesso: {success} | ❌ Falha: {failed}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
