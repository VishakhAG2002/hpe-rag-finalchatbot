#!/usr/bin/env python3
"""Ingest HPE PDFs and web docs into the vector store."""

import sys
import os
from pdf_processor import process_all_pdfs
from web_scraper import scrape_api_docs
from rag_engine import add_documents, collection
from config import PDF_DIR, GOOGLE_API_KEY, WEB_SOURCE_URL


def main():
    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY not set. Create a .env file with your key.")
        print("Get a free key at: https://aistudio.google.com/apikey")
        sys.exit(1)

    # Check PDF directory
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    print(f"Found {len(pdf_files)} PDF(s) in {PDF_DIR}/")

    # Check for existing data
    existing = collection.count()
    if existing > 0:
        print(f"Vector store already has {existing} chunks.")
        resp = input("Clear and re-ingest? [y/N]: ").strip().lower()
        if resp == "y":
            # Delete all documents
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)
            print("Cleared existing data.")
        else:
            print("Keeping existing data. Appending new documents.")

    all_chunks = []

    # 1. Process PDFs
    if pdf_files:
        print("\n--- Processing PDFs ---")
        pdf_chunks = process_all_pdfs(PDF_DIR)
        all_chunks.extend(pdf_chunks)
        print(f"PDF total: {len(pdf_chunks)} chunks")
    else:
        print(f"\nNo PDFs in {PDF_DIR}/ — skipping PDF ingestion.")

    # 2. Scrape web docs
    print("\n--- Scraping HPE OneView REST API Reference ---")
    try:
        web_chunks = scrape_api_docs(WEB_SOURCE_URL)
        all_chunks.extend(web_chunks)
        print(f"Web total: {len(web_chunks)} chunks")
    except Exception as e:
        print(f"WARNING: Web scraping failed: {e}")
        print("Continuing with PDF-only data.")

    # 3. Embed and store
    if all_chunks:
        print(f"\n--- Embedding & storing {len(all_chunks)} total chunks ---")
        add_documents(all_chunks)
        print(f"\nDone! Vector store now has {collection.count()} chunks.")
        print("Start the chatbot: python server.py")
    else:
        print("\nNo data to ingest. Add PDFs to pdfs/ or check web scraping.")
        sys.exit(1)


if __name__ == "__main__":
    main()
