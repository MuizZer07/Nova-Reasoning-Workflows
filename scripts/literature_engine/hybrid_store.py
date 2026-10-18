"""
Simplified hybrid retrieval store: ChromaDB (semantic) + BM25 (lexical).
Supports upsert, search, and ensemble retrieval with configurable weights.
"""

import os
import pickle
import hashlib
from typing import List, Dict, Tuple

from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document

# ── Embedding providers (pick one) ──
# Uncomment the one you want to use:

# Option A: OpenAI embeddings
from langchain_openai import OpenAIEmbeddings

# Option B: Google Gemini embeddings
# from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Option C: Local Ollama embeddings
# from langchain_ollama import OllamaEmbeddings


# ── Defaults ──
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
BM25_PATH = os.path.join(DATA_DIR, "bm25_docs.pkl")

SEMANTIC_WEIGHT = 0.4
BM25_WEIGHT = 0.6


def _doc_hash(doc: Document) -> str:
    """Content-based hash for deduplication."""
    sig = (doc.page_content or "") + "|" + str((doc.metadata or {}).get("rag_id", ""))
    return hashlib.md5(sig.encode()).hexdigest()


class HybridStore:
    """
    Hybrid retrieval store combining:
      - ChromaDB for semantic (vector) search
      - BM25 for lexical (keyword) search
      - EnsembleRetriever to merge results with configurable weights
    """

    def __init__(
        self,
        chroma_dir: str = CHROMA_DIR,
        bm25_path: str = BM25_PATH,
        collection_name: str = "pubmed_refs",
        embedding_model: str = "text-embedding-3-small",
    ):
        os.makedirs(chroma_dir, exist_ok=True)
        os.makedirs(os.path.dirname(bm25_path), exist_ok=True)

        self.bm25_path = bm25_path

        # ── Embedding function ──
        # Option A: OpenAI
        self._emb = OpenAIEmbeddings(model=embedding_model)

        # Option B: Gemini
        # self._emb = GoogleGenerativeAIEmbeddings(
        #     model="models/gemini-embedding-001",
        #     google_api_key=os.getenv("GOOGLE_API_KEY"),
        # )

        # Option C: Local Ollama
        # self._emb = OllamaEmbeddings(model="nomic-embed-text", base_url="http://localhost:11434")

        # ── ChromaDB ──
        self._chroma = Chroma(
            embedding_function=self._emb,
            persist_directory=chroma_dir,
            collection_name=collection_name,
        )

        # ── BM25 ──
        self._bm25_docs: List[Document] = self._load_bm25()
        self._bm25 = self._build_bm25(self._bm25_docs)

        # ── Dedup registry ──
        self._known_ids: set = self._load_chroma_ids()

    # ────────── Persistence ──────────

    def _load_bm25(self) -> List[Document]:
        if os.path.exists(self.bm25_path):
            with open(self.bm25_path, "rb") as f:
                return pickle.load(f)
        return []

    def _save_bm25(self):
        with open(self.bm25_path, "wb") as f:
            pickle.dump(self._bm25_docs, f)

    def _build_bm25(self, docs: List[Document]) -> BM25Retriever:
        placeholder = [Document(page_content="__empty__")]
        bm25 = BM25Retriever.from_documents(docs if docs else placeholder)
        bm25.k = 50
        return bm25

    def _load_chroma_ids(self) -> set:
        try:
            data = self._chroma._collection.get(include=[])
            return set(data.get("ids") or [])
        except Exception:
            return set()

    # ────────── Public API ──────────

    def upsert(self, docs: List[Document]) -> Tuple[int, int]:
        """
        Add documents to both Chroma and BM25 with deduplication.
        Returns (chroma_added, bm25_added).
        """
        if not docs:
            return 0, 0

        # Filter empty and deduplicate
        new_docs, new_ids = [], []
        for d in docs:
            if not (d.page_content or "").strip():
                continue
            vid = _doc_hash(d)
            if vid not in self._known_ids:
                new_docs.append(d)
                new_ids.append(vid)
                self._known_ids.add(vid)

        if not new_docs:
            return 0, 0

        # Add to Chroma
        self._chroma.add_documents(documents=new_docs, ids=new_ids)

        # Add to BM25
        self._bm25_docs.extend(new_docs)
        self._bm25 = self._build_bm25(self._bm25_docs)
        self._save_bm25()

        print(f"[HybridStore] Added {len(new_docs)} documents (chroma + bm25)")
        return len(new_docs), len(new_docs)

    def search(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Hybrid search: combines semantic (Chroma) + lexical (BM25) results
        using an ensemble retriever with weighted scores.
        """
        self._bm25.k = max(top_k, 1)
        semantic = self._chroma.as_retriever(search_kwargs={"k": max(top_k, 1)})

        ensemble = EnsembleRetriever(
            retrievers=[semantic, self._bm25],
            weights=[SEMANTIC_WEIGHT, BM25_WEIGHT],
        )
        return ensemble.invoke(query)

    def size(self) -> Dict[str, int]:
        """Return document counts for each store."""
        try:
            chroma_count = self._chroma._collection.count()
        except Exception:
            chroma_count = 0
        return {"chroma": chroma_count, "bm25": len(self._bm25_docs)}

    def clear(self):
        """Remove all documents from both stores."""
        try:
            all_ids = self._chroma._collection.get(include=[]).get("ids", [])
            if all_ids:
                self._chroma._collection.delete(ids=all_ids)
        except Exception:
            pass

        self._bm25_docs = []
        self._bm25 = self._build_bm25([])
        self._known_ids = set()

        if os.path.exists(self.bm25_path):
            os.remove(self.bm25_path)

        print("[HybridStore] All data cleared.")
