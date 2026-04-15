import chromadb
import google.generativeai as genai
from config import (
    GOOGLE_API_KEY, CHROMA_DB_PATH, CHROMA_COLLECTION,
    TOP_K, SIMILARITY_THRESHOLD, LLM_MODEL,
    LLM_TEMPERATURE, LLM_MAX_OUTPUT_TOKENS,
)
from embeddings import embed_texts, embed_query

genai.configure(api_key=GOOGLE_API_KEY)

# --- ChromaDB setup ---
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    metadata={"hnsw:space": "cosine"},
)

# --- RAG Prompt ---
SYSTEM_PROMPT = """You are an expert HPE (Hewlett Packard Enterprise) technical assistant specializing in HPE OneView documentation.
You help administrators and developers understand HPE OneView products, configurations, APIs, and troubleshooting.

RULES:
1. Answer ONLY based on the provided context. Do not use prior knowledge.
2. If the context does not contain enough information, say: "I don't have enough information in the available documentation to answer that. Try asking about HPE OneView features, configuration, API endpoints, or known issues."
3. Be precise and technical. Use specific product names, version numbers, and API details when available.
4. Format your answers with markdown: use **bold** for key terms, `code` for technical values, and bullet points for lists.
5. When referencing information, naturally mention which document it comes from (e.g., "According to the User Guide..." or "The Release Notes mention...").
6. Keep answers concise but complete. Aim for 2-4 paragraphs unless the question requires more detail."""


def add_documents(chunks):
    """Embed chunks and upsert into ChromaDB."""
    if not chunks:
        print("  No chunks to add.")
        return

    texts = [c["text"] for c in chunks]
    ids = [c["chunk_id"] for c in chunks]
    metadatas = [{"source": c["source"], "page": str(c["page"])} for c in chunks]

    print(f"  Embedding {len(texts)} chunks...")
    embeddings = embed_texts(texts)

    # Upsert in batches (ChromaDB limit)
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        collection.upsert(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
        )

    print(f"  Stored {len(ids)} chunks in vector store.")


def retrieve(query_text, top_k=TOP_K):
    """Retrieve the most relevant chunks for a query."""
    query_embedding = embed_query(query_text)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        if distance > SIMILARITY_THRESHOLD:
            continue
        chunks.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "page": results["metadatas"][0][i]["page"],
            "distance": distance,
        })

    return chunks


def generate_answer(query_text, contexts, chat_history=None):
    """Generate an answer using retrieved context and Gemini."""
    if not contexts:
        return {
            "answer": "I don't have enough information in the available documentation to answer that. Try asking about HPE OneView features, configuration, API endpoints, or known issues.",
            "sources": [],
        }

    # Build context block
    context_block = "\n\n---\n\n".join([
        f"[Source: {c['source']}, Page {c['page']}]\n{c['text']}"
        for c in contexts
    ])

    # Build history block
    history_block = "(No prior conversation)"
    if chat_history:
        recent = chat_history[-6:]  # Last 3 turns
        history_block = "\n".join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:500]}"
            for m in recent
        ])

    prompt = f"""{SYSTEM_PROMPT}

CONTEXT (retrieved from HPE documentation):
---
{context_block}
---

CONVERSATION HISTORY:
{history_block}

USER QUESTION: {query_text}

Provide a helpful, accurate answer based on the context above."""

    model = genai.GenerativeModel(LLM_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=LLM_TEMPERATURE,
            max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
        ),
    )

    # Deduplicate sources
    seen = set()
    sources = []
    for c in contexts:
        key = (c["source"], c["page"])
        if key not in seen:
            seen.add(key)
            sources.append({"source": c["source"], "page": c["page"]})

    return {
        "answer": response.text,
        "sources": sources,
    }


def query(user_message, chat_history=None):
    """Top-level RAG query: retrieve then generate."""
    contexts = retrieve(user_message)
    return generate_answer(user_message, contexts, chat_history)
