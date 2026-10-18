"""
Simplified reference retrieval pipeline.

Usage:
    python main.py "BRCA1 DNA repair mechanisms"
    python main.py "TP53 apoptosis signaling pathway" --max-results 15 --top-k 10
"""

import argparse
from pubmed_search import fetch_documents
from hybrid_store import HybridStore


def run(query: str, max_results: int = 10, top_k: int = 5):
    store = HybridStore()

    # Step 1 — Fetch from PubMed and store in hybrid DB
    print(f"\n[1/3] Searching PubMed for: '{query}' (max {max_results} articles)...")
    docs = fetch_documents(query, max_results=max_results)
    print(f"      Found {len(docs)} document chunks.")

    # Step 2 — Upsert into hybrid store (Chroma + BM25)
    print(f"[2/3] Upserting into hybrid store...")
    chroma_added, bm25_added = store.upsert(docs)
    sizes = store.size()
    print(f"      Store totals → Chroma: {sizes['chroma']}, BM25: {sizes['bm25']}")

    # Step 3 — Hybrid retrieval
    print(f"[3/3] Running hybrid search (top {top_k})...\n")
    results = store.search(query, top_k=top_k)

    for i, doc in enumerate(results, 1):
        md = doc.metadata
        print(f"── Result {i} ──")
        print(f"  PMID:    {md.get('pmid', 'N/A')}")
        print(f"  Title:   {md.get('title', 'N/A')}")
        print(f"  Authors: {md.get('authors_short', md.get('authors', 'N/A'))}")
        print(f"  Source:  {md.get('source', 'N/A')}")
        print(f"  Snippet: {doc.page_content[:200]}...")
        print()

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PubMed → Hybrid DB search pipeline")
    parser.add_argument("query", help="PubMed search query")
    parser.add_argument("--max-results", type=int, default=10, help="Max PubMed articles to fetch")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K results from hybrid search")
    args = parser.parse_args()

    run(args.query, max_results=args.max_results, top_k=args.top_k)
