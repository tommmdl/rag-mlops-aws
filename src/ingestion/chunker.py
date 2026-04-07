"""chunker.py — divide texto em chunks com overlap"""
from typing import List


def chunk_document(text: str, chunk_size: int = 512, overlap: int = 50) -> List[dict]:
    """Divide o texto em chunks por tokens aproximados (palavras)."""
    words  = text.split()
    chunks = []
    start  = 0

    while start < len(words):
        end        = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append({"text": chunk_text, "start": start, "end": end})
        if end == len(words):
            break
        start = end - overlap  # overlap entre chunks

    return chunks
