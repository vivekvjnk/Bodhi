<!-- 
Author: Prophet System Team
-->
# Goal

Test the causal impact of:

1. **Priming summary content/strength** (what it emphasizes and how strongly).
2. **Generic type allowance** (allowance of generic entity types).
3. **Token limit of text unit(chunk)** 
We want to know: 
- which instruction(s) cause loss of methodological entities, and whether relaxing/tuning them restores method-level coverage without collapsing domain coherence.
- effect of allowing generic type for the entities which don't belong to any of the defined types, if allowance of generic type let the model stretch itself and extract more relevant entities.
- effect of varying token limit of text units, if reduced token limit results in fine grained extraction or not.

# High-level design

* Experimental unit: one K-token chunk (same chunks used across experiments).
* Repeats: use N = 4 distinct chunks sampled from the source corpus (stratify so chunks include domain anchors and method-level phrases). After a complete cycle of ablations for other 2 variables, change token limit(k) of chunks and repeat. Range of K = [250,500,750,100]
* For each chunk run the NER LLM with different prompt conditions (below).
* Collect outputs (entities + types). Map canonical forms and dedupe.
* Evaluate per-chunk and aggregated metrics (see Metrics section).
* Use paired comparisons and appropriate statistical tests (paired t-test or Wilcoxon) across chunks to detect differences.

# Metrics (primary + secondary)

Primary coverage metrics (per chunk and averaged):

1. **Method Coverage (MC)** — proportion of expected method-related gold entities recovered (e.g., VAE, KL divergence, loss terms, teacher forcing, encoder/decoder, GRU, RDKit, GAN, etc.). Use a gold list of method entities derived from full-document annotation.
2. **Domain Coverage (DC)** — proportion of expected domain entities recovered (proteins, diseases, datasets, molecules).
3. **Balance Score (BS)** — MC / (MC + DC) (range 0..1). Value near 0.5 indicates balanced coverage; skew indicates bias.
4. **Precision / Recall / F1** — computed against gold annotations (separately for METHOD and DOMAIN).
5. **Novelty & Redundancy** — fraction of outputs that are near-duplicates or synonyms (detect canonical merges).

Secondary metrics:

* **False Positive Rate (FPR)** — proportion of extracted entities not present/relevant to chunk or gold list.
* **Granularity Index (GI)** — average specificity level (e.g., encoder/decoder > model name > generic method) — numeric score you can define.

# Baseline

* **BasePrompt** = current Algorithm 2 prompt (with priming summary + coherence instructions + ENTITY TYPES rigidity).
* **GoldSet** = human-annotated entities for all N chunks, labeled by type (METHOD, DOMAIN, GENERIC, etc.). Use a small expert-labeled subset (e.g., 100 chunks) to bootstrap evaluation; can expand later.

# Perturbation experiments (each is an A/B or multi-arm test)

## Experiment A — Priming summary + Generic type ablations
* **Purpose:** test how much priming summary content drives domain bias. test impact of generic type allowance

Total of 4 ablation experiments are planned
|                | With Priming Summary | Without Priming Summary |
|----------------|-------------------------|-------------------------|
| **Without Generic Type**   |  experiment A_1                       |       experiment A_2                  |
| **With Generic Type**  |   experiment A_3                      |       experiment A_4                  |

### A_1 : With priming summary, Without generic type
* **Setup:** run prompt **with priming** summary. generic type not allowed
* **Expected signal:** Low Method Coverage, High Domain Coverage; 

### A_2 : Without priming summary, Without generic type
* **Setup:** run prompt **without priming** summary. **generic** type **not allowed**
* **Expected signal:** High Method Coverage, low Domain Coverage; 

### A_3 : With priming summary, With generic type
* **Setup:** run prompt with priming summary. allowed types **include a generic** type (instruction to use it when extracted entities doesn't belong to any other allowed types)
* **Expected signal:** Low Method Coverage, High Domain Coverage; Higher number of extracted entities

### A_4 : Without priming summary, With generic type
* **Setup:** run prompt **without priming** summary. allowed types **include a generic** type (instruction to use it when extracted entities doesn't belong to any other allowed types)
* **Expected signal:** Low Method Coverage, High Domain Coverage; Higher number of extracted entities


### Experiment B — Token limit ablations

* **Purpose:** see whether changing text unit token limit affect overall behaviour of the system
* **Setup:** Repeat Experiment A with 4 different token limits for text units: [250,500,750,1000]
* **Expected signal:** As token limit reduces, both Method Coverage and Domain Coverage increase
- Total of 16 experiments would be carried out

### Experiment C — Entity Count Constraint Removal

* **Purpose:** confirm that per-chunk 10–15 requirement is not a bottleneck.
* **Setup:** allow “up to 30 entities” or unconstrained; keep BasePrompt.
* **Expected signal:** if method coverage increases it was a bottleneck; if not, priming/coherence cause remains.

### Experiment D — Adversarial Priming (noise)

* **Purpose:** test robustness—if priming contains misleading emphasis, how model behaves.
* **Setup:** inject irrelevant but strongly worded priming lines (e.g., emphasize chemistry vocabulary unrelated to chunk). Observe hallucinations or drift.
* **Expected signal:** shows sensitivity and potential for prompt-induced hallucination.

# Operational details

* **Runs per condition:** run each experiment on the same N chunks; repeat each chunk run M = 3 times to measure LLM nondeterminism (or set deterministic seed).
* **Randomization:** randomize chunk order; balance chunk selection to include method-rich and domain-rich slices.
* **Control for temperature:** fix LLM temperature to same value across conditions or run at two temps (0.0 for deterministic behavior, 0.7 for higher variability).
* **Canonicalization:** normalize entity mentions (case, punctuation, synonyms). Use a mapping table (e.g., GxVAEs / Gx-VAEs → GxVAEs).
* **Evaluation pipeline:** automated string matching with fuzzy threshold + llm adjudication for borderline matches.

# Statistical analysis

* For each metric compare BasePrompt vs perturbation using paired tests across chunks:

  * If metrics approximately normal: paired t-test.
  * If non-normal or small N: Wilcoxon signed-rank.
  * Compute effect sizes (Cohen’s d).
  * Correct for multiple comparisons (Benjamini-Hochberg) since many tests will be run.
* Decision thresholds:

  * A change in MC or DC with p < 0.01 and Cohen’s d > 0.5 considered meaningful.
* Visuals: boxplots per condition for MC, DC, BS; heatmap for per-entity extraction frequency across conditions.

# Expected interpretations / decision rules

* **Priming causal if:** Experiment A show significant directional changes in MC/DC compared to BasePrompt(A_3).
* **Entity types constraint causal if:** Experiment A_3,A_4 shows marked increase in method entities when relaxed.
* **Chunk size/context matters if:** Experiment B increases method coverage substantially.

# Reporting & outputs

For each experiment produce:

* Per-condition summary table (MC, DC, BS, F1\_method, F1\_domain, CUC).
* Top 20 most frequently extracted entities per class (METHOD / DOMAIN).
* Example chunks where behavior changed significantly (qualitative analysis).
* Statistical test results and effect sizes.
---

# Ablations (Iteration 1)
Following are the ablation variables of consideration 
1. priming summary
2. generic type allowance 

Total of 4 ablation experiments are planned

|                | With Priming Summary | Without Priming Summary |
|----------------|-------------------------|-------------------------|
| **Without Generic Type**   |  experiment A_1                       |       experiment A_2                  |
| **With Generic Type**  |   experiment A_3                      |       experiment A_4                  |

## Preparations 
- [Created 4 prompt files](prompt_engineering/experiment_A/prompts/A_1_with_priming_summary_without_generic_type.py)
- Created 2 variants of Bodhi graph_extraction.py : With and without priming summary
  - `Generic Type` related instructions are contained in LLM prompts. There are no dependence on main code. Hence we don't have to prepare variants of any Bodhi code.
  - `Priming Summary` related configuration and instructions are spread across prompts and graph_extraction.py. Hence we've variants of graph_extraction.py

- Generated outputs are stored in dedicated folders with corresponding experiment name
  - All artifacts, including logs, after running Bodhi pipeline are captured

### Bodhi configuration 
#### LLM Setup 
- fast_model: "gemini-2.0-flash-lite-001"
- general_model: "gemini-2.5-flash"
- thinking_model: "gemini-2.5-pro"
- inference_engine: "vertexai"
- token_limit: 1000 # This parameter decides the granurality of Knowledge Graphs
- temparature: 0.7 # For all vertexai models, this parameter is defaulted to 0.7

#### Deduplication pipeline
- similarity_threshold=0.9
- description_threshold=0.6

## Experiment results 
A_2 : {'total_gold': 53, 'direct': 18, 'fuzzy_candidates': 14, 'missed': 21, 'coverage_pct': 60.37735849056604}
A_4 : {'total_gold': 53, 'direct': 17, 'fuzzy_candidates': 14, 'missed': 22, 'coverage_pct': 58.490566037735846}
A_3 : {'total_gold': 53, 'direct': 12, 'fuzzy_candidates': 15, 'missed': 26, 'coverage_pct': 50.943396226415096}
A_1 : {'total_gold': 53, 'direct': 13, 'fuzzy_candidates': 9, 'missed': 31, 'coverage_pct': 41.509433962264154}

## Observations 

A_2 Has the lowest missed entity count:
  - Priming summary is not present
  - Generic type is not allowed
A_4 Comes 2nd:
  - Priming summary is not present 
  - Generic type allowed
A_3, A_1 are the worst cases:
  - In both cases, priming summary is present
  - A_1 performs worst. In A_1 generic type is not allowed

## Inferences 
- This evidence aligns well with our primary assumption: Priming summary reduces number of general entities extracted from the source. 
  - Need to do few more experiments with different text units, different context length to verify the assumption
  - If same trend is repeated across all experiments, we've evidence for influence of priming summary
- Evaluation mechanism need to be modified. We need to integrate domain coverage, method coverage f1 scores etc. LLM based automated pipeline is required for rigorous evaluation. 

# Evaluation design 
## Method Coverage 
Primary coverage metrics (per chunk and averaged):

1. **Method Coverage (MC)** — proportion of expected method-related gold entities recovered (e.g., VAE, KL divergence, loss terms, teacher forcing, encoder/decoder, GRU, RDKit, GAN, etc.). Use a gold list of method entities derived from full-document annotation.
2. **Domain Coverage (DC)** — proportion of expected domain entities recovered (proteins, diseases, datasets, molecules).
3. **Balance Score (BS)** — MC / (MC + DC) (range 0..1). Value near 0.5 indicates balanced coverage; skew indicates bias.
4. **Precision / Recall / F1** — computed against gold annotations (separately for METHOD and DOMAIN).
5. **Novelty & Redundancy** — fraction of outputs that are near-duplicates or synonyms (detect canonical merges).

## Validation
### Step 1: Entity classification
- Metrics 3,4,5 depends on Metrics 1,2 for calculation
- Hence we need to extract `Method entities` and `Domain entities` from both:
  - gold standard 
  - bodhi graph extraction
- We've 106 manually annotated full text scientific publications from SciER
  - Manually classifying gold standard entities into Method and Domain is error prone and time consuming for a 1 person team (with limited domain knowledge).
  - Hence we delegate this process to an LLM
- Classify entities in each gold standard dataset(corresponding to one scientific publication) into `Method entities` and `Domain entities`
  - Feed LLM `full text`(scientific publication), first N entities, and instructions for classification
  - N : defined by the LLM context limit. 
    - Assume usable context limit of 10k
    - First we calculate token length of `Full text`. Assume it is around 5k
    - Token length for classification instructions is fixed. Let it be 1k
    - We will split all available entities into multiple groups, where for each group, total number of tokens = 4k
    - Usable context limit would be a variable parameter in the evaluation script. According to it's value, system would split the entities into multiple groups
  - Instructions for classification
    - Clear definition of `Method` and `Domain` entities are provided 
    - Few shot examples are provided
    - Together with format instructions, token length should not exceed 1k
- Above approach will be repeated for Bodhi extracted entities also.
- Then we've apples to apples for comparison

### Fuzzy matching with LLM adjudication
- Stage 1: One to one entity matching 
  - Normalize entities from gold standard and bodhi extractions
  - Compare normalized strings 
  - Collect all normalized entities from bodhi which didn't match. Pass them to Stage 2 

- Stage 2: Fuzzy pattern matching
  - Use difflib sequencematcher to calculate similarity between all possible combinations
  - Make sure numeric differences between entities are handled properly
  - Identify entities with similarity > threshold as matches
  - Collect all mismatched entities from bodhi. Pass them to Stage 3

- Stage 3: Pass mismatched entities to LLM to idenify any possible matches
  - Apply prompt building strategy based on the usable context limit(UCL)
  - Collect all mismatched bodhi entities, add them to the prompt, count number of tokens. Make sure content doesn't take more than UCL/2. The other UCL/2 will be used for gold standard entities and format instructions 
  - Calculate token count for format instructions(token_fi)
  - Split gold standard entities such that token length of each individual set(token_gs) < (UCL/2 - token_fi)
  - Total number of LLM calls = ceil_div(token_ge, token_gs) : where token_ge = total number of tokens for entire gold standard dataset, token_gs = number of tokens per gold standard set
  - Instruct LLM to identify matching entities from gold standard set and bodhi set

- After execution of stage 3, all mismatched entities from bodhi extractions would be considered as novel extractions
  - These novel entities would go through another LLM cycle with source text for analyzing their importance with respect to the source text unit. 
- Entities from gold standard set which doesn't have any matches in Bodhi extraction would be considered as missed entities by Bodhi pipeline.

- Calculate overall coverage

**NOTES**: All LLM operations done on gold standard should be cached. Since we reuse gold standard data across different runs of the experiment, we can replay LLM gold standard operations so that, compute time and cost will be optimized.

##### Method Coverage and Domain Coverage
- Split all matched entities from Bodhi extraction into Domain entities and Method entities
- Calculate method coverage and domain coverage independently based on gold standard Method entities and Domain entities
- Determine metrics 3,4,5 using coverage information 

##### Entity type adherence validation
- For each matched entity type from Bodhi extraction, check the if the entity type is matching with the gold standard. 
  - Bodhi allows multiple types for single entity. Hence we should check if the gold standard type annotation is present atleast once in the type list of each matched entities in Bodhi extraction.


# Experiment orchestration 
- 16 experiments per resource
  - Each experiment is repeated 3 times for LLM probabilistic variance analysis
  - Hence, 48 runs of Bodhi per resource
- 106 resources in SciERC dataset
  - 106 * 48 = 5088 experiments in total 

- All 48 experiments for each resource should be captured and kept in one place
  - What are the artifacts for each experiment?
    - Bodhi graph, intermediate data, extraction logs, Evaluation results 
- Hence, top level hierarchy becomes the unique resource. Lower level hierarchies are built upon individual experiments 