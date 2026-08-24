"""Reproducible ingestion of official Getnet pages into the local RAG corpus.

Run with: python -m app.services.ingestion --output /tmp/getnet-corpus.json
The curated corpus remains the default because it is reviewed and deterministic.
"""

import argparse
import asyncio
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import httpx


OFFICIAL_URLS = [
    "https://www.getnet.net/en",
    "https://site.getnet.com.br/maquininha/get-smart/",
    "https://site.getnet.com.br/maquininha/get-classica/",
    "https://site.getnet.com.br/conta-digital/",
    "https://site.getnet.com.br/get-ajuda/",
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "svg", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg", "noscript"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored and data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def chunk_text(text: str, size: int = 1200, overlap: int = 180) -> list[str]:
    chunks, cursor = [], 0
    while cursor < len(text):
        end = min(len(text), cursor + size)
        if end < len(text):
            boundary = text.rfind(". ", cursor + size // 2, end)
            end = boundary + 1 if boundary > cursor else end
        chunk = text[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        cursor = max(cursor + 1, end - overlap)
    return chunks


async def ingest(urls: list[str]) -> list[dict]:
    documents: list[dict] = []
    headers = {"User-Agent": "GetnetAgentOps/1.0 (take-home RAG indexer)"}
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
        for url in urls:
            response = await client.get(url)
            response.raise_for_status()
            if "text/html" not in response.headers.get("content-type", ""):
                continue
            parser = TextExtractor()
            parser.feed(response.text)
            title_match = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.I | re.S)
            title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else urlparse(url).path or urlparse(url).netloc
            for index, content in enumerate(chunk_text(parser.text())):
                documents.append({"id": f"{urlparse(url).netloc}-{index}", "title": title, "url": str(response.url), "content": content})
    return documents


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest official Getnet pages for the RAG corpus")
    parser.add_argument("--output", type=Path, default=Path("app/data/knowledge.ingested.json"))
    parser.add_argument("--url", action="append", dest="urls", help="URL to ingest; may be repeated")
    args = parser.parse_args()
    docs = await ingest(args.urls or OFFICIAL_URLS)
    args.output.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(docs)} chunks to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())

