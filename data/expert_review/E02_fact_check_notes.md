# Expert Review E02: Fact-Check Sheet

Working notes for the blinded evaluation of AI-generated transcriptomic interpretations (10 cases).

## Part 1. Fact-check by case

### Case 1: GSE147507, IL6/IRF9/ICAM1/TNF

**Applies to all four responses**

- Every value matches the reference: TNF +5.07/8e-5, IRF9 +2.86/0.014, IL6 −0.603/0.737, ICAM1 +0.459/0.779.
- IL6 |logFC| 0.603 technically passes the magnitude cutoff. It fails only on adjusted p. B notes this correctly; the others imply it fails both.
- None of the four raises the reference’s main point: the contrast is most consistent with post-mortem lung, not NHBE. Each attributes the IL6/ICAM1 mismatch to pipeline, donor, time point or dose instead.

**Response A**

- The IL6 upstream-regulator figures (15/24, p 0.949) are unverifiable but agree with C.
- It attributes the discrepancy to “the specific NHBE sample subset,” which implicitly treats the contrast as NHBE.

**Response B**

- The header calls it a “SARS-CoV-2 vs healthy NHBE contrast,” which mislabels it.

**Response C**

- It calls it a “SARS-CoV-2 vs mock NHBE contrast,” which mislabels it.
- The RUVSeq batch-correction claim is unverifiable.
- The claim that the regulator analysis “predicts all four as activated” is unverifiable.

**Response D**

- It calls TNF’s regulator p (0.70) an “over-representation p.” C calls the same number a regulator p-value, so the terminology is inconsistent.
- The phrase “the 4 of 4 concordance question” is garbled.
- D avoids saying NHBE in its limitations, but it doesn’t name the lung contrast either.

> Possible comment: The question’s premise is the NHBE culture comparison, but the analysed contrast is most consistent with post-mortem lung. The item therefore tests recognition of a design mismatch more than gene concordance. The reference handles this, but none of the responses surface it.

### Case 2: GSE58434, cytokine/chemokine KEGG + GO MF

**Applies to all four responses**

- The core values match the reference: 26/134 and 1.92e-8; cytokine activity 29/103 and 1.93e-11; chemokine activity 10/20 and 3.24e-6.
- None mentions the perturbation support (pAcc 0.0005).
- None mentions that the authors drew their follow-up genes from the chemokine-activity category. Both points are in the reference.

**Response A**

- It contradicts itself on chemokine receptor binding. It first gives 11/29 DE, then says the term is “represented by only one DE gene (CXCL12).”
- It labels the pathway p-values as ORA p-values. The reference separates pORA (4.5e-9) from the FDR (1.9e-8).
- It says no perturbation score was available, but pAcc exists.
- It reframes the authors’ claim as “responders vs non-responders,” which is not how the paper’s comparison is described in the case.

**Response B**

- The added parent terms (receptor ligand activity 55/239, 1.65e-17; signaling receptor activator activity 55/245, 2.91e-17) are unverifiable but agree with C and D.

**Response C**

- The claim that hsa04061 (11/40, 6.38e-6) together with the other two pathways makes up “the top three KEGG ranks” is unverifiable.
- It cites placeholder references marked “[PMID: unverified].”

**Response D**

- Same as C on hsa04061 and the top-three claim.
- “Five of the top 25 MF terms” is unverifiable.
- The Drăghici 2007 and Tarca 2009 impact-analysis citations are real and correctly attributed.

> Possible comment: The question says the categories “distinguished the vitamin D responses.” In the paper this refers to a comparison between donor groups, which this single contrast can’t test. The wording invites the responders/non-responders reading seen in one response.

### Case 3: GSE74000, TGF-β in the APAP contrast

**Applies to all four responses**

- The core values match across responses: TGFB1 0.035/0.851; KEGG hsa04350 2/105, p 0.282; regulator call p 0.722.
- None notes that the analysed contrast is unrecorded. It could be HepG2, HepaRG, hSKP-HPC, or ALF.
- B, C and D assert that the publication’s “Necrosis of Liver” table is a disease-annotation result rather than expression. That conflicts with the question’s statement that TGFB1 is “up-regulated” in ALF, and it isn’t supported by anything in the case.

**Response A**

- It calls SMAD2 (−0.55, 0.032) “significant.” That’s true by p-value, but SMAD2 is not DE because |logFC| < 0.6.
- It says the publication’s claim is “not reproducible from this dataset.” That overstates things, since this may not be the ALF contrast at all.
- “Not among the top 20 pathways” is unverifiable.

**Response B**

- It handles SMAD2 correctly (not DE).
- GDF15 (−1.04, 0.036) is unverifiable.
- PMID 31132129 (GW788388 in mouse APAP injury) is a real study, but external.
- It omits CDKN1A.
- “62 of 316 pathways significant” is unverifiable.

**Response C**

- It contradicts itself on the regulator call. It says TGFB1 is predicted “inhibited,” but describes 3 of 5 targets as “activation-consistent.” The other three responses say inhibition-consistent.
- “212 of 704 disease terms” is unverifiable.
- PMID 30940161 is real but external.

**Response D**

- It contradicts itself on what is significant. The intro says SMAD2 is “the only significant signal,” but section 2 lists INHBE and BMP2 as DE.
- It calls SMAD2 “significantly downregulated,” but SMAD2 is not DE.
- It labels the result “contradicted,” but every value is non-significant, so the data are null rather than contradictory.
- The verdict sentence is garbled: “insufficient evidence to supported.”

> Possible comment: The analysed contrast is unrecorded and may be an in vitro hepatocyte model. “Divergence from the publication” assumes this contrast should reproduce a clinical ALF finding. If it’s a cell line, the absence of TGFB1 induction may be expected rather than divergent.

### Case 4: GSE47363, miR-424/503/542 cluster co-regulation (turn 7)

**Applies to all four responses**

- The miR-424-5p statistics conflict between responses. A reports rank 21, p 0.01352. B reports rank 24, p 1.03e-3. These may be FDR versus raw p, but you can’t tell from the form.

**Response A**

- miR-542-3p FDR 2.52e-5 with 48/343 is consistent with C and D in Case 8.
- It explicitly restates the turn-3 point (no cluster-member activity).

**Response B**

- It reports miR-542-3p p = 7.10e-8, a different statistic from A’s FDR.
- Its added inference, that endogenous miR-424/503 levels may be low, is clearly labelled as an inference.
- The TaqMan/RT-qPCR Methods detail is unverifiable.

**Response C**

- SRC (0.521, 0.0002, not DE) agrees with D.
- It says the miR-424-5p signal is “shared-seed enrichment.” That is questionable: miR-424-5p belongs to the miR-15/16 seed family and does not share a seed with miR-542-3p.
- It does not explicitly re-state the turn-3 finding.

**Response D**

- Factual error: it calls MEG3, MEG8, DLK1 and DIO3 “neighbouring imprinted locus genes.” DLK1–DIO3 is on 14q32. The miR-424/503/542 cluster is on Xq26.3. Those genes are not neighbours of this cluster.
- It treats probes for the host genes MIR542, MIR424 and MIR503 on the HT-12 array as pri-miRNA readouts. That is questionable, and the reading is unverifiable anyway.
- The direct quotations from the paper are unverifiable.
- It restates the earlier conclusion explicitly.

> Possible comment: None needed.

### Case 5: GSE147507, GPSM1/2/3 + PCP2 (turn 5)

**Applies to all four responses**

- 18/18 consistent targets, 62 total, p 5.27e-8 is consistent everywhere. The z of −4.24 is correct (18/√18).
- GPSM2 and PCP2 show logFC 0 with adj p 0. An adj p of exactly 0 is a placeholder, so these genes are unmeasured. The reference says “unmeasured,” but A, B and C say “not expressed.”
- None ties the answer back to turns 3–4 or explicitly removes these calls from the braking evidence base, which is the expected revision.

**Response A**

- It refers to “NHBE cells” and “bronchial epithelium,” which mislabels the contrast as NHBE.
- It singles out GPSM3’s call as “worth examining further.” That conflicts with its own point that the four calls are one shared signal.
- It uses “Partially supported → qualify,” which is hypothesis-state language in a conversation case.
- The three PMIDs look plausible but are external.

**Response B**

- It mislabels the contrast as NHBE.
- It calls PCP2 a “regulator of G-protein signalling family” member. PCP2, like GPSM1–3, is a GoLoco-motif protein, not a member of the RGS family.
- It says there is “no literature support” for immune roles. GPSM3 does have a published leukocyte/inflammation role (A cites one).

**Response C**

- PMID 38674408 is a paper about GPSM2 in colorectal cancer, but C cites it for a GPSM3–glioblastoma link. The citation doesn’t match the claim.
- It ends by keeping a re-framed “module predicted inhibited” call, rather than excluding it as the expected revision says.

**Response D**

- It has the same PMID mismatch as C.
- It uses an “[PMID: unverified]” marker.
- It says “none are established immunoregulators,” which overstates the case given GPSM3’s known role.
- It uses “weakened on all three components,” again hypothesis language.

> Possible comment: The reference’s suggestion that the shared targets are “most likely chemokine/GPCR signalling genes” isn’t shown in the evidence and reads as speculative.

### Case 6: GSE150316, p53 effectors

**Applies to all four responses**

- The values match the evidence in all four.
- All four give CONTRADICTED. The reference state is Weakened.
- None raises cell-composition change in bulk autopsy lung as an alternative explanation for the downward p53-target trends.

**Response A**

- It says “5 of 5 significant DE p53 genes down.” The earlier step listed 6, counting PTEN.
- Its opening says GDF15 is “strongly repressed,” but adj p is 0.076.

**Response B**

- It contradicts itself on the flat genes. It first says “1 is essentially unchanged,” then names two near-zero genes (FAS and SESN1).
- It treats the TP53 regulator “inhibition prediction” as an independent line of evidence. D reports that call as FDR 0.246, which is non-significant.
- It calls ZMAT3 and CCNG1 “originally named targets,” but the hypothesis didn’t name them.

**Response C**

- It omits PTEN.
- Otherwise, no factual issues.

**Response D**

- It says the non-significant TP53 regulator call (FDR 0.246) is “further corroborated.”

> Possible comment: The “Contradicts” relation rests entirely on non-significant trends. In Case 7, the reference treats non-significant trends in the opposite direction as “Qualifies” and notes that absence of significance is not evidence of absence. It would help to apply the same rule to both. Bulk-tissue composition change is also a plausible non-p53 explanation for the downward trends.

### Case 7: GSE26487, TIMPs in dexamethasone-treated keratinocytes

**Applies to all four responses**

- The TIMP values match the evidence.
- TIMP4 at exactly 0.00 / 1.0 looks like a placeholder (unmeasured) rather than “unchanged,” but all four read it as a real flat result.
- None mentions that the time point is unrecorded, or that the paper’s TIMP2 induction was at late time points under a 2-fold criterion. Both are central to the reference.

**Response A**

- The serpin, SPINK and cystatin values are unverifiable.
- It counts SERPINH1 (HSP47, a non-inhibitory collagen chaperone) among the “inhibitors” moving the wrong way.
- PMID 1707919 is plausible but from a different cell type, a limitation A itself states.

**Response B and C**

- Both refer to “prior/earlier serpin results” that aren’t in this case’s evidence. They are presumably from their own earlier steps, which the form allows.

**Response C**

- It explicitly notes that non-significance doesn’t contradict the hypothesis.

**Response D**

- “Reproduce the ledger values exactly” is process language.

> Possible comment: TIMP4’s logFC 0.00 with adj p 1.0 may be a placeholder for an unmeasured gene rather than a true null.

### Case 8: GSE47363, BIRC5/ILK

**Applies to all four responses**

- BIRC5 −2.95 and ILK −1.80, both with adj p 1e-6, match everywhere.
- None notes that BIRC5 is a p53-repressed gene and a G2/M cell-cycle gene. In wt-TP53 U2OS with p53 activated, its downregulation is expected regardless, so it doesn’t discriminate p53-independent action. C comes closest, saying independence rests on the shRNA experiment.

**Response A**

- No factual issues.

**Response B**

- It attributes BIRC5/ILK targeting to prior refs 49 and 25. C and D quote the Discussion as saying these were “revealed by our gene expression analysis,” so the attribution conflicts.

**Response C**

- It contradicts itself on the ERK/MAPK genes. It says “all four are down-regulated and significant,” then says MAPK3 (−0.60) is “trend-only” and only three clear both thresholds.
- It calls the control “sham.” It was a negative-control mimic.
- The TP53 regulator figures (48/55, 1.4e-13) are unverifiable.

**Response D**

- Its status reads “SUPPORT,” which is likely “Supported.” The reference state is Partially supported.

> Possible comment: Because BIRC5 is transcriptionally repressed by p53 and is cell-cycle-linked, its downregulation in wt-p53 cells is consistent with both p53-dependent and p53-independent routes. That may limit how strongly this step can “support” the p53-independent arm.

### Case 9: GSE58434, HSD11B1/HSD11B2

**Applies to all four responses**

- The values match the evidence. “~2.1-fold” is correct (2^1.09).
- None mentions that the effect is conditional on cortisone substrate being present in culture, which the reference states.
- None mentions that HSD11B1’s reductase direction depends on H6PD/NADPH supply.

**Response A**

- Its opening sentence (“do not both change in a way that favours…”) reads like a “no,” but the conclusion is consistent with the hypothesis.

**Response B**

- It previews later-step genes (CEBPB, NR3C1, FKBP5, TSC22D3, DUSP1), which are unverifiable here. They are clearly flagged as out of scope.

**Response C**

- PMID 19251840 is real, but that study used Th2-cytokine induction, not vitamin D. “Literature confirms” overstates how well it transfers to this experiment.
- It notes that the contrast identity is unverified.

**Response D**

- It notes that the contrast identity is unverified.
- There are stray ** formatting artifacts and a truncated status line.

> Possible comment: The “Supports” relation depends on cortisone availability (serum in the medium) and on H6PD-dependent reductase activity. Neither is measured, so the link from transcript to more active glucocorticoid is two steps removed.

### Case 10: GSE147507, chemokine molecular functions

**Applies to all four responses**

- The MF values match the evidence, and “4/10 wrong direction” is correct (IL6, CXCL2, CXCL3, CXCL5).

**Response A**

- Status Weakened, consistent with its reasoning.

**Response B**

- Its status, PARTIALLY_SUPPORTED, upgrades from Weakened while its own text says the evidence is agnostic to the hypothesis. The status and reasoning are inconsistent.
- It labels the gene ratio for CCR chemokine receptor binding as 34%. The correct figure is 42% (10/24). 34% is the ratio for chemokine receptor binding (13/38).

**Response C**

- Its status, CONTRADICT, downgrades from Weakened on evidence it describes as confirming the program exists. That is internally inconsistent.
- It lists 9 genes as “the genes driving” an 11-gene term.
- The elim p-values and the GO-BP and hallmark evidence it cites are unverifiable.

**Response D**

- It lists GPCR binding among “four chemokine-specific terms,” which is a minor mislabel.
- Status Weakened, consistent with its reasoning.

> Possible comment: MF enrichment and the KEGG cytokine/chemokine pathways are driven by largely the same chemokine genes. “Independently confirm” in the question somewhat overstates how separate this evidence is from Step 1.

---

Note: Each case above ends with a shaded “Possible comment.” These are factual observations about the question or reference, phrased so they can be pasted into the optional comment field. Edit or drop any you don’t share; they deliberately avoid stating agreement or disagreement with the reference conclusion.
