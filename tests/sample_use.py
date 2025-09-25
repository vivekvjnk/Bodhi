import yaml

from Bodhi import Bodhi
from Bodhi.utils import set_global_seed
import logging

# Set up top-level logging
log_file = "bodhi_sample_use.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def load_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def main():
    # Paths
    config_path = "tests/sample_config.yml"
    sample_doc_path = "AAAI2024.md"

    # Load config
    config = load_config(config_path)

    # Prepare Bodhi
    bodhi = Bodhi(config=config)

    entity_types = {"with_generic_type": {"task":"Represents a scientific or application-oriented objective that the method is designed to accomplish","method":"Refers to a specific algorithm, model, computational technique, statistical tool, or approach used in the study","dataset":"Refers to a structured collection of data, often from biological, chemical, or clinical sources, used to train, validate, or test methods","generic":"Generic type. Use this if extracted entity doesn't not belong to any other types. Consider this as a type failure fallback. Try not to use this entity type as much as possible"},
    "without_generic_type":{"task":"Represents a scientific or application-oriented objective that the method is designed to accomplish","method":"Refers to a specific algorithm, model, computational technique, statistical tool, or approach used in the study","dataset":"Refers to a structured collection of data, often from biological, chemical, or clinical sources, used to train, validate, or test methods"}}
    
    # Prepare initial state
    ontology = {"entity_types":entity_types["with_generic_type"]}
    init_state = {
        "source_path": sample_doc_path,
        "ontology": ontology
    }

    # Run Bodhi extraction
    bodhi.invoke(init_state)

    print(f"Extraction completed")

if __name__ == "__main__":
    main()