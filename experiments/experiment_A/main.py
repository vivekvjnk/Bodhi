"""
Author: Prophet System Team
Date: 2024-06-15
"""
from pathlib import Path
import os
from typing import List
import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig,open_dict

from Bodhi import Bodhi

from Bodhi.utils import set_global_seed

from .validation.validation import evaluate, load_full_text


def get_doc(dataset_path, dest_path, limit=None,document_name=None):
    # If a limit is set, initialize a counter
    count = 0 
    
    dataset = load_full_text(dataset_path=dataset_path)
    
    if document_name:
        # load the specific document and send back
        doc_name = f"{document_name}.md"
        doc_path = os.path.join(dest_path, doc_name)
        if not os.path.isfile(doc_path):
            with open(doc_path, "w") as f:
                f.write(dataset[document_name])
        return doc_name

# Joblib parallel run time : 3 experiments : 2m33.022s
# Sequential run time : 3 experiments : 6m15.104s
@hydra.main(version_base="1.1",config_path="../configs",config_name="experiment_config")
# @hydra.main(version_base="1.1",config_path="../../../configs",config_name="experiment_config_joblib")
def exec_experiment(cfg:DictConfig):

    print(f"Storage directory is: {cfg.general_config.storage_dir}")
    hydra_config = HydraConfig.get()

    priming = cfg["general_config"]["priming"]
    generic_type = cfg["general_config"]["generic_type_allowance"]

    seed = cfg["general_config"]["seed"]
    set_global_seed(seed)

    prompt_paths = {"A_1":"experiments.experiment_A.prompts.A_1_with_priming_summary_without_generic_type",
                    "A_2":"experiments.experiment_A.prompts.A_2_without_priming_summary_without_generic_type",
                    "A_3":"experiments.experiment_A.prompts.A_3_with_priming_summary_with_generic_type",
                    "A_4":"experiments.experiment_A.prompts.A_4_without_priming_summary_with_generic_type"}
    
    entity_types = {"with_generic_type": {"Task":"Represents a scientific or application-oriented objective that the method is designed to accomplish","Method":"Refers to a specific algorithm, model, computational technique, statistical tool, or approach used in the study","Dataset":"Refers to a structured collection of data, often from biological, chemical, or clinical sources, used to train, validate, or test methods","generic":"Generic type. Use this if extracted entity doesn't not belong to any other types. Consider this as a type failure fallback. Try not to use this entity type as much as possible"},
    "without_generic_type":{"Task":"Represents a scientific or application-oriented objective that the method is designed to accomplish","Method":"Refers to a specific algorithm, model, computational technique, statistical tool, or approach used in the study","Dataset":"Refers to a structured collection of data, often from biological, chemical, or clinical sources, used to train, validate, or test methods"}}
    
    if priming and generic_type:
        prompt = prompt_paths["A_3"]
        entity_type = entity_types["with_generic_type"]
    
    elif (not priming) and generic_type:
        prompt = prompt_paths["A_4"]
        entity_type = entity_types["with_generic_type"] 
    
    elif priming and (not generic_type):
        prompt = prompt_paths["A_1"]
        entity_type = entity_types["without_generic_type"]   
    
    elif (not priming) and (not generic_type):
        prompt = prompt_paths["A_2"]
        entity_type = entity_types["without_generic_type"]
    
    # add prompt to the config dictionary
    with open_dict(cfg):
        cfg.general_config.prompt_path = prompt

    ontology = {"entity_types":entity_type}

    bodhi = Bodhi(config=cfg["general_config"])
    
    hydra_op_dir = hydra_config.runtime.output_dir
    project_root_dir = hydra.utils.get_original_cwd()
    
    print(f"Hydra output dir: {hydra_op_dir}\nProject root dir: {project_root_dir}")
    
    scier_dataset_input_path=os.path.join(project_root_dir,"experiments/Datasets/SciER/LLM/superset.jsonl")

    dataset_sources_path = os.path.join(hydra_op_dir,"storage/data")
    os.makedirs(dataset_sources_path,exist_ok=True)

    def run(source):
        source_name = Path(source).stem  # Remove file extension
        init_state = {"source_path": source,"ontology": ontology}
        
        bodhi.invoke(init_state)
        
        exec_evaluate(cfg=cfg,output_dir=hydra_op_dir,doc_name=source_name)

    # for doc_name in get_doc(dataset_path=scier_dataset_input_path,
    #                         dest_path=dataset_sources_path):
    #     run(source=doc_name)
    doc_name = get_doc(dataset_path=scier_dataset_input_path,
                            dest_path=dataset_sources_path,
                            document_name=cfg["general_config"]["document_name"])
    run(source=doc_name)

def ensure_directories(paths:List[str])->None:
    print(f"Paths :{paths}")
    for path_str in paths:
        if "input" in path_str: 
            continue # Dont create paths for evaluation input. They should be generated by test execution
        
        path = Path(path_str)
        if path.suffix:
            dir_to_create = path.parent
        else:
            dir_to_create = path
        os.makedirs(dir_to_create,exist_ok=True)

def exec_evaluate(cfg,output_dir,doc_name):
    source_name = doc_name.replace("doc_","")
    bodhi_src_path = f"{output_dir}/storage/Bodhi/{doc_name}/{doc_name}_graph.yml"
    eval_results_root = os.path.join(output_dir,doc_name,"eval_results")
    project_root_dir = hydra.utils.get_original_cwd()

    paths={
        "scier_dataset_input_path":f"{project_root_dir}/experiments/Datasets/SciER/LLM/superset.jsonl",
        "bodhi_src_input_path":bodhi_src_path,
        "scier_classify_output_path": f"{project_root_dir}/experiments/prompt_engineering/experiment_A/test_data/scier_{doc_name}.yml",
        "bodhi_classify_output_path": os.path.join(eval_results_root,"classification_results.yml"),
        "validation_output_path": os.path.join(eval_results_root,"eval_output.yml"),
        "validation_metrics_output_path": os.path.join(eval_results_root,"eval_metrics.yml"),
        }
    
    # Make necessary directories for outputs 
    ensure_directories(list(paths.values()))
    evaluate(paths=paths,source_name=source_name,config=cfg.general_config)

if __name__ == "__main__":    
    exec_experiment()
    