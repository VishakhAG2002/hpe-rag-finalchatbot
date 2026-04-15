import os
from dotenv import load_dotenv

load_dotenv()

# --- API ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Models ---
EMBEDDING_MODEL = "models/gemini-embedding-001"
LLM_MODEL = "gemini-2.5-flash-lite"
LLM_TEMPERATURE = 0.3
LLM_MAX_OUTPUT_TOKENS = 2048

# --- Chunking ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
SEPARATORS = ["\n\n", "\n", ". ", " "]

# --- Retrieval ---
CHROMA_COLLECTION = "hpe_docs"
CHROMA_DB_PATH = "./chroma_db"
TOP_K = 5
SIMILARITY_THRESHOLD = 1.2  # cosine distance; lower = more similar

# --- Paths ---
PDF_DIR = "./pdfs"
WEB_SOURCE_URL = "https://support.hpe.com/docs/display/public/dp00007440en_us/index.html"

# --- Rate Limiting ---
EMBED_RPM = 1400
EMBED_BATCH_SIZE = 50
LLM_RPM = 14
