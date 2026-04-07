#!/usr/bin/env python3
"""
scripts/query.py — CLI para queries no RAG MLOps
Uso:
  python3 scripts/query.py --api-url <URL> --question "O que é MLOps?"
  python3 scripts/query.py --api-url <URL>  # modo interativo
"""
import argparse
import json
import sys
import uuid
import requests


def query_rag(api_url: str, question: str, session_id: str) -> dict:
    url = f"{api_url.rstrip('/')}/query"
    resp = requests.post(url, json={"question": question, "session_id": session_id}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def print_result(result: dict) -> None:
    print("\n" + "="*60)
    print("🤖 RESPOSTA:")
    print("="*60)
    print(result.get("answer", "Sem resposta"))
    print("\n" + "-"*60)
    sources = result.get("sources", [])
    if sources:
        print(f"📚 Fontes ({len(sources)}): {', '.join(sources)}")
    contexts = result.get("contexts", [])
    if contexts:
        print(f"🔍 Chunks recuperados: {len(contexts)} | Top score: {contexts[0]['score']:.3f}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Query RAG MLOps")
    parser.add_argument("--api-url",  required=True, help="URL base da API Gateway")
    parser.add_argument("--question", help="Pergunta (sem isso entra em modo interativo)")
    args = parser.parse_args()

    session_id = str(uuid.uuid4())[:8]

    # Health check
    try:
        health = requests.get(f"{args.api_url}/health", timeout=10)
        health.raise_for_status()
        print(f"✅ API online | session={session_id}")
    except Exception as e:
        print(f"❌ API offline: {e}")
        sys.exit(1)

    if args.question:
        result = query_rag(args.api_url, args.question, session_id)
        print_result(result)
        return

    # Modo interativo
    print("\n🤖 RAG MLOps — Modo interativo (Ctrl+C para sair)\n")
    while True:
        try:
            question = input("❓ Pergunta: ").strip()
            if not question:
                continue
            result = query_rag(args.api_url, question, session_id)
            print_result(result)
        except KeyboardInterrupt:
            print("\n\n👋 Até mais!")
            break
        except Exception as e:
            print(f"❌ Erro: {e}")


if __name__ == "__main__":
    main()
