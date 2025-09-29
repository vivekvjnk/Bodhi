# BODHI: Configurable scientific Knowledge Graph extraction system 
Bodhi is a Large Language Model (LLM)-powered, **highly configurable**, scientific knowledge graph extraction system. It features **multiple validation and feedback loops** to ensure reliability and precision.

# How to use?
Bodhi uses YAML files for configuration. Configuration files are compatible with OmegaConf. Hydra is used to orchestrate experiments of configuration ablations. 

## Minimum configuration
A config file in yaml format with following parameters
```yaml 
# config.yml
#========================
# LLM configurations
#----------------------------
fast_model: "gemini-2.5-flash-lite" 
general_model: "gemini-2.5-flash-lite" # Used most widely across the system
thinking_model: "gemini-2.5-pro" # Used for resolving impasses resulted from repeating loops in the system
inference_engine: "vertexai" # Supports Ollama and Vertexai

# Storage configurations
#----------------------------
storage_backend: "LocalStorage" # Current implementation supports File System based storage. LocalStorage uses standard python OS libraries for file management. Future versions will support object storage backends such as MinIO.
storage_dir: "tests/storage" # The root directory for all the artifacts. Bodhi will build a folder hierarchy on top of this root directory to store all artifacts generated during KG extraction

# KG Extraction configurations
#----------------------------
max_num_threads: 18 # Maximum number of parallel threads for KG extraction
token_limit: 300 # Text unit token length. Each source document is split into text units before KG extraction. This parameter sets the maximum token limit per text unit

# Ablation parameters
#--------------------
priming: True # If enabled, Bodhi will construct a priming summary from the source document and use it as a biasing context for the KG extraction
generic_type_allowance: True # If enabled, entity type "generic" will be allowed for entities which do not belong to any of the other allowed entity types. Bodhi expects a dicitonary of entity types with a brief explanation for each entity type. 

# seed variable for multi sampling 
seed: 0 # This parameter is used to set the seed variable in underlying langchain vertexai and ollama wrappers. This is also used during hydra based experiment orchestration
```
- Bodhi module expects configuration in a dictionary format. It's the users responsibility to prepare and load the configuraitons into the input dictionary. 
    - Through this design choice, we avoided dependence on any one particular config file type. 

## Expected files and storage locations 
Bodhi supports source documents in .md, .pdf and .txt formats.<br>
Source documents are expected to be present under the directory:<br>
`<storage_dir>/data`, where <storage_dir> is the directory specified in the config.yaml file
Sample artifacts directory with 600 token configuration and maximum 18 thread. System split source document("AAAI2024") into 4 chunks and assigned each chunk to a thread for KG extraction(Map step). Finally all the intermediate files are deduplicated and combined to form AAI2024_combined_intermediate_data.yml. From this file, system generates the final graph.
```bash

tests/storage
├── Bodhi
│   └── AAAI2024
│       ├── 0
│       │   └── AAAI2024_intermediate_data.yml
│       ├── 1
│       │   └── AAAI2024_intermediate_data.yml
│       ├── 2
│       │   └── AAAI2024_intermediate_data.yml
│       ├── AAAI2024_combined_intermediate_data.yml # Deduplicated intermediate KG
│       ├── AAAI2024_graph.yml # Final extracted knowledge graph
│       ├── AAAI2024_ref_separated_text.yml # Source text with references separated
│       ├── AAAI2024_text_units.yml  # Tokenized text chunks
│       └── AAAI2024_text.yml
└── data
    └── AAAI2024.md
```

## Finally, How to run Bodhi..
*Refer [sample_use.py](tests/sample_use.py)*

1. Load the configuration dictionary
```python
config_path = "tests/sample_config.yml"
# Load config
config = load_config(config_path)
```
2. Create object of Bodhi with the configuration dictionary
```python
# Prepare Bodhi
bodhi = Bodhi(config=config)
```
3. Prepare an ontology dictionary with allowed entity types 
```python
entity_types = {"task":"Represents a scientific or application-oriented objective that the method is designed to accomplish","method":"Refers to a specific algorithm, model, computational technique, statistical tool, or approach used in the study","dataset":"Refers to a structured collection of data, often from biological, chemical, or clinical sources, used to train, validate, or test methods","generic":"Generic type. Use this if extracted entity doesn't not belong to any other types. Consider this as a type failure fallback. Try not to use this entity type as much as possible"}
# Prepare initial state
ontology = {"entity_types":entity_types}
```
**You must provide an ontology dictionary with allowed entity types.**
4. Choose the source document from which knowledge graph to be extracted. Ensure the document is placed in <storage_dir>/data. For example, `tests/storage/data/AAAI2024.md`.
```python
doc_path = "AAAI2024.md"
```
5. Prepare initial state dictionary for Bodhi
```python 
# Prepare initial state
init_state = {
    "source_path": doc_path,
    "ontology": ontology
}
```
6. Run Bodhi with initial state
```python
# Run Bodhi extraction
bodhi.invoke(init_state)
```
- Primary output: <storage_dir>/Bodhi/<doc_name>_graph.yml (final knowledge graph).
- Intermediate artifacts: Combined KG, text units, and reference-separated text.
    - All the extraction artifacts will be stored in <storage_dir>/Bodhi

# Design
This section discusses about the design and architecture of Bodhi KG extraction system.

## Major design features
- Configurable KG extraction. Following are the major configurable parameters/inputs
    - Priming : Why priming?
        - Each text unit is processed independently in the pipeline. This lead to narrow focused entity/relationship extraction. 
        - System failes to comprehend overall theme of the source with the text unit.
        - Priming summary of the source document is generated at the very beginning. 
        - Observed better domain adherence with priming summary in experiments.
    - Ontology adherence and enforcement
        - Ontology enforcement loop is present in entity extraction. If LLM extracts entities of type not present in ontology dictionary, system will prompt LLM to re-type those entities into one of the available types.
    - Generic type allowance : What difference it make?
        - Increased coverage. Under ontology enforcement, many high priority entities may get missed out from extraction. 
        - LLM classify these high priority entities under type `Generic`
        - It's observed from experiments, that `Generic` type allowance improvises coverage
    - Token count configuration per text unit
        - Lower token count per text unit : Lead to fine grained KG extraction. Prone to high noise
        - Higher token count per text unit: Lead to corase KG extraction. May miss out key concepts 
        - Highly dependent on the LLM model size and LLM input token limit.
            - For Gemini 2.5 flash model the sweet spot is around 500 tokens per text unit
            - Make sure the token count of the overall extraction prompt is within usable context limit of LLM model
    - Storage selection
        - Bodhi uses storage abstraction. This allows usage of different types of storage backends
        - At present, File system based storage layer is implemented as LocalStorage
        - Object storage support is planned for future releases
    - LLM Inference engine and LLM model selection
        - Validated with 
            - small local models(gemma 3:13b, qwen3:12b, Phi4 etc) running through Ollama
            - Gemini-2.0-flash, Gemini-2.5-flash
    - Configurable number of threads for parallel KG extraction
        - Limited by the LLM inference engine rate limiter and Host system resources
        - Default configuration is 18
            - This number is a sweet spot derived for single user VertexAI inference engine with Gemini-2.5-flash

- Multi-threaded 
    - Significantly increase KG extraction speed
    - KG extraction for each text unit is an independent process. Hence chunk level parallelism is possible
- Modular
- Persistent
- Rigorous through validation loops
    - Entity and relationship validation loops to ensure coverage
    - Heimdall for structured output validation
- Deduplication/Resolution
    - Long distance relationship capture
    - Coherent entity description

[Config + Ontology] 
      ↓
[Bodhi Core]
    ├─ [Preprocessing]
    ├─ [Parallel Knowledge Graph Extraction Pipeline]
    |  └─ [Validation & Feedback Loops]
    ├─ [Entity resolution]
    └─ [Storage Backend]
      ↓
[Artifacts + Final KG]


- Bodhi uses Langgraph framework for orchestrating KG extraction process.
- Input and output of `kg_extraction_graph` follows `BodhiState` schema.
    - In LangGraph, **state** serves as the message schema in a message-passing paradigm. Both the input and output of a LangGraph graph are instances of this state, ensuring that all nodes communicate through a shared, typed message structure.

## Few design considerations 
1. Why so many file operations and intermediate files?
We started developing Bodhi using locally hosted LLMs(Ollama) with RTX A2000 12GB graphics chip. There were few quantized small LLMs capable of doing `structured output` during that time. One of the few major bottlenecks was the uncertainity in LLM outputs. Most of the time LLM failed to follow the structured output instructions. This lead us to the design of an LLM wrapper langgraph runnable, which would force LLM to follow formatting instructions through error correction loops. This is `Heimdall`. 
Even after introducing `Heimdall` the pipeline used to break in between KG extraction due to various reasons. Sometimes, it is power loss, LLM stalling due to bug in ollama, etc. Hence we decided to incorporate persistence across major time consuming processes in the pipeline. This way we were able to utilize available time and resources more efficiently. 
One of the fundamental design principle of `Bodhi` is that **it may fail**. Acknowledging this, we introduced persistence across the pipeline so that, even if `Bodhi` fail to extract KG at one go, it will continue from the failure point in the next iteration.


# The Design Philosophy

Bodhi is designed under the assumption that **LLMs deliver great potential but can struggle with precision and consistency unless guided by feedback loops and persistence mechanisms**.

# Bodhi at a glance: three pipelines
![bodhi-Top Level Architecture](docs/diagrams/bodhi-Top%20Level%20Architecture.jpg)

## 1) Preprocessing — make text model-ready

**What it does:**

* Converts the input document to a uniform text format (markdown).
* Splits the document into **text units** using a configurable `token_limit`.

**Why this exists:**
LLMs work best on clean, bounded chunks. Standardizing the format removes parser variance, and chunking keeps every unit within the model’s usable context window so you don’t lose content or truncate prompts.

**Design decisions (top-level):**

* **Canonical format first:** normalize early to reduce downstream ambiguity.
* **Configurable chunking:** `token_limit` is a dial—lower values → finer detail (but noisier), higher values → broader context (but coarser).
* **Deterministic segmentation:** consistent units enable parallel work and reproducible results.

*Architect’s hook:* the chunking policy is intentionally simple here; downstream behavior (quality, speed, cost) is highly sensitive to this one knob.

---

## 2) Parallel KG extraction — turn units into structured signals

**What it does:**

* **Orchestrates and executes** knowledge-graph extraction **in parallel** across those text units.
* **Saves artifacts** to the storage layer during the run.

**Why this exists:**
Each text unit can be processed independently, so parallelism gives near-linear throughput gains while keeping latency practical for long documents. Persisting artifacts makes runs inspectable and recoverable.

**Design decisions (top-level):**

* **Unit-level parallelism:** the natural boundary is the text unit, so concurrency is safe and simple.
* **Orchestration over ad-hoc calls:** a single controller coordinates workers, making rate limits and failures manageable.
* **Artifact-first persistence:** write intermediate outputs as you go to enable debugging, audits, and resume-from-checkpoint.

*Architect’s hook:* the degree of parallelism is a policy choice (bounded by model rate limits and host resources). Persistence is a deliberate trade-off: more I/O for strong observability and fault tolerance.

---

## 3) Entity & relations resolution — unify, then finalize the graph

**What it does:**

1. **Deduplicates** entities and relations produced by parallel extraction.
2. **Saves** the deduplicated/optimized entity-relation data.
3. Builds the final **NetworkX graph** from that optimized representation.

**Why this exists:**
Parallel extraction inevitably creates duplicates and fragmented relationship evidence. A dedicated resolution pass merges equivalents, reconciles conflicts, and ensures the final KG is coherent and analyzable.

**Design decisions (top-level):**

* **Separation of concerns:** keep extraction fast and independent; defer global consistency to a resolver that has the whole picture.
* **Entity-first, then relations:** stabilize the node set before locking in edges for better consistency.
* **Graph as a first-class product:** materialize to NetworkX to enable downstream analytics and visualization immediately.

*Architect’s hook:* the resolver is where global policies live (matching thresholds, tie-breakers, provenance). Small changes here swing precision/recall and graph topology.

---

## How the three fit together

* **Flow:** *Preprocessing* (normalize & segment) → *Parallel KG extraction* (independent, persisted unit processing) → *Resolution* (global dedup + final graph).
* **Guiding theme:** each stage optimizes for a different concern—**clean input**, **throughput with observability**, and **global consistency**—so the system stays understandable, tunable, and reliable.


# Detailed Design 


# 1. Preprocessing

The **Preprocessing stage** prepares raw documents for knowledge graph extraction by ensuring clean, context-preserving text units. It follows a three-step flow: **text extraction & chunking → priming → outlier summarization**.

![Preprocessing](docs/diagrams/preprocessing.jpg)
---

## 1.1 Text Extraction and Chunking

* **Purpose:** Convert heterogeneous source files into standardized text chunks that fit within the LLM’s processing window.
* **Process:**

  * If the source is a **PDF**, text is extracted using the `pymupdf4llm` package.
  * If the source is already text-based (`.md`, `.txt`, `.yml`, etc.), the content is loaded directly.
  * Chunks are generated according to the configured `token_limit`.
  * To preserve linguistic coherence, **SpaCy** is used for sentence boundary detection, ensuring chunks do not split mid-sentence.
* **Design Choice:**

  * Implemented as an **injectable callback dependency**. This makes it easy to swap out the extraction/chunking strategy without affecting downstream logic, as long as the input-output contract remains consistent.

---

## 1.2 Priming

* **Purpose:** Provide a **knowledge graph priming summary** — a high-fidelity contextual guide distilled from the start of the document.
* **Mechanism:**

  * If the `priming` flag is enabled in `config.yml`, the system takes the **first 2000 tokens** of the document and generates a summary capped at **500 tokens**.
  * This priming summary captures **core terminology, domain definitions, and inherent structural connections**.
* **Benefit:** Ensures consistent entity typing and accurate relationship linking across all text units, by anchoring extractors with shared vocabulary and domain context.

---

## 1.3 Outlier Text Unit Summarization

* **Purpose:** Handle text units that are either **highly structured** (e.g., tables, code blocks, numbered lists) or **cognitively dense** (heavy jargon, layered concepts).
* **Process:**

  * These “outlier” text units are detected heuristically.
  * Instead of storing them raw, an LLM-generated summary replaces them in the `text_units` dictionary.
* **Rationale:** Reduces noise, normalizes complex formats, and ensures downstream extractors process meaningful content rather than low-signal or structurally irregular text.

---

## Implementation Notes

* Implemented inside `parallel_kg_extractor.py`.
* Uses **pymupdf4llm** (PDF handling), **SpaCy** (sentence segmentation), and **LLMs** (summarization tasks).
* Configurable knobs: `token_limit` (chunk size), `priming` flag (enable/disable summary generation).

---

**Summary:**
The Preprocessing stage ensures every subsequent pipeline works on clean, bounded, and semantically consistent text units. Its modular design (injectable callbacks, optional priming, selective summarization) balances **robustness** for arbitrary document types with **flexibility** for domain-specific tuning.

# 2. Parallel KG Extraction

The **Parallel KG Extraction stage** is the core engine of Bodhi, responsible for turning preprocessed text units into structured knowledge graphs. To maximize throughput while preserving modularity, it is designed around a **Map–Thread–Reduce paradigm**, with the centerpiece being the **`kg_extraction_graph` runnable**.

---

## 2.1 Map

* **Purpose:** Distribute text units evenly across multiple worker threads for parallel extraction.
* **Process:**

  * Chunks are uniformly allocated so each thread receives a minimum baseline.
  * If the number of chunks is not divisible by thread count, extra units are distributed across the first *n* threads.
  * Empirical testing showed the system performs best with a **higher number of threads and fewer chunks per thread**.
* **Design Choice:**

  * Currently configured for **18 threads**, balancing Vertex AI rate limits with diminishing returns observed beyond this number.
  * Designed for scalability — thread count can be tuned depending on host capabilities and external rate limits.

---

## 2.2 KG Extraction Execution

![Parallel KG Extraction](docs/diagrams/Parallel_KG_Extraction.jpg)<br>
* **Thread Function:**

  * Each worker invokes the shared `invoke_graph_in_thread` function.
  * Prepares the **LangGraph state and metadata**, then calls the `kg_extraction_graph` runnable.

* **`kg_extraction_graph`: The Core Runnable**<br>
![kg_extraction_gaph](docs/diagrams/kg_extraction_graph.jpg)<br>
  * Implements the **entity and relationship extraction loops** as a LangGraph pipeline.
  * Validates extracted entities/relations in situ, improving precision before results are written out.
  * Designed as a **callback abstraction**:

    * Core extraction logic is isolated from orchestration concerns.
    * Collaborators can iterate, extend, or replace KG extraction strategies (e.g., different LLM prompts, new validation heuristics) **without disturbing the parallelization framework**.
  * Implementation resides in `graph_extraction.py`.

* **Implementation Notes:**

  * Custom thread orchestration is used instead of higher-level libraries (e.g., Joblib).
  * Justification: each text unit is of comparable token size, leading to **predictable runtimes** across threads, which simplifies load balancing.

---

## 2.3 Reduce

* **Purpose:** Merge intermediate results from all threads into a unified representation.
* **Process:**

  * Each thread saves extracted knowledge graph artifacts as **YAML files**.
  * The `_reduce_intermediate_files` function aggregates these into a single consolidated YAML file.
  * This output file serves as the foundation for the subsequent **Entity & Relations Resolution** stage.
* **Design Choice:**

  * Intermediate persistence (YAML) ensures partial progress is never lost if execution is interrupted.
  * Output is both human-readable and machine-processable, supporting debugging and downstream automation.

---

## Architectural Rationale

### * **Map–Reduce Paradigm:** 
The system operates on a map–reduce paradigm, where each module processes input artifacts and passes results downstream. Instead of transient message passing, we chose to persist outputs as files in predefined directories. Each stage saves its intermediate artifacts to disk, which are then read by subsequent modules. This design reflects two deliberate choices. First, persistence acts as a safeguard against failure. Given that multiple steps in the extraction process are potential failure points, persisting artifacts ensures that the system can resume from the last successful stage without recomputation. Second, it promotes transparency and reproducibility, as the artifacts serve as checkpoints for debugging, analysis, and verification. Thus, the combination of a modular extraction graph and a persistence-first communication strategy makes the system resilient, extensible, and well-suited for iterative improvement.

### * **Runnable Isolation (`kg_extraction_graph`):** 
By decoupling orchestration from extraction logic, Bodhi ensures that innovation in KG extraction can happen **independently and safely**. This makes the system attractive for collaboration — contributors can focus on improving extraction logic without worrying about breaking parallelism or orchestration.
### * **Resilience via Intermediate Files:** 
The reduce stage doubles as a checkpointing mechanism, improving reliability in production-scale workloads.

---

## Implementation Notes

* Implemented across `parallel_kg_extractor.py` (orchestration) and `graph_extraction.py` (`kg_extraction_graph` runnable).
* Current defaults: **18 threads**, YAML-based artifact storage.
* Configurable knobs: number of threads, thread allocation policy, and the callback implementation of `kg_extraction_graph`.

---

**Summary:**
Parallel KG Extraction transforms text units into structured graph fragments at scale. Its **Map–Thread–Reduce design** balances speed, modularity, and resilience. At its center, the **`kg_extraction_graph` runnable** embodies Bodhi’s philosophy: make the core logic pluggable, so improvements to entity/relationship extraction can evolve independently of system scaffolding. For newcomers, this is “splitting up the work and stitching it back together.” For architects, it’s a showcase of modularity and isolation. For developers, it provides explicit hooks, files, and abstractions to extend or replace without fear.


# 3 Entity & Relations Resolution

![Hybrid entity resolution](docs/diagrams/hybrid_entity_resolution.jpg)

The **Entity & Relations Resolution** stage ensures that the knowledge graph produced in the extraction phase is **clean, coherent, and non-redundant**. It refines raw entities and relationships into an optimized form suitable for analysis or downstream applications.

---

## 3.1 Core Functions

1. **Deduplication of Entities & Relations**

   * Identifies and merges entities that are semantically equivalent.
   * Removes duplicate or redundant relationships across chunks.

2. **Persistence**

   * Saves deduplicated entities and relationships into intermediate files for traceability.
   * Supports recovery and reproducibility if the pipeline is interrupted.

3. **Graph Construction**

   * Generates a final **networkX graph** from the optimized entity–relation information.
   * This graph is the artifact exposed to downstream applications.

---

## 3.2 The Pluggable Hybrid Resolver

The centerpiece of this stage is the **Hybrid Resolver**, designed as a **pluggable, extensible framework** for entity resolution. The original design included **two complementary subsystems**:

* **System 1: Learned Rules**

  * A set of composable, sequentially applied rules for deterministic entity resolution.
  * Present implementation includes two rules:

    * **Rule 1:** Entities with high semantic similarity in their names are merged.

      * If their descriptions are also semantically similar, a single unified description is maintained.
      * If their descriptions differ significantly, all variations are preserved in a description list.
      * The same logic applies to entity types.
    * **Rule 2:** If entities differ *only by numbers* (e.g., “Model A1” vs. “Model A2”), they are treated as **distinct entities**.

      * This corner case arose frequently in research/scientific text, where numbered entities represent different objects.

* **System 2: LLM-based Ambiguity Resolution** *(Planned)*

  * In cases where System 1 rules cannot confidently resolve ambiguity, the entity is deferred to an LLM for clarification.
  * Intended to address borderline semantic cases where learned rules fall short.
  * Not yet implemented due to time constraints, but forms part of the long-term roadmap.

---

## 3.3 Design Rationale

* **Rule-Based Foundation:** Ensures determinism and reproducibility — critical for knowledge graph reliability.
* **Pluggability:** New resolution strategies (lexical, semantic, ontology-based, ML-driven) can be added without altering the pipeline.
* **LLM Escalation (Future):** Keeps the system pragmatic by combining **fast, rule-based resolution** with **flexible, high-recall LLM reasoning** for edge cases.
* **Extensibility:** Future versions plan to introduce **composition rules** to orchestrate multiple resolution strategies together, making the resolver adaptive to different domains.

---

## Implementation Notes

* Implemented in **core.py**.
* Current version includes only **System 1** with two rules.
* Resolution framework already supports plugin-style integration, laying groundwork for future expansion.

---

**Summary:**
Entity & Relations Resolution is where Bodhi consolidates its extracted knowledge into a **usable graph**. Today, it leverages deterministic, rule-based logic to merge and disambiguate entities, with practical heuristics to handle edge cases. Tomorrow, it will expand into a hybrid framework that escalates hard cases to LLMs. For newcomers, this stage is “cleaning up duplicates.” For architects, it’s a flexible **two-tiered resolution strategy**. For implementers, it’s a well-defined plugin interface already in place for extending resolution logic.
