"""
Simplified PubMed search client.
Searches PubMed, fetches metadata + full-text paragraphs from PMC,
and returns LangChain Documents ready for hybrid storage.
"""

import os
import re
import hashlib
import requests
import xml.etree.ElementTree as ET
from typing import List, Optional
from Bio import Entrez, Medline
from langchain_core.documents import Document

# ── Entrez config ──
Entrez.email = os.getenv("ENTREZ_EMAIL", "your-email@example.com")
Entrez.tool = "RefsSimplified/1.0"
Entrez.api_key = os.getenv("NCBI_API_KEY")
Entrez.max_tries = 3
Entrez.sleep_between_tries = 1

# Auto-incrementing document counter
_rag_counter = 0


def _next_rag_id() -> int:
    global _rag_counter
    _rag_counter += 1
    return _rag_counter


def search_pubmed(query: str, max_results: int = 10) -> List[str]:
    """Search PubMed and return PMIDs."""
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="relevance")
    results = Entrez.read(handle)
    handle.close()
    return results.get("IdList", [])


def fetch_medline_records(pmids: List[str]) -> List[dict]:
    """Fetch Medline metadata for a list of PMIDs."""
    if not pmids:
        return []
    handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="medline", retmode="text")
    records = list(Medline.parse(handle))
    handle.close()
    return records


def _get_pmc_id(pmid: str) -> Optional[str]:
    """Look up PMC ID for a given PMID."""
    try:
        xml_rec = Entrez.read(Entrez.efetch(db="pubmed", id=pmid, retmode="xml"))
        article = xml_rec["PubmedArticle"][0]
        for id_item in article["PubmedData"]["ArticleIdList"]:
            if id_item.attributes.get("IdType") == "pmc":
                return str(id_item)
    except Exception:
        pass
    return None


def _download_fulltext(pmc_id: str) -> List[str]:
    """Download full-text paragraphs from PMC via BioC XML."""
    url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmc_id}/unicode"
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        return []
    try:
        root = ET.fromstring(resp.text)
        return [
            p.find("text").text.strip()
            for p in root.iter("passage")
            if p.find("text") is not None and p.find("text").text
        ]
    except ET.ParseError:
        return []


def _extract_keywords(query: str) -> List[str]:
    """Extract keyword tokens from a query string."""
    cleaned = re.sub(r"[^\w\s-]", "", query)
    tokens = cleaned.lower().split()
    stop = {"and", "or", "not", "the", "of", "in", "for", "a", "an", "with", "from", "by"}
    return list({t for t in tokens if t not in stop and len(t) > 2})


def fetch_documents(query: str, max_results: int = 10) -> List[Document]:
    """
    End-to-end: search PubMed → fetch metadata → get full-text paragraphs
    → filter by keyword relevance → return as LangChain Documents.
    """
    pmids = search_pubmed(query, max_results)
    records = fetch_medline_records(pmids)
    keywords = _extract_keywords(query)

    docs: List[Document] = []
    for rec in records:
        pmid = rec.get("PMID")
        if not pmid:
            continue

        title = rec.get("TI", "")
        authors = rec.get("AU", [])
        source = rec.get("SO", "")
        abstract = rec.get("AB", "") or ""

        pmc_id = _get_pmc_id(pmid)
        paragraphs = _download_fulltext(pmc_id) if pmc_id else []

        # Keep paragraphs that mention at least one keyword
        matched = [p for p in paragraphs if any(k in p.lower() for k in keywords)]

        # If no full-text matches, use the abstract as a fallback
        if not matched and abstract:
            matched = [abstract]

        for para in matched:
            content_hash = hashlib.md5(para.encode()).hexdigest()
            docs.append(Document(
                page_content=para,
                metadata={
                    "rag_id": _next_rag_id(),
                    "pmid": pmid,
                    "pmc_id": pmc_id or "",
                    "title": title,
                    "authors": ", ".join(authors),
                    "authors_short": (authors[0] + " et al.") if len(authors) > 1 else ", ".join(authors),
                    "abstract": abstract[:500],
                    "source": source,
                    "chunk_id": f"{pmid}:{content_hash}",
                },
            ))
    return docs
