# Nova Reasoning Workflows

Benchmark, results, and analysis code for the paper

> **Evaluating Reasoning Strategies for Interactive Transcriptomic Interpretation**
> Muiz Khan, Alan Carbajo, Cristiana Iosef, Suzan Arslanturk, and Sorin Draghici (2026, under review).

The study compares four reasoning workflows of *Nova* (a single-pass workflow, a fixed
multi-stage workflow, a workflow that dynamically decomposes a query across parallel
sub-agents, and an adaptive workflow that routes among them) over the same tools,
evidence, and model, and compares them with the frontier model GPT-6 used directly on the
same analysis results. Interpretation is followed from independent questions to
multi-turn conversations and stepwise evaluation of mechanistic hypotheses, on a
1,000-item, evidence-traceable benchmark built from six public transcriptomic studies.

## Contents

```
data/
  benchmark/                 the 1,000-item benchmark and its reference annotations
    S1_independent_questions.xlsx   400 independent questions (5 formats)
    S2_conversations.xlsx           30 conversations, 300 turns
    S3_hypothesis_evaluation.xlsx   30 hypotheses, 300 evidence steps, 30 final decisions
    benchmark_summary.xlsx          per-dataset summary, distributions, automated checks
  results/                   graded answers, one workbook per dataset (D1-D6)
    nova_run/                Nova run: four workflows on GLM-5.2, graded by Claude Opus 5.5
    gpt6_run/                GPT-6 run: GPT-6 used directly (Instant, Medium, High), graded by Claude Opus 5.5
    regrading_check/         robustness check: the Nova-run answers regraded by GPT-6
    robustness_subset/D1-D6/ robustness check: 192 items rerun on GLM-5.2 and Claude Haiku 4.5,
                             original and rephrased wording (15%_<model>_<wording>.xlsx)
  gpt6_run_packages/D1-D6/   exactly what GPT-6 received in the GPT-6 run: PROMPT.md, the question
                             workbook, and the iPathwayGuide result tables (data/*.tsv)
  regrading_packages/D1-D6/  the regrading check: the Nova-run answers with the reference-grader and
                             SonicChat-judge prompts, grading sheets, and the iPathwayGuide result tables
  input-datasets/            the six datasets: raw expression tables (raw_data/) and their
                             iPathwayGuide analysis results (ipathwayguide_results/<GSE>/)
prompts/                     the prompts as run: the four Nova workflows, the SonicChat judge, the
                             question rephraser, and the benchmark generation prompt with its validators
scripts/                     analysis code that recomputes every number, table, and figure
  literature_engine/         the PubMed literature engine: hybrid lexical (BM25) + semantic retrieval
  nova_cli/                  an illustrative command-line chat with the four workflows and sessions
figures/                     figures produced by the scripts (Figs. 1-4 of the paper and supplementary figures)
supplementary/supplementary_material.pdf   the paper's Supplementary Material (Tables S1-S12, Figs. S1-S7)
docs/workflow_specification.md   specification of the four Nova workflows
```

## Benchmark

Six public GEO datasets, each with a peer-reviewed publication and iPathwayGuide analysis
results (DEGs, pathways, GO terms, upstream regulators, miRNAs, and diseases):

| ID | GEO | Experiment | Publication |
|---|---|---|---|
| D1 | GSE47363 | miR-542-3p and p53 in U2OS osteosarcoma cells | Wang et al., *Cancer Research* 2014 |
| D2 | GSE147507 | SARS-CoV-2 host response | Blanco-Melo et al., *Cell* 2020 |
| D3 | GSE150316 | COVID-19 autopsy lung | Desai et al., *Nature Communications* 2020 |
| D4 | GSE26487 | Dexamethasone in epidermal keratinocytes | Stojadinovic et al., *J. Biol. Chem.* 2007 |
| D5 | GSE74000 | Acetaminophen in hepatic systems | Rodrigues et al., *Data in Brief* 2016 |
| D6 | GSE58434 | Vitamin D in airway smooth muscle | Himes et al., *PLoS One* 2015 |

| Setting | Items | What it tests |
|---|---|---|
| S1 Independent questions | 400 (143 closed-form) | Interpretation of single questions in five formats: multiple-choice, true/false, short answer, evidence integration, and mechanistic interpretation |
| S2 Multi-turn conversations | 300 turns in 30 conversations | Preserving and revising interpretations across a continuing analysis; 103 challenge turns |
| S3 Hypothesis evaluation | 300 steps in 30 hypotheses, plus 30 final decisions | Updating a mechanistic hypothesis as mixed evidence accumulates |

Every item carries **reference annotations**: the evidence needed, its provenance (source
file, row, and column, or publication passage), the expected tool category, the reasoning
chain, supporting and contradictory evidence, the expected conclusion, an *a priori*
Reasoning Requirement Level (RRL, L0-L4; `R0`-`R4` in the files), and a difficulty label.
Hypothesis steps also carry the reference evidence relation (supports, qualifies,
contradicts, or neutral) and the hypothesis state after the step; final assessments carry
the reference decision and a calibration requirement. `Generation_Source` marks items as
`MANUAL_CURATED` (300) or `LLM_ASSISTED` (700).

## Results workbooks

Each results workbook has the sheets `Run_Info`, `Summary_Wide`, `Summary_Long`,
`S1_Results`, `S2_Results`, and `S3_Results`. Item-level rows hold the question, the
reference answer, the system's answer, and its grades:

| Column(s) | Meaning |
|---|---|
| `Workflow` | Nova Instant / Thinking / Deep Thinking / Auto, or GPT-6 Instant / Medium / High |
| `Verdict`, `Credit` | Reference-based verdict (match, partial, mismatch) and credit (1, 0.5, 0); closed-form questions by exact match |
| `Ref_Correctness`, `Ref_Completeness`, `Ref_Reasoning` | Reference-based 0-10 scores (open answers) |
| `Judge_Correctness`, `Judge_Completeness`, `Judge_Reasoning`, `LLM_Judge_Overall` | Reference-free SonicChat judge scores (0-10) |
| `Hallucination_Rate` | Share of unsupported claims estimated by the SonicChat judge (reported as *unsupported claims*) |
| `Tool_Category_Match` | Whether the expected kind of evidence was retrieved |
| `Consistency_OK`, `Revision_OK` | Conversation turns: earlier facts preserved; revision made where expected |
| `Relationship_Match`, `State_Match`, `Decision_Match`, `Calibration_OK` | Hypothesis steps and final decisions against the reference annotations |
| `Total_Tokens`, `Tool_Call_Count`, `Response_Time_s` | Cost per answer |

## Reproducing the paper

```bash
python -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/nova_results.py         # Nova run: Table 5 (Nova columns), Fig. 2, statistics
.venv/bin/python scripts/gpt_comparison.py       # Nova vs GPT-6: Table 5, Fig. 3
.venv/bin/python scripts/judge_comparison.py     # regrading check: Fig. 4
.venv/bin/python scripts/robustness_results.py   # robustness subset: Table 6
.venv/bin/python scripts/main_patterns.py        # task-level analyses and reruns
.venv/bin/python scripts/mixed_evidence.py       # mixed-evidence numbers quoted in RQ3 and RQ4
.venv/bin/python scripts/overview_figure.py      # Fig. 1
```

Figures are written to `figures/`. Every number the scripts compute is written as LaTeX
macros and tables to `$NOVA_NUMBERS_DIR` (a temporary directory if unset). All scores are
macro-averaged over the six datasets.

| Paper | Script | Output |
|---|---|---|
| Fig. 1 | `overview_figure.py` | `figures/overview.png` |
| Fig. 2 | `nova_results.py` | `figures/fig_cost.pdf` |
| Fig. 3 | `gpt_comparison.py` | `figures/fig_ladder.pdf` |
| Fig. 4 | `judge_comparison.py` | `figures/fig_rq4.pdf` |
| Table 5 | `nova_results.py`, `gpt_comparison.py` | `tab_gpt.tex`, `results_macros.tex`, `gpt_macros.tex` |
| Table 6 | `robustness_results.py` | `robust_macros.tex` |

## Supplementary Material

[`supplementary/supplementary_material.pdf`](supplementary/supplementary_material.pdf) supports the paper's
statements with the underlying tables, figures, and benchmark examples. Every item comes from the files
and scripts in this repository:

| Item | Content | Source |
|---|---|---|
| Table S1 | iPathwayGuide summary of the six datasets | `data/input-datasets/ipathwayguide_results/*/experiment_info.tsv` |
| Tables S2-S4 | One benchmark item per setting with its reference annotations (NOVA-S1-D1-033, NOVA-S2-D1-T03, NOVA-S3-D1-H02), with the states declared by the systems | `data/benchmark/`, `data/results/nova_run/`, `data/results/gpt6_run/` |
| Table S5 | Qualifying evidence read as contradicting (NOVA-S3-D2-H03-S04, NOVA-S3-D4-H03-S03) | `data/benchmark/S3_hypothesis_evaluation.xlsx`, `data/results/` |
| Fig. S1 | Excerpt of the shared Nova system prompt | `prompts/nova_*/_system_prompt_build.md` |
| Table S6 | Paired workflow comparisons in credit | `scripts/nova_results.py` (`tab_pairwise.tex`) |
| Table S7 | Paired comparisons in strict accuracy and reference-based grades | `scripts/supplement_tables.py` |
| Table S8 | Credit by item type with Friedman tests | `scripts/main_patterns.py` (`tab_main_patterns.tex`) |
| Fig. S2 | Credit by Reasoning Requirement Level and difficulty | `scripts/nova_results.py` (`figures/fig_rrl.pdf`) |
| Table S9, Fig. S3 | Item-level agreement between Nova-Thinking and GPT-6 Medium | `scripts/gpt_comparison.py` (`tab_agree.tex`, `figures/fig_agree.pdf`) |
| Fig. S4 | Conversations: credit by turn position, fact preservation, revision | `scripts/nova_results.py` (`figures/fig_interactive.pdf`) |
| Fig. S5 | Suite score by dataset and workflow | `scripts/nova_results.py` (`figures/fig_datasets.pdf`) |
| Tables S10-S12 | Results under each grader, grader agreement, reference-based vs. reference-free grading | `scripts/judge_comparison.py` (`tab_judges.tex`, `tab_judge_agree.tex`, `tab_paths.tex`) |
| Fig. S6 | Robustness subset by setting, model, and wording | `scripts/robustness_results.py` (`figures/fig_robust.pdf`) |
| Fig. S7 | Worked example (NOVA-S1-D1-033 on the robustness subset) | `data/results/robustness_subset/D1/15%_glm_original.xlsx` |

Tables are written to `$NOVA_NUMBERS_DIR` by the listed scripts.

## Reproducing the GPT-6 run and the regrading check

Both external runs can be repeated with any model from the packages in `data/`:

- **GPT-6 run** (`data/gpt6_run_packages/<dataset>/`). In one new session per dataset and reasoning
  effort, attach `PROMPT.md`, the question workbook, and the result tables in `data/`. The model answers
  from the attached iPathwayGuide results only (no web or literature search), fills the `Answer` column,
  answers each conversation and hypothesis in order, and ends hypothesis steps with the status line
  requested in the question. The graded answers of the paper's run are in `data/results/gpt6_run/`.
- **Regrading check** (`data/regrading_packages/<dataset>/`). Two independent passes in separate
  sessions: `1_reference_grading/` (the reference-based grader, which sees the reference annotations but no
  data) and `2_sonicchat_judge/` (the reference-free SonicChat judge, which sees the iPathwayGuide result
  tables but never the reference annotations). Each `PROMPT.md` contains the grader's system prompt
  verbatim. The completed sheets are merged by `Row_ID`; the paper's regraded results are in
  `data/results/regrading_check/`.

In these packages, platform-specific upload instructions and the platform name were replaced with neutral
wording; the answering and grading instructions, including the verbatim grader prompts, are otherwise
unchanged. The iPathwayGuide result tables in the packages are the analysis results that Nova's tools query.

## Nova workflows

The four workflows are specified in [`docs/workflow_specification.md`](docs/workflow_specification.md),
and their prompts are in [`prompts/`](prompts) (see [`prompts/README.md`](prompts/README.md) for the
stages of each workflow). [`scripts/nova_cli/`](scripts/nova_cli) is a minimal command-line chat that
assembles the same prompts, the experiment-data tools over `data/input-datasets/`, the literature engine
in [`scripts/literature_engine/`](scripts/literature_engine), and sessions that keep every earlier turn
as context. It is an illustrative sketch of the design; running it needs a model endpoint of your own.

## Disclaimer

The prompts, code, and source files in this repository were prepared for public release and kept
generic. To protect ongoing and proprietary work, platform-specific names, internal identifiers and
version labels, product-specific instructions, and features unrelated to this study were removed or
replaced with neutral wording, and `scripts/nova_cli/` is a simplified illustration rather than the
production system. These edits do not affect reproducibility: the benchmark items, reference
annotations, model answers, grades, and scores are unchanged, and the scripts in `scripts/` reproduce
every number, table, and figure of the paper from the released files.

## License

Code (`scripts/`) is released under the [MIT License](LICENSE). The benchmark, results,
figures, prompts, and documentation (`data/`, `figures/`, `prompts/`, `docs/`) are released under
[CC BY 4.0](LICENSE-DATA.md). The six source datasets are public GEO accessions.

## Citation

```bibtex
@unpublished{khan2026nova,
  title  = {Evaluating Reasoning Strategies for Interactive Transcriptomic Interpretation},
  author = {Khan, Muiz and Carbajo, Alan and Iosef, Cristiana and Arslanturk, Suzan and Draghici, Sorin},
  year   = {2026},
  note   = {Under review}
}
```
