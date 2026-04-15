from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from rag_engine import query as rag_query, collection
from config import GOOGLE_API_KEY

app = FastAPI(title="HPE RAG Chatbot")


# --- Models ---
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class SourceInfo(BaseModel):
    source: str
    page: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]


# --- API Routes ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(500, "GOOGLE_API_KEY not configured")
    if collection.count() == 0:
        raise HTTPException(503, "No documents ingested. Run: python ingest.py")

    try:
        history = [{"role": m.role, "content": m.content} for m in request.history]
        result = rag_query(request.message, history)
        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        err_str = str(e)
        if "ResourceExhausted" in type(e).__name__ or (
            "429" in err_str and "quota" in err_str.lower()
        ):
            raise HTTPException(429, "Rate limit reached. Please wait a moment.")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error: {err_str[:200]}")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "vector_store": collection.count() > 0,
        "chunks": collection.count(),
    }


@app.get("/api/stats")
async def stats():
    all_meta = collection.get(include=["metadatas"])
    sources = set()
    for m in all_meta["metadatas"]:
        sources.add(m.get("source", "unknown"))
    return {
        "total_chunks": collection.count(),
        "documents": sorted(sources),
        "document_count": len(sources),
    }


# --- Static files (must be after API routes) ---
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    print("Starting HPE RAG Chatbot...")
    print(f"Vector store: {collection.count()} chunks loaded")
    print("Open: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
