from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# Uses the same all-MiniLM-L6-v2 model but via ONNX runtime
# (already bundled with ChromaDB — no PyTorch needed)
_ef = ONNXMiniLM_L6_V2()


def embed_texts(texts):
    """Embed a list of texts for document storage."""
    return _ef(texts)


def embed_query(text):
    """Embed a single query for retrieval."""
    return _ef([text])[0]
