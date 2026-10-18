"""Experiment-data and literature tools over one dataset's iPathwayGuide results.

Each tool reads the result tables in data/input-datasets/ipathwayguide_results/<GSE>/ and returns
plain records with the exact values, so the workflows can quote them. Named entities are looked up
directly in the full tables, never inferred from a truncated ranking.
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(REPO, "data", "input-datasets", "ipathwayguide_results")


class ExperimentTools:
    def __init__(self, gse: str):
        self.dir = os.path.join(RESULTS, gse)
        if not os.path.isdir(self.dir):
            raise FileNotFoundError(f"no iPathwayGuide results for {gse} in {RESULTS}")
        self.gse = gse
        self._cache: dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------ helpers
    def _t(self, name: str) -> pd.DataFrame:
        if name not in self._cache:
            path = os.path.join(self.dir, name)
            self._cache[name] = pd.read_csv(path, sep="\t") if os.path.getsize(path) else pd.DataFrame()
        return self._cache[name]

    @staticmethod
    def _records(df: pd.DataFrame, cols: list[str], n: int | None = None) -> list[dict]:
        cols = [c for c in cols if c in df.columns]
        return json.loads(df[cols].head(n).to_json(orient="records")) if n else json.loads(df[cols].to_json(orient="records"))

    # ------------------------------------------------------------------ tools
    def get_experiment_info(self) -> dict:
        info = self._t("experiment_info.tsv").iloc[0]
        return {"experiment": info["report_title"],
                "contrast": f'{info["experiment_condition_1"]} vs {info["experiment_condition_2"]}',
                "genes_measured": int(info["total_number_of_genes"]),
                "de_genes": int(info["total_number_of_de_genes"])}

    def get_gene_expression(self, genes: list[str]) -> list[dict]:
        df = self._t("gene_analyses.tsv")
        hits = df[df["symbol"].str.upper().isin([g.upper() for g in genes])]
        found = self._records(hits, ["symbol", "logfc", "adjpv"])
        missing = sorted(set(g.upper() for g in genes) - set(hits["symbol"].str.upper()))
        return found + [{"symbol": g, "status": "not measured in this experiment"} for g in missing]

    def get_top_DEGs(self, n: int = 20, direction: str | None = None) -> list[dict]:
        df = self._t("gene_analyses.tsv").copy()
        if direction == "up":
            df = df[df["logfc"] > 0]
        elif direction == "down":
            df = df[df["logfc"] < 0]
        return self._records(df.sort_values("adjpv"), ["symbol", "logfc", "adjpv"], n)

    def get_top_significant_pathways(self, n: int = 10) -> list[dict]:
        return self._records(self._t("pathway_analyses.tsv").sort_values("pComb"),
                             ["pName", "pORA", "pORA_fdr", "pAcc", "pAcc_fdr", "pComb", "pComb_fdr"], n)

    def get_pathway_by_name(self, name: str) -> list[dict]:
        df = self._t("pathway_analyses.tsv")
        return self._records(df[df["pName"].str.contains(name, case=False, regex=False)],
                             ["pName", "pORA", "pORA_fdr", "pAcc", "pAcc_fdr", "pComb", "pComb_fdr"])

    def get_upstream_regulator(self, name: str) -> list[dict]:
        df = self._t("upstream_gene.tsv")
        return self._records(df[df["symbol"].str.upper() == name.upper()],
                             ["symbol", "zscore", "cDE", "cDE_p", "cDE_n", "pv", "pv_fdr", "logfc", "adjpv"]) \
            or [{"symbol": name, "status": "not among the predicted upstream regulators"}]

    def get_top_upstream_regulators(self, n: int = 10) -> list[dict]:
        return self._records(self._t("upstream_gene.tsv").sort_values("pv"),
                             ["symbol", "zscore", "cDE", "cDE_p", "cDE_n", "pv", "pv_fdr", "logfc", "adjpv"], n)

    def get_top_GO_terms(self, ontology: str = "BP", n: int = 10) -> list[dict]:
        return self._records(self._t(f"go_analyses_{ontology.upper()}.tsv").sort_values("pv"),
                             ["goName", "countDE", "countAll", "pv", "pv_fdr", "pv_elim"], n)

    def get_top_miRNAs(self, n: int = 10) -> list[dict]:
        return self._records(self._t("mirna_analyses.tsv").sort_values("pv"),
                             ["mirnaName", "cDE", "cAll", "cDE_p", "cDE_n", "pv", "pv_fdr", "pvn", "pvn_fdr"], n)

    def get_top_diseases(self, n: int = 10) -> list[dict]:
        return self._records(self._t("disease_analyses.tsv").sort_values("pv"),
                             ["diseaseName", "countDE", "countAll", "pv", "pv_fdr"], n)

    @staticmethod
    def search_literature(query: str, top_k: int = 5) -> list[dict]:
        """PubMed through the hybrid lexical + semantic literature engine (scripts/literature_engine)."""
        sys.path.insert(0, os.path.join(REPO, "scripts", "literature_engine"))
        from main import run  # noqa: E402  (imported lazily: needs PubMed access)
        docs = run(query, max_results=10, top_k=top_k)
        return [{"pmid": d.metadata.get("pmid"), "title": d.metadata.get("title"),
                 "snippet": d.page_content[:400]} for d in docs]

    # ------------------------------------------------------------------ registry
    CAPABILITIES = {
        "experiment_data": ["get_experiment_info", "get_gene_expression", "get_top_DEGs",
                            "get_top_significant_pathways", "get_pathway_by_name", "get_upstream_regulator",
                            "get_top_upstream_regulators", "get_top_GO_terms", "get_top_miRNAs", "get_top_diseases"],
        "literature_tools": ["search_literature"],
    }

    def call(self, name: str, args: dict):
        if name not in sum(self.CAPABILITIES.values(), []):
            return {"error": f"unknown tool {name}"}
        try:
            return getattr(self, name)(**args)
        except Exception as e:  # report tool errors instead of inventing output
            return {"error": str(e)}


def tool_schemas(capabilities: list[str] | None = None) -> list[dict]:
    """OpenAI-style function schemas for the tools in the given capability categories."""
    s = lambda name, desc, props=None, req=None: {  # noqa: E731
        "type": "function", "function": {"name": name, "description": desc,
                                         "parameters": {"type": "object", "properties": props or {},
                                                        "required": req or []}}}
    n = {"n": {"type": "integer"}}
    all_ = {
        "get_experiment_info": s("get_experiment_info", "Experiment title, contrast, and gene/DE counts."),
        "get_gene_expression": s("get_gene_expression", "logFC and adjusted p for each named gene (direct lookup).",
                                 {"genes": {"type": "array", "items": {"type": "string"}}}, ["genes"]),
        "get_top_DEGs": s("get_top_DEGs", "Top DE genes by adjusted p.",
                          {**n, "direction": {"type": "string", "enum": ["up", "down"]}}),
        "get_top_significant_pathways": s("get_top_significant_pathways", "KEGG pathways: ORA, perturbation, combined.", n),
        "get_pathway_by_name": s("get_pathway_by_name", "Direct lookup of a named pathway.",
                                 {"name": {"type": "string"}}, ["name"]),
        "get_upstream_regulator": s("get_upstream_regulator", "Direct lookup of a named upstream regulator.",
                                    {"name": {"type": "string"}}, ["name"]),
        "get_top_upstream_regulators": s("get_top_upstream_regulators", "Predicted upstream regulators.", n),
        "get_top_GO_terms": s("get_top_GO_terms", "GO enrichment (BP, MF, or CC).",
                              {**n, "ontology": {"type": "string", "enum": ["BP", "MF", "CC"]}}),
        "get_top_miRNAs": s("get_top_miRNAs", "Predicted upstream miRNAs.", n),
        "get_top_diseases": s("get_top_diseases", "Disease associations.", n),
        "search_literature": s("search_literature", "PubMed search (hybrid lexical + semantic retrieval).",
                               {"query": {"type": "string"}, "top_k": {"type": "integer"}}, ["query"]),
    }
    caps = capabilities or list(ExperimentTools.CAPABILITIES)
    names = sum((ExperimentTools.CAPABILITIES[c] for c in caps if c in ExperimentTools.CAPABILITIES), [])
    return [all_[x] for x in names]
