# Nova Benchmark — Generation Prompt (v2)

How to use this prompt:
- Paste everything below the line "BEGIN PROMPT" into a chatbot that can read uploaded files. A chatbot that can also run Python (code interpreter or agent mode) works best.
- Upload the Nova folder contents for the dataset(s) you are generating: the publication PDF plus the `data/*.tsv` and `data/*.json` files.
- The full benchmark has 1,000 items, which is far more than one chat reply can hold. Run it as 18 jobs: 6 datasets × 3 settings. Each job uses the same prompt plus a one-line JOB header, for example `JOB: dataset=D3, setting=2`.
- Jobs for the same dataset should run in this order: Setting 3, then Setting 2, then Setting 1. Upload the files from earlier jobs so the later jobs can avoid duplicate questions.
- The two validators (`validate_items.py`, `validate_v2.py`, saved next to this prompt) reproduce the automatic checks used for v2. Run them on each JSON file when the chatbot can execute code.

---------------------------------------------------------------------- BEGIN PROMPT

You are constructing part of **Nova**, a benchmark that evaluates evidence-grounded scientific and mechanistic reasoning over transcriptomic experiments. You will author benchmark items for ONE dataset and ONE setting, given in the JOB line at the end of this prompt. You have been given:
1. the peer-reviewed publication associated with the dataset (PDF), and
2. structured analysis results for that dataset, exported from iPathwayGuide (TSV/JSON files described in Section 2).

Work carefully, verify every number against the files, and follow every rule. Quality matters more than speed.

## 1. What the benchmark tests

Nova tests whether a reasoning system can interpret a transcriptomic experiment mechanistically:
- identify coordinated gene programs;
- name and interpret pathways and processes, including their direction;
- distinguish a regulator's inferred activity from its own mRNA change;
- integrate evidence across layers;
- recognise feedback, alternative mechanisms, cell-composition effects and conflicts with the publication;
- make evidence-based perturbation predictions;
- calibrate conclusions when evidence is insufficient.

This is **not** a general biology exam, and **not** a quiz about statistics, thresholds or file contents.

## 2. Inputs and how to read them

First, inspect all files and the paper before writing anything. Write down (privately, for your own use):
- the Dataset_ID;
- the publication citation;
- the experimental context and contrast (as far as the metadata states it);
- which evidence layers are present;
- the paper's main claims, each with its section, figure or table.

File semantics (iPathwayGuide export; paths are relative to `data/`):

- **gene_analyses.tsv**: `symbol`, `logfc`, `adjpv`.
  - Differentially expressed (DE) means adjpv < 0.05 and |logFC| > 0.6, unless `experiment_info.tsv` says otherwise.
  - adjpv values are floored at 1e-6. logFC values of exactly ±10 are capped (usually zero counts in one group).
  - A row with logFC exactly 0 and adjpv 1 is an uninformative placeholder, not evidence of "no change".
- **pathway_analyses.tsv** (KEGG impact analysis):
  - `pORA` is over-representation.
  - `pAcc` is propagated perturbation through the pathway topology. A pAcc of 0 together with totalAcc 0 means there is no topology evidence.
  - `pv` / `pv_fdr` are the combined result.
  - `totalAcc` sign is the predicted net direction.
  - Over-representation without perturbation shows that members changed, not which direction the pathway moved.
- **pathway_gene_associations.tsv** and **go_*_terms.tsv** (present only for some datasets): the DE member genes of each pathway or term. When these files are absent, gene membership is NOT given. Any statement that a particular gene drives a term must then be hedged as an inference.
- **go_analyses_BP/MF/CC.tsv**: `pv_fdr` is the classic result. `pv_elim` and `pv_weight` are topology-aware: a term that loses significance under weighting is redundant with its child terms.
- **upstream_gene.tsv** (upstream regulators inferred from their targets):
  - `cDE` is the number of DE targets.
  - `cDE_p` and `cDE_n` count targets consistent with activation and with inhibition.
  - `zscore` sign gives the predicted state. `pv_comb_p_fdr` and `pv_comb_n_fdr` are the direction-aware FDRs.
  - `logfc` and `adjpv` are the regulator's OWN mRNA change. logfc 0 together with adjpv 0 means the regulator's own mRNA was not measured.
  - Several regulators with identical statistics share one annotated target set. Count them as one piece of evidence, not several independent regulators.
- **upstream_chemical_positive/negative.tsv**: the same table in two sort orders.
  - zscore > 0: the changed genes mimic the compound's effect.
  - zscore < 0: the changes oppose it.
  - These are transcriptional-connectivity evidence only, never treatment claims.
- **mirna_analyses.tsv**:
  - `cDE_p` and `cDE_n` count DE targets that went up and down.
  - `pvn` / `pvn_fdr` measure enrichment of DOWN-regulated targets, consistent with that miRNA being active.
  - `pv` / `pv_fdr` measure direction-agnostic over-representation.
- **disease_analyses.tsv**: direction-agnostic overlap with disease gene sets.
- **enrichment_collection_XX.tsv**: 29 = MSigDB Hallmark, 30 = Oncogenic (C6), 31 = Immunologic (C7), 32 = Cell-type (C8), 70 = Advaita organ signatures, 76 = Advaita toxicity signatures. All are direction-agnostic.
- **experiment_info.tsv** and **summary.tsv**: metadata and top-ranked lists. The "significant" counts in experiment_info are nominal p < 0.05, not FDR. summary.tsv ranks genes by logFC regardless of significance.

Dataset-specific caveats (contrast identity, annotation artifacts, paper limitations) are in **Appendix A**. Respect them.

## 3. Global grounding rules (apply to every item)

1. Every question must be answerable from the supplied structured results, the publication, or an explicitly identified combination of the two.
2. Never invent genes, values, pathways, regulators, miRNAs, statistics, diseases, mechanisms or findings. Never use your parametric biology knowledge as ground truth. Light annotation knowledge (e.g., "LILRB2 is characteristic of monocytes") may appear only as a clearly labelled interpretation.
3. Copy every number from the files. Round sensibly: logFC to 2 decimals, p/FDR to 2–3 significant figures. If you can run code, verify each value with pandas.
4. Distinguish **experimental observation** (a data value) from **biological interpretation**. Treat the publication's conclusions as reference interpretations, not absolute truth.
5. Never assert an unverified contrast identity as fact (see Appendix A). Use the dataset's standard phrase from Appendix A.
6. Report contradictory or limiting evidence only when it genuinely exists. Examples: a regulator's mRNA is not DE; a gene the paper highlights is not significant here; a pathway is over-represented but has no perturbation; a logFC is capped; targets point in opposite directions. Otherwise write exactly `NONE IDENTIFIED`. Never manufacture contradiction to make an item harder.
7. When the evidence is insufficient, the reference answer must say so explicitly.
8. Do not leak the answer in the question. MCQ distractors must be REAL entities from the same files that are wrong for the property asked about, e.g., a pathway that exists but is not significant. Never use an invented result as a distractor.
9. Provenance must be specific: file + row key + columns, e.g. `data/upstream_gene.tsv [symbol=TP53: zscore, cDE_p, cDE_n, pv_comb_p_fdr]`. For the paper, give section/figure/table, e.g. `Publication: Results 'miR-542-3p induces ribosomal p53 response'; Fig. 3C`. Separate multiple sources with ` ; `.
10. Evidence-layer tokens, separated by ` ; `: DEG, PATHWAY, GO, UPSTREAM_REGULATOR, MIRNA, DISEASE, PHENOTYPE, LITERATURE, OTHER. OTHER covers MSigDB/Advaita collections, chemicals and design facts. Setting 3 may also use TARGET_GENE_DIRECTIONALITY, CONTRADICTORY_EVIDENCE, LIMITING_EVIDENCE and ALTERNATIVE_MECHANISMS.

## 4. Banned naive questions (v2 — strictly enforced)

The QUESTION text must never:
- ask about thresholds, cut-offs or DE criteria, or ask for DE counts;
- ask "how many", "number of", "what fraction", "what proportion" or "percentage" of anything;
- ask for the logFC, p-value, adjusted p, FDR, q-value, z-score or Bonferroni value of anything. Numbers belong in the reference answer as evidence, never as the thing asked for;
- ask which contrast or comparison was analysed, or ask about the platform, replicates, sample size, time point, dose or concentration;
- ask about metadata, files, columns, placeholders or capped values;
- be a single-gene "is X differentially expressed / up-regulated?" TRUE/FALSE lookup.

The question must not contain these words: threshold, cutoff, cut-off, logFC, log2 fold-change value, p-value, adjusted p, FDR, q-value, z-score, Bonferroni, how many, number of, metadata, column, file, placeholder, capped. Phrase statistical caveats biologically, e.g. "Is this conclusion statistically supported?" or "How confident can we be that…?".

## 5. Reasoning Requirement Level (RRL) and Difficulty

Assign exactly one RRL to each item:
- **R0 – Direct retrieval of a NAMED biological entity.** Ask which pathway / GO process / upstream regulator / miRNA / gene program / disease term / cell-type signature / chemical best matches a biological description. Good example: "Which KEGG pathway captures the coordinated changes in CDKN1A, MDM2, GADD45A, BAX and SESN1?" Bad example: "What is the p-value of the p53 pathway?"
- **R1 – Local interpretation** within one layer.
- **R2 – Cross-layer integration** of at least two layers (e.g., DEG + PATHWAY, REGULATOR + TARGETS, GO + PATHWAY, MIRNA + DEG).
- **R3 – Mechanistic synthesis**: an explanatory chain such as regulator -> target genes -> observed expression -> pathway/process -> phenotype.
- **R4 – Critical mechanistic reasoning**: supporting vs contradictory evidence, alternatives, missing evidence, uncertainty, competing interpretations, calibration, revision.

Assign Difficulty (EASY / MODERATE / HARD / EXPERT) independently of RRL. Judge it by:
- the number of evidence elements and layers;
- ambiguity and conflicting evidence;
- the number of reasoning steps;
- whether competing explanations must be compared;
- how much prior context is needed;
- how much calibration is demanded.

Do NOT map RRL to Difficulty mechanically. For R2–R4 items, spell out the evidence relationships as `->` chains.

## 6. Diversity rules (v2 — strictly enforced)

Tag every item, turn and step with two keys:
- **Reasoning_Category** — exactly one of:
  - DEG_PROGRAM
  - PATHWAY_IDENTIFICATION
  - PATHWAY_DIRECTIONALITY
  - GO_PROCESS
  - UPSTREAM_REGULATOR
  - MIRNA_REGULATION
  - CHEMICAL_CONNECTIVITY
  - CELL_COMPOSITION
  - DISEASE_PHENOTYPE
  - CROSS_LAYER_CONSISTENCY
  - MECHANISTIC_CHAIN
  - FEEDBACK_COUNTERREGULATION
  - PUBLICATION_CONCORDANCE
  - ALTERNATIVE_MECHANISM
  - PERTURBATION_PREDICTION — predict, from the supplied evidence, what would change if a regulator or pathway were blocked or enhanced, and what observation would confirm it. Never clinical advice.
  - EVIDENCE_CALIBRATION
  - TRANSCRIPTIONAL_VS_POSTTRANSCRIPTIONAL
- **Primary_Entity** — the main gene, pathway, regulator, miRNA or process the item is about, as a short string.

**Setting 1 limits:**
- at least 14 distinct categories;
- no category used more than 8 times;
- no two items with the same (Reasoning_Category, Primary_Entity) pair;
- at most 5 EVIDENCE_CALIBRATION items, each about a biological conclusion rather than file mechanics;
- R0 items may use only these categories: PATHWAY_IDENTIFICATION, UPSTREAM_REGULATOR, MIRNA_REGULATION, GO_PROCESS, DEG_PROGRAM, DISEASE_PHENOTYPE, CELL_COMPOSITION, CHEMICAL_CONNECTIVITY.

**Settings 2 and 3 limits:**
- each trajectory or hypothesis uses at least 4 categories;
- the dataset's file uses at least 12 categories in total.

**For every setting:**
- no near-duplicate questions within the dataset, across all three settings;
- never reuse one question template with a swapped gene name more than once.

**Coverage expected for each dataset, across its three settings:**
- gene programs;
- pathway identity and direction (perturbation vs over-representation, explained biologically);
- GO processes, compartments and functions;
- upstream regulators vs their own mRNA;
- miRNA regulation;
- chemicals (where present);
- cell composition vs cell-intrinsic change;
- disease/phenotype links;
- feedback and counter-regulation;
- full mechanistic chains;
- concordance and divergence with the publication;
- alternative mechanisms;
- perturbation predictions;
- calibrated uncertainty.

**Themes:** use the theme allocation in **Appendix B**. Settings 2 and 3 of the same dataset must investigate different primary mechanisms. Setting 1 should span all themes plus anything else that is well supported.

## 7. Generation-source labels

You cannot certify that a human has reviewed anything, so use only:
- `MANUAL_CURATED_CANDIDATE` for the highest-value items: central mechanisms of the paper, R2–R4, multi-layer, meaningful uncertainty;
- `LLM_ASSISTED_REVIEW_PENDING` for all others.

Human_Review_Status is always `PENDING` and Reviewer_Notes is blank. These labels are converted to MANUAL_CURATED or LLM_ASSISTED_REVIEWED only after real human review.

## 8. Exact targets per dataset

| Dataset | Setting 1 items | S1 RRL R0/R1/R2/R3/R4 | S1 manual candidates | Setting 2 turn counts per trajectory | Setting 3 step counts per hypothesis |
|---|---|---|---|---|---|
| D1 | 67 | 7/10/17/20/13 | 17 | [9, 8, 11, 11, 11] | [9, 8, 11, 11, 11] |
| D2 | 67 | 7/10/17/20/13 | 17 | [8, 9, 11, 11, 11] | [8, 9, 11, 11, 11] |
| D3 | 67 | 7/10/17/20/13 | 17 | [9, 8, 11, 11, 11] | [9, 8, 11, 11, 11] |
| D4 | 67 | 7/10/17/20/13 | 17 | [8, 9, 11, 11, 11] | [8, 9, 11, 11, 11] |
| D5 | 66 | 7/10/16/20/13 | 16 | [8, 8, 12, 11, 11] | [8, 8, 12, 11, 11] |
| D6 | 66 | 7/10/16/20/13 | 16 | [8, 8, 12, 11, 11] | [8, 8, 12, 11, 11] |

In Settings 2 and 3, the first two trajectories or hypotheses are MANUAL_CURATED_CANDIDATE and the other three are LLM_ASSISTED_REVIEW_PENDING. This gives exactly 100 manual candidates per setting across the six datasets.

Totals:
- Setting 1: 400 items.
- Setting 2: 300 turns in 30 trajectories.
- Setting 3: 300 steps in 30 hypotheses.
- Grand total: 1,000.

## 9. Setting specifications

### Setting 1 — single-turn mechanistic reasoning

Each item stands alone.
- Question_Type is one of: MCQ, TRUE_FALSE, SHORT_ANSWER, EVIDENCE_INTEGRATION, MECHANISTIC_INTERPRETATION.
- MCQ and TRUE_FALSE are used mainly for R0–R2. The other types are used mainly for R2–R4.
- Suggested mix per dataset: about 14 MCQ, 8 TRUE_FALSE, 13 SHORT_ANSWER, 16 EVIDENCE_INTEGRATION and 15–16 MECHANISTIC_INTERPRETATION.
- Balance TRUE and FALSE answers, and vary which MCQ letter is correct.

Fields, in this order:

| Field | Content |
|---|---|
| Generation_Source | Label from Section 7 |
| Question_Type | One of the five types above |
| RRL | R0–R4 |
| Difficulty | EASY / MODERATE / HARD / EXPERT |
| Question | The question text |
| Option_A, Option_B, Option_C, Option_D | MCQ only; blank ("") otherwise |
| Correct_Answer | MCQ: `"B | <exact option text>"`; TRUE_FALSE: `TRUE` or `FALSE`; other types: a concise answer |
| Reference_Answer | Complete answer, typically 2–6 sentences with the key numbers |
| Required_Evidence | Pieces of evidence, ` ; ` separated |
| Evidence_Layers | Layer tokens from Section 3 |
| Evidence_Provenance | Specific sources, per rule 9 |
| Required_Reasoning_Relations | The `->` chain |
| Supporting_Evidence | ` ; ` separated |
| Contradictory_Evidence | Genuine contradictions, or `NONE IDENTIFIED` |
| Expected_Conclusion | The conclusion a correct answer reaches |
| Acceptable_Alternative | Another defensible interpretation, or `NONE` |
| Rationale_for_RRL | Why this RRL |
| Rationale_for_Difficulty | Why this Difficulty |
| Reasoning_Category | From Section 6 |
| Primary_Entity | From Section 6 |
| checks | List of machine-checkable facts (Section 10) |

### Setting 2 — interactive / conversational reasoning

Each trajectory simulates a researcher progressively investigating ONE interpretation:
- Later turns MUST genuinely depend on evidence, conclusions or uncertainties established earlier. Refer back, e.g. "the pathway identified above", "the regulator you proposed", without revealing what the system was expected to conclude.
- Turn 1 must already be biologically meaningful.
- Every trajectory has at least one challenge turn: justify, search for contradiction, consider an alternative mechanism, explain uncertainty, reassess or revise.
- Across the dataset's 5 trajectories, include later evidence that SUPPORTS, WEAKENS, QUALIFIES and REQUIRES REVISION of the earlier interpretation. At least one turn must have Revision_Expected = YES.
- Do not apply one template mechanically. A possible arc is observation -> clarification -> molecular evidence -> cross-layer integration -> mechanism -> challenge -> alternative -> additional evidence -> refinement -> calibrated interpretation.

Trajectory fields:
- Generation_Source
- Trajectory_Goal
- Starting_Biological_Question
- Overall_Difficulty
- Expected_Final_Interpretation
- Primary_Mechanism
- Primary_Uncertainty
- turns (list)

Turn fields:

| Field | Content |
|---|---|
| Question | The turn's question |
| RRL, Difficulty | As in Section 5 |
| Depends_On | List of earlier turn numbers; [] for turn 1 |
| Prior_Evidence_Required | What earlier information is needed; "NONE" for turn 1 |
| New_Evidence_Required | What new evidence this turn needs |
| Evidence_Layers | Layer tokens |
| Evidence_Provenance | Specific sources |
| Required_Reasoning | The reasoning the turn requires |
| Reference_Answer | Complete answer |
| Supporting_Evidence | ` ; ` separated |
| Contradictory_Evidence | Genuine contradictions, or `NONE IDENTIFIED` |
| Consistency_Constraint | Facts or numbers from earlier turns that must stay consistent |
| Revision_Expected | YES / NO |
| Expected_Revision | What should change; "NONE" if NO |
| Challenge_Turn | YES / NO |
| Rationale_for_Difficulty | Why this Difficulty |
| Reasoning_Category, Primary_Entity | From Section 6 |
| checks | Machine-checkable facts |

### Setting 3 — hypothesis evaluation and revision

Each trajectory starts from one hypothesis H0 that is:
- relevant to the experiment;
- mechanistic rather than descriptive;
- testable with multiple evidence layers;
- neither trivially true nor trivially false;
- specific. A typical form is "activation/inhibition of regulator X contributes to phenotype Y through pathway/process Z".

Evidence accumulates step by step: E1 -> interim assessment -> E2 -> updated assessment -> … -> challenge -> alternative -> more evidence -> final assessment.
- Every step evaluates the SAME H0 or a justified revision of it.
- At least one step critically tests H0 (CONTRADICTS, QUALIFIES, or explicit limiting evidence).
- No trajectory may be confirmation-only. If contradictory evidence does not exist, evaluate missing evidence, uncertainty, limitations and alternatives instead; never invent contradiction.
- The LAST step is the final synthesis. It asks, in natural language, whether the accumulated evidence means H0 should be retained, qualified, revised, rejected, or considered insufficiently supported.
  - It must depend on most of the prior steps.
  - It must not retrieve a new fact.
  - Vary its wording between hypotheses.
- Across the dataset's 5 hypotheses, final Decisions must vary; they cannot all be RETAIN.
- States chain: Hypothesis_State_Before of step k equals Hypothesis_State_After of step k-1. Step 1's Before equals Initial_Evidence_Status, which is normally INSUFFICIENT_EVIDENCE.

State values: SUPPORTED, PARTIALLY_SUPPORTED, INSUFFICIENT_EVIDENCE, WEAKENED, CONTRADICTED.

Hypothesis fields:
- Generation_Source
- Initial_Hypothesis
- Biological_Rationale
- Primary_Mechanism
- Evidence_Layers_Available
- Initial_Evidence_Status
- Overall_Difficulty
- Expected_Final_State (equals the last step's After state)
- Reference_Revised_Hypothesis (or "NONE")
- steps (list)
- final (object)

Step fields:

| Field | Content |
|---|---|
| Question | The step's question |
| RRL, Difficulty | As in Section 5 |
| Depends_On | List of earlier step numbers |
| Evidence_Being_Tested | What this step tests |
| Evidence_Layer | Layer tokens (Setting 3 extras allowed) |
| Evidence_Provenance | Specific sources |
| Reference_Evidence | The actual evidence values |
| Expected_Reasoning | The reasoning the step requires |
| Evidence_Relationship_to_Hypothesis | SUPPORTS / CONTRADICTS / QUALIFIES / NEUTRAL |
| Hypothesis_State_Before, Hypothesis_State_After | State values |
| Revision_Expected | YES / NO |
| Revised_Hypothesis | The revised text, or "NONE" |
| Supporting_Evidence | ` ; ` separated |
| Contradictory_or_Limiting_Evidence | Genuine contradictions or limits, or `NONE IDENTIFIED` |
| Alternative_Explanation | Another explanation, or "NONE" |
| Rationale_for_Difficulty | Why this Difficulty |
| Reasoning_Category, Primary_Entity | From Section 6 |
| checks | Machine-checkable facts |

final object fields:
- Reference_Final_Answer
- Supporting_Evidence_Summary
- Contradictory_or_Limiting_Evidence_Summary
- Alternative_Explanation
- Final_Hypothesis_State (equals the last step's After state)
- Decision: RETAIN / QUALIFY / REVISE / REJECT / INSUFFICIENT_EVIDENCE
- Reference_Revised_Hypothesis
- Calibration_Requirement: the confidence level or hedging a correct answer must show
- Evidence_Provenance_Summary

## 10. Machine-checkable facts ("checks")

Every item, turn and step carries a `checks` list with the 1–6 key data facts it relies on, for example:

`{"file": "gene_analyses.tsv", "key_col": "symbol", "key": "TP53", "col": "logfc", "value": 0.263}`

Key columns by file:

| File | key_col |
|---|---|
| gene_analyses.tsv | symbol |
| upstream_gene.tsv | symbol |
| pathway_analyses.tsv | pName |
| go_analyses_*.tsv | goName or goId |
| mirna_analyses.tsv | mirnaName |
| disease_analyses.tsv | diseaseName |
| enrichment_collection_XX.tsv | gene_set_name |
| upstream_chemical_positive.tsv | chemicalName |

The value is the number (or category) exactly as you state it in the text. Rounding is tolerated. Items that rest only on the publication or on synthesis may have an empty list.

## 11. Output format

Return ONE JSON object:
- **Setting 1:** `{"dataset": "<DK>", "setting": 1, "items": [...]}`
- **Setting 2:** `{"dataset": "<DK>", "setting": 2, "trajectories": [...]}`
- **Setting 3:** `{"dataset": "<DK>", "setting": 3, "hypotheses": [...]}`

Use plain ASCII where possible ("beta", "->").

**If you can run code:**
- Build the JSON with a script.
- Write it in small batches: at most 6 Setting-1 items, or 1 trajectory/hypothesis, per edit. Assemble with a build script.
- Run `python3 validate_v2.py <file>`. It requires `validate_items.py` and the dataset folder; set the environment variable NOVA_ROOT to the folder that contains the six dataset folders.
- Fix every ERROR until the file prints VALID.

**If you cannot run code:**
- Output the JSON in consecutive chunks: about 10 Setting-1 items, or 1 trajectory/hypothesis, per reply, and continue when the user says "continue".
- Before finishing, self-check every rule in Section 12 and state the result.

## 12. Final self-check (report it explicitly)

1. Exact counts, RRL distribution, manual-candidate counts and trajectory/step lengths match Section 8.
2. No question matches any banned pattern in Section 4.
3. Every R0 item retrieves a named biological entity.
4. The diversity limits in Section 6 hold, and every item has Reasoning_Category and Primary_Entity.
5. Every MCQ has 4 distinct options drawn from real entities and exactly one correct answer, whose text matches its option. Non-MCQ items have blank option fields.
6. Every number matches the files; the checks are present.
7. No invented evidence or contradictions; `NONE IDENTIFIED` is used where appropriate.
8. The unverified contrast identity is never asserted.
9. Settings 2 and 3: dependencies are genuine; every trajectory has a challenge turn; at least one revision exists; Setting 3 states chain correctly; final decisions vary; every hypothesis includes a critical test.
10. No near-duplicates within the dataset, including against the uploaded files from the other settings.

Assembling the final Excel workbooks (done separately, after all 18 JSON files exist):
- **Setting 1:** `Nova_Setting1_AllDatasets.xlsx`, sheet `Single_Turn`.
- **Setting 2:** `Nova_Setting2_AllDatasets.xlsx`, sheets `Conversation_Turns` and `Trajectory_Summary`.
- **Setting 3:** `Nova_Setting3_AllDatasets.xlsx`, sheets `Hypotheses`, `Hypothesis_Steps` and `Final_Assessments`.
- **IDs:**
  - `NOVA-S1-D1-001`;
  - `NOVA-S2-D1-T01` and `NOVA-S2-D1-T01-U01`;
  - `NOVA-S3-D1-H01` and `NOVA-S3-D1-H01-S01`.
- **Dataset_ID values:**
  - D1 = `NOVA_D1_GSE47363`
  - D2 = `NOVA_D2_GSE147507`
  - D3 = `NOVA_D3_GSE150316`
  - D4 = `NOVA_D4_GSE26487`
  - D5 = `NOVA_D5_GSE74000`
  - D6 = `NOVA_D6_GSE58434`
- **Formatting:** one item per row, a single frozen header row with filters, wrapped long-text columns, identifiers stored as text, and no merged cells.
- **Splitting:** per-dataset files (one per dataset × setting) use the same sheets and columns, filtered to that dataset.


## Appendix A — Dataset identities and caveats

**D1 — GSE47363 (folder "1. GSE47363 - mir-542-3p")**
- **Publication:** Wang Y et al., "p53 Is Positively Regulated by miR-542-3p", Cancer Res 2014;74(12):3218-27.
- **Contrast:** recorded in experiment_info: "miR 542" vs "sham", i.e., U2OS cells (wild-type TP53) transfected with a miR-542-3p mimic vs a negative-control mimic, measured on Illumina HT-12 v4. Standard phrase: "the miR-542-3p mimic vs control contrast". There are 1,166 DE genes out of 20,526 measured.
- **Files:** pathway_gene_associations.tsv and go_*_terms.tsv list member DE genes. The upstream chemical files are empty.
- **Paper reference points:**
  - p53 protein rises but the TP53 transcript does not (Supp Fig S2; TP53 logFC 0.26, not DE, while TP53 is the top regulator predicted activated from its targets).
  - RPS23 is a direct 3'UTR target (Fig 4). The RPS23 -> RPL11 -> MDM2 sequestration route is shown in Fig 3.
  - Rescue with RPS23 lacking its 3'UTR is only partial, so other mechanisms exist (Fig 4C; Discussion).
  - Growth inhibition is partly p53-independent: BIRC5/survivin, ILK and ERK/MAPK components (Discussion; Supp Figs S8-S9).
  - The miRNA layer recovers hsa-miR-542-3p as the top miRNA whose targets go down.

**D2 — GSE147507 (folder labelled "Covid NBHE")**
- **Publication:** Blanco-Melo D et al., "Imbalanced Host Response to SARS-CoV-2 Drives Development of COVID-19", Cell 2020;181:1036-1045.
- **Contrast:** experiment_info is EMPTY. The signature does NOT match the paper's NHBE culture:
  - NHBE markers IL6, CXCL1-3, CXCL5 and CCL20 are not DE.
  - CCL2, CCL8 and CCL11 are strongly up.
  - Leukocyte genes (SELL, FCER1G, S100A8/9) and monocyte/neutrophil cell-type signatures dominate.
  - Together this is most consistent with the post-mortem COVID-19 lung vs healthy lung comparison (Fig 4A), but it is UNVERIFIED. Standard phrase: "the GSE147507 SARS-CoV-2 vs control contrast analysed here".
- **Files:** the gene list is pre-filtered (812 genes with adjpv < 0.05, all with |logFC| > 1). IFNB1, IFNL1-3 and CXCL8 are absent from it. IFNA6 is the only IFN-I gene that is DE, and its logFC is capped at 10.
- **Paper reference points:**
  - Low IFN-I/III with a subset of ISGs and a strong chemokine signal.
  - Ruxolitinib blocks ISG induction but not chemokines (Fig S1G).
  - Serum IL-6 and IL1RA are elevated (Fig 4C).

**D3 — GSE150316 (folder labelled "Covid Influenza")**
- **Publication:** Desai N et al., "Temporal and spatial heterogeneity of host response to SARS-CoV-2 pulmonary infection", Nat Commun 2020;11:6319.
- **Contrast:** experiment_info is EMPTY and the group labels are not recorded. The signature is most consistent with COVID-19 autopsy lung vs non-COVID control lung, but this is UNVERIFIED and it is NOT the paper's virus-high vs virus-low comparison. Standard phrase: "the GSE150316 COVID-19 lung contrast analysed here".
- **Annotation artifact:** gene symbol "S" (Entrez 1041, logFC 10) is almost certainly SARS-CoV-2 spike reads assigned to a colliding human ID. It indicates viral RNA but is not a human gene.
- **Weak signal:** 229 DE genes; no KEGG pathway or miRNA passes FDR; only 2 regulators pass.
- **Paper reference points:**
  - High-virus cases show ISGs and JAK2/STAT1/STAT2 (Figs 2, 3, 5).
  - Epithelial recovery markers are higher in low-virus cases.
  - IDO1, PD-L1 and CTLA4 proteins are elevated in virus-positive regions (Fig 7).

**D4 — GSE26487 (folder "4. GSE26487 - Dexamethasone")**
- **Publication:** Stojadinovic O et al., "Novel Genomic Effects of Glucocorticoids in Epidermal Keratinocytes", J Biol Chem 2007;282(6):4021-34.
- **Contrast:** primary human keratinocytes, dexamethasone 0.1 uM vs untreated. experiment_info is EMPTY; the time point (the paper used 1-72 h, HG-U95Av2 arrays and a 2-fold criterion) is NOT recorded. Standard phrase: "the DEX vs control keratinocyte contrast analysed here".
- **Sparse signal:** 62 DE genes out of 8,577; no KEGG/GO MF/GO CC result is significant; the NR3C1 regulator call has a combined FDR of 0.14.
- **Paper reference points:**
  - NFKBIA is induced from 1 h.
  - Anti-inflammatory timeline: TNF -> interleukins -> IFN-gamma (48-72 h; STAT1 and IRF7 suppressed in the paper but not significant here).
  - MMP1/3/9/10 are suppressed.
  - Early differentiation is inhibited (JAG1, involucrin) while late differentiation is promoted (KLF4, TGM1, FLG).
  - Anti-apoptotic genes are induced (BCL6, NFKBIA); pro-apoptotic genes are suppressed (CASP1/4).

**D5 — GSE74000 (folder "5. GSE74000 - Acetaminophen")**
- **Publication:** Rodrigues RM et al., Data in Brief 2016;7:1052-7. It contains limited mechanistic content.
- **Contrast:** experiment_info says only "Condition" vs "Control". Which GSE74000 system was analysed (HepG2, HepaRG, hSKP-HPC or the clinical ALF samples) is NOT recorded.
- **Files:** about 6,100 genes are placeholders (logFC 0, adjpv 1), including ALB, CYP2E1 and FGA. Standard phrase: "the APAP-exposed vs control contrast analysed here".
- **Weak signal:** no KEGG, GO BP or upstream-gene result passes FDR; many miRNAs and some MSigDB/Advaita sets do. KEGG pComb_fdr = 0 values are artifacts; use pv/pv_fdr. Acetaminophen is recovered among the upstream chemicals.
- **Paper tables:** fold changes in Tables 1-2 (ALF and each in-vitro system) lose their minus signs in text extraction, so read them from the PDF page images. Table 1's hHEP and HepG2 columns are identical (a probable typesetting error).
- **No external ground truth:** do not use external APAP biology (dosing, NAPQI, toxic mechanisms) as ground truth. It may appear only as an explicitly labelled hypothesis to be evaluated against the data.

**D6 — GSE58434 (folder "6. GSE58434 - Vitamin D Calcitriol")**
- **Publication:** Himes BE et al., "Vitamin D Modulates Expression of the Airway Smooth Muscle Transcriptome in Fatal Asthma", PLoS ONE 2015;10(7):e0134057.
- **Contrast:** "Condition" vs "Control". It is most consistent with fatal-asthma-derived airway smooth muscle (ASM) treated with vitamin D vs vehicle (the paper's 711-DEG comparison):
  - CEBPB, CDC42EP3, ITPR1 and HSD11B1 are DE, but G6PD is not.
  - CCL2 goes down and CXCL12 goes up.
  - The Table 5 q-values match.
  - Still UNVERIFIED. Standard phrase: "the vitamin D vs vehicle ASM contrast analysed here (most likely fatal-asthma donors; unverified)".
- **Files:** the adjpv floor is 0.00192. IL8 is stored under the symbol "IL8". HBD is hemoglobin delta, not a defensin. CYP24A1 has a capped logFC of 10 but adjpv 0.25, so it is not significant.
- **Paper reference points:**
  - qPCR: CCL2 down and CXCL12 up with vitamin D; CCL13 and IL8 are inconsistent.
  - Vitamin D inhibits TNF-alpha-induced IL8, CCL5 and CXCL10 protein.
  - MMP9, ADAM33 and KPNA4 are not DE.
  - The smooth-muscle proliferation and contraction GO categories are not significant.

## Appendix B — Theme allocation per dataset


## D1 (miR-542-3p, U2OS)
S3 hypotheses: H1 p53 activated post-transcriptionally (protein stabilization) drives the arrest program ; H2 RPS23->RPL11->MDM2 is the sole route to p53 activation ; H3 growth inhibition is partly p53-independent (BIRC5/ILK/ERK-MAPK) ; H4 SREBP-driven cholesterol-biosynthesis repression is a p53 consequence ; H5 the down-regulated gene set is dominated by direct miR-542-3p seed targets.
S2 trajectories: T1 apoptosis vs cell-cycle-arrest fate decision (BAX, CDKN1A, GDF15, BTG2, Apoptosis pathway, p21) ; T2 cytoskeleton / focal adhesion / cell-migration program (and its paper concordance) ; T3 ribosome biogenesis / nucleolar stress beyond RPS23 (ribosomal-protein genes, rRNA processing GO) ; T4 the miR-15/16/424/497/503 seed-family signal vs miR-542-3p (co-transcribed cluster; direction-aware vs agnostic enrichment) ; T5 unexpected neurotrophin-type regulators (NGF, BDNF, NTF4 predicted activated) and MAPK signalling.

## D2 (GSE147507; SARS-CoV-2 vs control, signature consistent with post-mortem lung; unverified)
S3: H1 ISG induction via canonical type I IFN -> IRF9/STAT2 ; H2 the chemokine signature recapitulates the epithelial-culture (NHBE) program ; H3 an IL-1/IL-6 axis drives the inflammatory program ; H4 monocyte-recruiting chemokines (CCL2/CCL8/CXCL10) are IFN-driven rather than NF-kB-driven ; H5 the signal is cell-intrinsic rather than infiltrate-derived.
S2: T1 necroptosis / cell-death pathways ; T2 neutrophil and antimicrobial programs (S100A8/9, granule compartments, antimicrobial GO) ; T3 complement, coagulation and thrombo-inflammatory programs (complement receptor activity, platelet/coagulation genes) ; T4 immunoregulation and counter-regulation (IL10, IL1RN, regulator inhibition calls) ; T5 eosinophil/CCL11 axis and hypersensitivity/allergy disease terms.

## D3 (GSE150316 autopsy lung; unverified contrast)
S3: H1 ISGF3 interferon program with JAK-STAT up-regulation ; H2 immunoglobulin signature reflects B-cell receptor signalling ; H3 p53 pathway is activated ; H4 IFN-gamma-driven checkpoint program (IDO1, LAG3) ; H5 loss of alveolar type II / epithelial transcripts.
S2: T1 complement, coagulation and neutrophil-extracellular-trap pathways ; T2 down-regulated metabolic/stress genes (GLUL, HK2, SLC7A11, PLIN2, TXNRD1) — hypoxia/nutrient interpretations ; T3 CXCL10/CCL8 chemokines and macrophage/monocyte recruitment ; T4 MHC class I antigen presentation (TAP1, HLA, B2M) and IFN-gamma ; T5 chemical connectivity (tofacitinib, glucocorticoids, antimalarials) and JAK-STAT reasoning.

## D4 (dexamethasone keratinocytes)
S3: H1 GR activation (not GR induction) drives the induced program ; H2 NF-kB/IL-1 restraint via NFKBIA/TSC22D3/DUSP1/ZFP36/IL1RN ; H3 migration impairment via protease/inhibitor balance ; H4 IFN-gamma/STAT1/IRF7 suppression ; H5 dual effect on differentiation (early vs late).
S2: T1 anti-apoptotic reprogramming (BCL6, CASP4, GADD45B, SFRP1) ; T2 metabolic/redox remodelling (GLUL, TXNIP, GCLC, NAMPT, NPC1) ; T3 PTHLH and EGF-family growth signalling vs proliferation ; T4 TGF-beta/activin axis (TGFBR2 up, FST down, activin-binding GO) ; T5 transcriptional repressor network and feedback (KLF9, ZBTB16, TSC22D3, CEBPD, ZFP36, HIC2).

## D5 (APAP vs control; system unknown)
S3: H1 a p53/DNA-damage response program ; H2 an integrated-stress-response/ATF4 program (TRIB3, INHBE, ASNS, DDIT3) ; H3 suppression of innate/inflammasome genes (RSAD2, CASP1) ; H4 cytoskeletal/neuronal-like remodelling (MAP2, TUBA1A, TUBB2A) ; H5 a miRNA-mediated repression program explains down-regulated genes.
S2: T1 lipid handling and cholesterol efflux (ABCG1, LPL, HPGD, lipolysis pathway) ; T2 proliferation / chromosome / helicase programs (GO MF/CC significant terms, BUB1) ; T3 apoptosis/necrosis regulators from the paper's ALF gene classes (API5, XIAP, PIK3R1, NF1, PAWR) ; T4 growth-factor signalling (FGF2, PAPPA, IGF axis, Parathyroid hormone pathway) ; T5 chemical connectivity (acetaminophen and other hepatotoxicant signatures) and what they imply.

## D6 (vitamin D, ASM; most likely fatal-asthma donors; unverified)
S3: H1 chemokine suppression through TNF/IL-1/NF-kB restraint ; H2 IFN/STAT2/IRF9 suppression explains ISG decrease ; H3 vitamin D enhances glucocorticoid action (HSD11B1, CEBPB) ; H4 anti-hyperplasia via growth-factor repression ; H5 ligand-activated VDR signalling (CYP24A1).
S2: T1 ECM remodelling and TGF-beta pathway (MMP12, SFRP2, CILP, TGF-beta KEGG) ; T2 contractile machinery and ion channels (KCNMA1, KCNK3, ACTG2, EDNRA, PDE2A) ; T3 BMP/Wnt antagonists (NOG, SFRP2, CHRDL2, BMP4 inhibited) ; T4 immediate-early/AP-1 genes (FOS, EGR1, EGR2) and growth signalling ; T5 host-defence and neutrophil-chemotaxis genes (SLPI, SERPINB2, CXCL1/5/6, IL8; note HBD here is hemoglobin delta, NOT a defensin - treat as possible non-ASM/globin signal).

Setting 1 should span ALL themes above plus anything else well supported, with each (category, entity) pair used once.

---------------------------------------------------------------------- END PROMPT

JOB: dataset=<D1|D2|D3|D4|D5|D6>, setting=<1|2|3>   (uploaded files: <paper PDF>, <data/*.tsv>, and any already-generated JSON for the other settings of this dataset)
