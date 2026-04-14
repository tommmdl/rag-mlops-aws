"""
test_chunker.py — testes unitários para src/ingestion/chunker.py

chunk_document(text, chunk_size, overlap) divide texto em chunks por palavras.
Cada chunk é um dict com campos: text, start, end.
"""
import sys
import os

# src/ingestion/ já adicionado ao sys.path pelo conftest.py
from chunker import chunk_document


def test_basic_chunking():
    """Texto de 1000 palavras com chunk_size=100 deve produzir múltiplos chunks."""
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)
    chunks = chunk_document(text, chunk_size=100, overlap=50)
    assert len(chunks) > 1


def test_overlap():
    """As últimas `overlap` palavras do chunk N devem aparecer no início do chunk N+1."""
    words = [f"w{i}" for i in range(25)]
    text = " ".join(words)
    chunks = chunk_document(text, chunk_size=10, overlap=3)

    assert len(chunks) >= 2, "Deve haver pelo menos 2 chunks para testar overlap"

    chunk0_words = chunks[0]["text"].split()
    chunk1_words = chunks[1]["text"].split()

    # Últimas 3 palavras do chunk 0 == primeiras 3 palavras do chunk 1
    assert chunk0_words[-3:] == chunk1_words[:3]


def test_empty_text():
    """Texto vazio deve retornar lista vazia."""
    chunks = chunk_document("", chunk_size=100, overlap=10)
    assert chunks == []


def test_short_text():
    """Texto menor que chunk_size deve retornar exatamente 1 chunk."""
    words = [f"word{i}" for i in range(50)]
    text = " ".join(words)
    chunks = chunk_document(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1


def test_chunk_fields():
    """Cada chunk deve ter os campos 'text', 'start' e 'end'."""
    words = [f"word{i}" for i in range(200)]
    text = " ".join(words)
    chunks = chunk_document(text, chunk_size=50, overlap=10)

    for chunk in chunks:
        assert "text" in chunk, "Campo 'text' ausente"
        assert "start" in chunk, "Campo 'start' ausente"
        assert "end" in chunk, "Campo 'end' ausente"
