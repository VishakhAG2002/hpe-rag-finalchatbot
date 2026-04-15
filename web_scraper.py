import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pdf_processor import chunk_documents
from config import WEB_SOURCE_URL


def fetch_page(url, timeout=15):
    """Fetch a page and extract clean text content."""
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (HPE RAG Chatbot POC)"
        })
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    WARNING: Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script, style, nav, footer elements
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    # Try to find main content area
    main = (
        soup.find("main")
        or soup.find("div", {"role": "main"})
        or soup.find("div", class_="content")
        or soup.find("article")
        or soup.find("div", id="content")
        or soup.body
    )

    if not main:
        return None

    text = main.get_text(separator="\n", strip=True)

    # Skip pages with very little content
    if len(text) < 100:
        return None

    return text


def extract_links(base_url):
    """Extract all documentation sub-page links from the index page."""
    try:
        resp = requests.get(base_url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (HPE RAG Chatbot POC)"
        })
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  WARNING: Failed to fetch index page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    base_parsed = urlparse(base_url)
    base_dir = base_url.rsplit("/", 1)[0] + "/"

    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Only follow links within the same documentation path
        if parsed.netloc == base_parsed.netloc and "/dp00007440en_us/" in parsed.path:
            # Remove fragment
            clean_url = parsed._replace(fragment="").geturl()
            if clean_url != base_url and clean_url.endswith(".html"):
                links.add(clean_url)

    return sorted(links)


def scrape_api_docs(base_url=WEB_SOURCE_URL):
    """Scrape the HPE OneView REST API reference site. Returns list of page dicts."""
    print(f"  Fetching index: {base_url}")

    # First, get content from the index page itself
    pages = []
    index_text = fetch_page(base_url)
    if index_text:
        pages.append({
            "text": index_text,
            "page": "index",
            "source": "HPE OneView REST API Reference",
        })

    # Extract and crawl sub-pages
    sub_links = extract_links(base_url)
    print(f"  Found {len(sub_links)} sub-pages to crawl")

    for i, url in enumerate(sub_links):
        # Rate limit: 1 request per second
        time.sleep(1)

        page_name = url.rsplit("/", 1)[-1].replace(".html", "")
        text = fetch_page(url)

        if text:
            pages.append({
                "text": text,
                "page": page_name,
                "source": "HPE OneView REST API Reference",
            })

        if (i + 1) % 10 == 0:
            print(f"    Scraped {i + 1}/{len(sub_links)} pages...")

    print(f"  Scraped {len(pages)} pages total from API reference")

    # Chunk through the same pipeline as PDFs
    chunks = chunk_documents(pages)
    return chunks
