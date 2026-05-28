import re
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup

_NOISE_TAGS = ["nav", "footer", "header", "script", "style", "aside", "iframe", "noscript"]

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""

def compute_hash_id(source_url: str, content: str) -> str:
    raw = f"{source_url}||{content}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def clean_to_document(raw_html: str, source_url: str, source_type: str, source_tier: str) -> dict:
    title = extract_title(raw_html)
    content = clean_html(raw_html)
    return {
        "title": title,
        "content": content,
        "source_url": source_url,
        "source_type": source_type,
        "source_tier": source_tier,
        "crawled_at": datetime.now().isoformat(),
        "hash_id": compute_hash_id(source_url, content),
    }
