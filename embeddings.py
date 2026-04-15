from sentence_transformers import SentenceTransformer

# Load model once (384-dim, ~80MB, fast on CPU)
print("Loading embedding model...")
_model = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model ready.")


def embed_texts(texts):
    """Embed a list of texts for document storage. Returns list of vectors."""
    embeddings = _model.encode(texts, show_progress_bar=True, batch_size=64)
    return embeddings.tolist()


def embed_query(text):
    """Embed a single query for retrieval. Returns one vector."""
    embedding = _model.encode(text)
    return embedding.tolist()
