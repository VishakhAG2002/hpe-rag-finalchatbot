import os
import glob
import fitz  # PyMuPDF
from config import PDF_DIR, CHUNK_SIZE, CHUNK_OVERLAP, SEPARATORS


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF, returning a list of page dicts."""
    doc = fitz.open(pdf_path)
    filename = os.path.basename(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()

        # Skip near-empty pages (cover pages, blank pages)
        if len(text) < 50:
            continue

        # Clean up excessive whitespace
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        text = "\n".join(cleaned_lines)

        pages.append({
            "text": text,
            "page": page_num + 1,
            "source": filename,
        })

    doc.close()
    return pages


def recursive_split(text, separators, chunk_size):
    """Recursively split text using hierarchical separators."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    if not separators:
        # Last resort: hard split at chunk_size
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks

    sep = separators[0]
    parts = text.split(sep)

    chunks = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part) > chunk_size:
                # Recurse with next separator
                chunks.extend(recursive_split(part, separators[1:], chunk_size))
                current = ""
            else:
                current = part

    if current.strip():
        chunks.append(current)

    return chunks


def chunk_documents(pages):
    """Split page-level documents into overlapping chunks with metadata."""
    all_chunks = []

    for page_doc in pages:
        text = page_doc["text"]
        raw_chunks = recursive_split(text, SEPARATORS, CHUNK_SIZE)

        for i, chunk_text in enumerate(raw_chunks):
            # Add overlap from previous chunk
            if i > 0 and CHUNK_OVERLAP > 0:
                prev = raw_chunks[i - 1]
                overlap_text = prev[-CHUNK_OVERLAP:] if len(prev) > CHUNK_OVERLAP else prev
                chunk_text = overlap_text + " " + chunk_text

            chunk_id = f"{page_doc['source']}_p{page_doc['page']}_c{i}"
            all_chunks.append({
                "text": chunk_text.strip(),
                "source": page_doc["source"],
                "page": page_doc["page"],
                "chunk_id": chunk_id,
            })

    return all_chunks


def process_all_pdfs(pdf_dir=PDF_DIR):
    """Process all PDFs in the directory. Returns aggregated list of chunks."""
    pdf_files = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))

    if not pdf_files:
        print(f"No PDFs found in {pdf_dir}/")
        return []

    all_chunks = []

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        try:
            pages = extract_text_from_pdf(pdf_path)
            chunks = chunk_documents(pages)
            all_chunks.extend(chunks)
            print(f"  {filename}: {len(pages)} pages -> {len(chunks)} chunks")
        except Exception as e:
            print(f"  WARNING: Failed to process {filename}: {e}")

    return all_chunks
