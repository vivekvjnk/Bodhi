# BODHI: Configurable scientific Knowledge Graph extraction system 
Bodhi is an LLM based highly configurable knowledge graph extraction system with multiple validation loops.

# How to use?
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
