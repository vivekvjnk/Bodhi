<!-- 
Author: Prophet System Team
-->



# Goal

## Some terminologies and their definitions 
- Scientific knowledge graph extraction - Knowledge graph extraction from scientific papers
- Priming summary - LLM generated summary of the source document(research paper). Later used in graph extraction pipeline for priming the LLM
- Methodological entities - Entities which belong to well established scientific methods/algorithms/facts etc.
- Domain entities - Entities which belong to the specific source document. 

## Experiment Goal
Test the causal impact of following parameters on Scientific Knowledge Graph Extraction using Bodhi:

1. **Priming summary content/strength** (what it emphasizes and how strongly).
2. **Generic type allowance** (allowance of generic entity types).
3. **Token limit of text unit(chunk)** 

We want to know:
1. Priming summary  
    - Does priming summary encourage `Domain entity` extraction, consequently discourage `Method entity` extraction? 
2. Generic type allowance
    - effect of allowing generic type for the entities which don't belong to any of the defined types, if allowance of generic type let the model stretch itself and extract more relevant entities.
3. Token limit of text unit
    - effect of varying token limit of text units, if reduced token limit results in fine grained extraction or not.

# High-level design
* Experimental unit: one source document(research paper). extracted from SciERC dataset 
* Repeats: use N = 3 distinct seeds(0,1,2), run experiment without changing any other parametes.  
After a complete cycle of ablations for other 2 variables, change token limit(k) of chunks and repeat. Range of K = [250,500,750,100]
* For source document run the KG extraction with different prompt conditions (below).
* Collect outputs (Knowledge Graph). Classify entities(Method or Domain).
* Evaluate per-document and aggregated metrics (see Metrics section).
* Use appropriate statistical tests across different ablations to detect differences.

# Evaluation

## Metrics (primary + secondary)
We evaluate each experiment run using a suite of **coverage-oriented** and **classification-oriented** metrics, with both **standard** and **adjusted (LLM-assisted)** variants.  

### 1. Coverage Metrics
- **Method Coverage (MC):**  
  Proportion of gold-standard method entities recovered.  
  \[
  MC = \frac{|TP_{\text{method}}|}{|GS_{\text{method}}|}
  \]

- **Domain Coverage (DC):**  
  Proportion of gold-standard domain entities recovered.  
  \[
  DC = \frac{|TP_{\text{domain}}|}{|GS_{\text{domain}}|}
  \]

### 2. Classification Metrics
We compute **precision, recall, and F1-score** separately for method and domain entities, and also aggregated across both:

- **Precision (P):** fraction of extracted entities that are correct.  
  \[
  P = \frac{TP}{TP + FP}
  \]

- **Recall (R):** fraction of gold entities successfully recovered.  
  \[
  R = \frac{TP}{TP + FN}
  \]

- **F1 Score:** harmonic mean of precision and recall.  
  \[
  F1 = 2 \cdot \frac{P \cdot R}{P + R}
  \]

These are reported **per category (method/domain)** and **overall**.

### 3. Adjusted Metrics (LLM-as-a-Judge)
Standard classification metrics penalize generative systems unfairly, since generative outputs may include **factually correct but novel entities** not present in the gold annotations. To account for this:

- Each “false positive” is re-assessed by a strong external LLM (judge).
- If judged factually correct, the entity is reclassified as a **True Novelty (TN)** and counted as a true positive.  
- This produces **adjusted precision, recall, and F1**:

\[
Adjusted\ Precision = \frac{TP_{Strict} + TP_{Novel}}{TP_{Strict} + TP_{Novel} + FP_{False}}
\]

\[
Adjusted\ Recall = \frac{TP_{Strict} + TP_{Novel}}{TP_{Strict} + TP_{Novel} + FN}
\]

\[
Adjusted\ F1 = 2 \cdot \frac{Adjusted\ Precision \cdot Adjusted\ Recall}{Adjusted\ Precision + Adjusted\ Recall}
\]

Where:
- \( TP_{Strict} \): exact matches with gold annotations  
- \( TP_{Novel} \): novel but factually correct entities  
- \( FP_{False} \): incorrect/hallucinated entities  
- \( FN \): missed gold entities  

### 4. Summary
- **Primary metrics:** Coverage (MC, DC), Balance (BS), Adjusted F1  
- **Secondary metrics:** Raw precision, recall, F1 per entity type (domain/method), both strict and adjusted.  
- Together, these capture both **faithfulness to gold standard** and **ability to generate correct novel knowledge**.

## Methodology
- Explain the automated evaluation pipeline 
    - Experiment orchestration
        - Bodhi initialization and KG extraction
        - Entity classification
    - Validation and result capture
        - Fuzzy adjudication
            - identified weakness: fail to separate entities with only numeric differences 
        - LLM as a judge
- Key python scripts involved in the process
    - main.py
    - entity_classification.py
    - fuzzy_adjudication.py
    - validation.py
    - helpers.py
    - analysis.py
- Output directories
    - Output artifacts
- Key documentation to refer to 

## Experiments
- Executed experiments
    - metadata: time taken, tokens used, etc
    - Artifacts: where to find them
- Results
- Analysis 