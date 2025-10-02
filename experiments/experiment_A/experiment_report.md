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
After a complete cycle of ablations for other 2 variables, change token limit(k) of chunks and repeat. Range of K = [250,500,750,1000]
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
  $
  MC = \frac{|TP_{\text{method}}|}{|GS_{\text{method}}|}
  $

- **Domain Coverage (DC):**  
  Proportion of gold-standard domain entities recovered.  
  $
  DC = \frac{|TP_{\text{domain}}|}{|GS_{\text{domain}}|}
  $

### 2. Classification Metrics
We compute **precision, recall, and F1-score** separately for method and domain entities, and also aggregated across both:

- **Precision (P):** fraction of extracted entities that are correct.  
  $
  P = \frac{TP}{TP + FP}
  $

- **Recall (R):** fraction of gold entities successfully recovered.  
  $
  R = \frac{TP}{TP + FN}
  $

- **F1 Score:** harmonic mean of precision and recall.  
  $
  F1 = 2 \cdot \frac{P \cdot R}{P + R}
  $

These are reported **per category (method/domain)** and **overall**.

### 3. Adjusted Metrics (LLM-as-a-Judge)
Standard classification metrics penalize generative systems unfairly, since generative outputs may include **factually correct but novel entities** not present in the gold annotations. To account for this:

- Each “false positive” is re-assessed by a strong external LLM (judge).
- If judged factually correct, the entity is reclassified as a **True Novelty (TN)** and counted as a true positive.  
- This produces **adjusted precision, recall, and F1**:

$
Adjusted\ Precision = \frac{TP_{Strict} + TP_{Novel}}{TP_{Strict} + TP_{Novel} + FP_{False}}
$

$
Adjusted\ Recall = \frac{TP_{Strict} + TP_{Novel}}{TP_{Strict} + TP_{Novel} + FN}
$

$
Adjusted\ F1 = 2 \cdot \frac{Adjusted\ Precision \cdot Adjusted\ Recall}{Adjusted\ Precision + Adjusted\ Recall}
$

Where:
- $ TP_{Strict} $: exact matches with gold annotations  
- $ TP_{Novel} $: novel but factually correct entities  
- $ FP_{False} $: incorrect/hallucinated entities  
- $ FN $: missed gold entities  

### 4. Summary
- **Primary metrics:** Coverage (MC, DC), Balance (BS), Adjusted F1  
- **Secondary metrics:** Raw precision, recall, F1 per entity type (domain/method), both strict and adjusted.  
- Together, these capture both **faithfulness to gold standard** and **ability to generate correct novel knowledge**.





## Methodology
This section describes the **automated evaluation pipeline** used in our experiments. The pipeline integrates Hydra-based orchestration, Bodhi graph extraction, classification, fuzzy adjudication, and metric calculation.  

### 1. Automated Evaluation Pipeline Overview
The pipeline is designed to automatically run multiple experiments across different parameter configurations. It consists of four main stages:

1. **Experiment orchestration (main.py: `exec_experiment`)**  
   - Configure and launch experiments using Hydra.  
   - Initialize Bodhi and perform knowledge graph extraction.  
   - Run the evaluation routine (`exec_evaluate`).  

2. **Entity classification**  
   - Both SciERC gold data and Bodhi outputs are classified into `Method` or `Domain` entities.  
   - Classification outputs are stored for later validation.  

3. **Validation and result capture (validation.py: `evaluate`)**  
   - Perform fuzzy adjudication between SciERC entities and Bodhi entities.  
   - Weakness identified: fails to separate entities differing only numerically.  
   - Pass unresolved cases and false positives to an LLM “judge” for novelty assessment.  

4. **Metrics computation and storage**  
   - Coverage, precision, recall, F1, and adjusted metrics are calculated.  
   - Results and metrics are saved as structured YAML files for downstream analysis.  

---

### 2. Experiment Orchestration (`main.py`)
Hydra is used as the top-level experiment manager. The Hydra entry point is `main.py:exec_experiment()`.  
Key details:  

- **Parallelization**:  
  - Uses joblib-based parallelization.  
  - Parallelism improves runtime until limited by LLM API rate limits.  
  - With VertexAI: best performance at **2 parallel jobs**, each with up to **18 Bodhi threads**.  

- **Sweep Parameters**:  
  - `token_limit` ∈ {250, 500, 750, 1000}: maximum tokens per text chunk.  
  - `priming` ∈ {True, False}: whether to use a priming summary.  
  - `generic_type_allowance` ∈ {True, False}: whether to allow a generic fallback entity type.  
  - `seed` ∈ {0, 1, 2}: seed passed to the LLM for reproducibility (though exact reproducibility is not yet guaranteed).  

- **Total experiments**:  
  - Per document: $2 \times 2 \times 4 \times 3 = 48$ runs.  
  - Dataset: 8 SciERC documents (randomly sampled from 106).  
  - Executed ~360 runs within available resources(which is Google cloud $300 free credit :).  

**Execution flow of `exec_experiment`:**
1. Load configuration from Hydra (OmegaConf).  
2. Select prompt templates:  
   - 4 variants depending on `priming` and `generic_type_allowance`.  
   - Prompts are stored in dedicated files.  
3. Select entity type schema:  
   - Two variants (with generic type / without).  
   - Entity type dictionaries include **Task, Method, Dataset**, and optionally **generic**.  
4. Update Hydra config with prompt path.  
   - Bodhi requires `prompt_path`. If not provided, Bodhi defaults to priming+generic prompt.  
5. Wrap entity types into an **ontology dictionary**.  
   - Chosen for extensibility (future support for relationship/edge types).  
6. Initialize Bodhi with Hydra config.  
7. Ensure source documents are present in input directory.  
8. Run Bodhi → Extract KG.  
9. Call `exec_evaluate` to run validation.  

---

### 3. Evaluation Function (`validation.py`)
The evaluation function handles classification, adjudication, and metric computation.  

**Execution flow of `evaluate`:**
1. Configure input/output paths for all artifacts:  
   - SciERC dataset  
   - Bodhi output graph  
   - Classification outputs (SciERC + Bodhi)  
   - Validation results and metrics  

2. Load SciERC dataset:  
   - Extract evaluation strings for the current document.  
   - Run SciERC classification(Method or Domain entities) pipeline.  
   - Output classified entities to YAML.  

3. Load Bodhi output:  
   - Parse entities from the extracted knowledge graph.  
   - Run classification pipeline aligned with SciERC schema.  

4. Run fuzzy adjudication:  
   - Identify entity matches using similarity-based adjudication.  
   - Known weakness: fails to separate entities that differ only numerically.  

5. Use **LLM-as-a-Judge**:  
   - False positives are reassessed by an external LLM.  
   - LLM judges classify them as either **relevant novel entities** or **false positives**.  
   - Relevant novel entities are included in adjusted metrics.  

6. Compute evaluation metrics:  
   - Standard precision, recall, F1 (per type and overall).  
   - Coverage metrics (Method Coverage, Domain Coverage).  
   - Adjusted metrics (incorporating LLM judgments).  

7. Save results:  
   - Adjudication pipeline results → `eval_output.yml`.  
   - Final metrics → `eval_metrics.yml`.  

---

### 4. Implementation Artifacts
Key scripts involved in the pipeline:  
- **main.py**: Hydra orchestration and experiment execution.  
- **entity_classification.py**: Classify entities into Method vs Domain.  
- **fuzzy_adjudication.py**: Perform fuzzy entity matching.  
- **validation.py**: End-to-end evaluation pipeline.  
- **helpers.py**: Utility functions.  
- **analysis.py**: Aggregate metrics, bootstrapping, and plotting.  

---

### 5. Output Directories
Each experiment produces:  
- Bodhi KG output (`*_graph.yml`).  
- Classification outputs (Bodhi + SciERC).  
- Validation results (`eval_output.yml`).  
- Metrics (`eval_metrics.yml`).  
- Organized under Hydra-managed output directories, with unique paths per experiment configuration.  

---

### 6. Documentation References
- Hydra configuration files under `configs/` define all sweep parameters.  
- Prompt templates stored under `experiments/experiment_A/prompts/`.  
- SciERC dataset (LLM-superset) located at `experiments/Datasets/SciER/LLM/superset.jsonl`.  


# Experiments
## Structure of this section
- Executed experiments
    - metadata: time taken, tokens used, etc
    - Artifacts: where to find them
- Results
- Analysis 