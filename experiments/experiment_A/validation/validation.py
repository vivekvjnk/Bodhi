import json, yaml
from collections import defaultdict
import os 
from omegaconf import DictConfig
from typing import Dict,Any
import logging

from .entity_classification import build_classification_graph
from .fuzzy_adjudication import run_fuzzy_adjudication_pipeline
from Bodhi.utils import estimate_tokens_hf_batch,get_llm_from_config

logger = logging.getLogger(__name__)


class EntityState(dict):
    # Keys we will pass around
    full_text: str
    entities: list[str]
    context_limit: int
    classified: list[dict]
    special_instructions: str
    output_path: str
    config: DictConfig
    helpers:Dict[str,Any]

def scier_load_dataset(dataset_path,source_name=None):
    """
    Load SciER dataset from a file and extract entities.
    """
    logger.info(f"Loading SciER dataset {"source:"+source_name if source_name else ""}...")

    # SciER dataset preparation
    def _scier_extract_entities_from_dict(data_list) -> dict:
        """
        Parse a JSON line containing 'ner' entries and return a dictionary:
        {entity_name: [list of types]}
        """
        entities = defaultdict(list)
        for data in data_list:
            for ent, etype in data.get("ner", []):
                entities[ent].append(etype)
            
        return dict(entities)

    def _scier_extract_evaluation_entities(data_list):
        sentence_list =[]
        entities = defaultdict(defaultdict)
        
        for i,data in enumerate(data_list):
            current_source = data["doc_id"]
            sentence_list.append(data["sentence"])
            if source_name:
                if source_name != current_source:
                    continue
            
            for ent,etype in data.get("ner",[]):
                if ent not in entities or "sources" not in entities[ent]:
                    entities[current_source][ent] = {"sources":[i],"types":[etype]}  
                else:
                    entities[current_source][ent]["sources"].append(i)
                    entities[current_source][ent]["types"].append(etype)
            
        # Now prepare the text content
        doc_string_dict = defaultdict()
        for doc,entity_dict in entities.items():
            e_string_dict = defaultdict()
            for name,entity in entity_dict.items():
                logger.info(f"Doc_name--{doc}--{name}:\nTotal number of sentences: {len(sentence_list)}\nSources:{entity["sources"]}")
                e_string = f"Name:{name}\nSources:{".\n".join([sentence_list[i] for i in entity["sources"]])}\n"
                e_string_dict[name] = e_string
            doc_string_dict[doc] = e_string_dict

        return dict(doc_string_dict)
    
    dataset_list = []
    if os.path.exists(dataset_path):
        with open(dataset_path, 'r') as dataset_file:
            for line in dataset_file:
                data = json.loads(line)
                dataset_list.append(data)
        logger.info(f"Loaded SciER dataset from {dataset_path}")
    else: 
        logger.error(f"Path not found: {dataset_path}")
        raise ValueError(f"Path not found: {dataset_path}")
    entities_dict = _scier_extract_entities_from_dict(dataset_list)

    doc_string_dict = _scier_extract_evaluation_entities(dataset_list)
    logger.info(f"Dataset information\n{'*'*40}\nNumber of unique entities:{len(entities_dict.keys())}\n{'*'*40}\nFrequency of each entities\n{'*'*40}")
    
    return entities_dict,doc_string_dict

def bodhi_load_dataset(paths):
    """
    Load Bodhi graph
    """
    logger.info(f"Loading Bodhi dataset from paths: {paths}")

    def _bodhi_extract_entities_from_dict(data_list)->dict:

        entities = defaultdict(list)
        for data in data_list:
            entities[data['id']] = data['type'].split(",")
        return dict(entities)
    
    def _bodhi_extract_evaluation_entities(data_list):
        e_string_dict = defaultdict()
        for data in data_list:
            # e_string_dict[data['id']] = f"Name:{data['id']}\nTypes:{data["type"]}\nDescription:{data["description"]}\n"
            e_string_dict[data['id']] = f"Name:{data['id']}\nDescription:{data["description"]}\n"
        return dict(e_string_dict)
    
    dataset_list = []
    e_string_dict = defaultdict()
    for path in paths:
        doc_name = path.split("/")[-1].replace("_graph.yml","").replace("doc_","")
        if os.path.exists(path):
            with open(path, 'r') as dataset_file:
                dataset = yaml.safe_load(dataset_file)
                dataset_list = dataset['nodes']
            logger.info(f"Loaded Bodhi dataset from {path}")
        else: 
            logger.error(f"Path doesn't exist: {path}")
            raise ValueError(f"Path doesn't exist: {path}")
        entities_dict = _bodhi_extract_entities_from_dict(dataset_list)
        e_string_dict[doc_name] = _bodhi_extract_evaluation_entities(dataset_list)

    return entities_dict,dict(e_string_dict)
  
def load_full_text(dataset_path):
    
    full_texts = defaultdict()
    prev_source = ""
    if os.path.exists(dataset_path):
        with open(dataset_path, 'r') as dataset_file:
            for line in dataset_file:
                data = json.loads(line)

                current_source = data["doc_id"]
                if prev_source != current_source:
                    prev_source = current_source
                if prev_source in full_texts:
                    full_texts[prev_source] += data["sentence"]
                else:
                    full_texts[prev_source] = data["sentence"]
        logger.info(f"Loaded full texts from {dataset_path}")
    else: 
        logger.error(f"Path not found: {dataset_path}: {os.getcwd()}")
        raise ValueError(f"Path not found: {dataset_path}")
    return dict(full_texts)

def classify_scier(scier_eval_strs,output_path,scier_dataset_path,config):
    # Check if output path already exists. If yes, just return. Classification is already complete
    if os.path.exists(output_path):
        logger.info(f"Classification output already exists at {output_path}, skipping classification.")
        return
    # prepare graph state

    source_text =  load_full_text(dataset_path=scier_dataset_path)
    for doc, entities in scier_eval_strs.items():
        entities_list = list(entities.values())
        helpers = {"logger":logger}
        state:EntityState = {"full_text":source_text[doc], "entities":entities_list, "context_limit": 10000,"output_path":output_path,"special_instructions":"*`Description` field depicts a comprehensive description of the entity.*","config":config,"helpers":helpers}
            
        logger.info(f"Classifying SciER entities for doc: {doc}")
        classification_graph = build_classification_graph()
        classification_graph.invoke(input=state, config={"recursion_limit": 100})

def classify_bodhi(bodhi_eval_strs,output_path,scier_dataset_path,config):
    # Check if output path already exists. If yes, just return. Classification is already complete
    if os.path.exists(output_path):
        logger.info(f"Classification output already exists at {output_path}, skipping classification.")
        return
    
    helpers = {"logger":logger}
    # prepare graph state
    source_text =  load_full_text(scier_dataset_path)
    # scier_entities = scier_eval_strs.values()
    for doc, entities in bodhi_eval_strs.items():
        entities_list = list(entities.values())
        state:EntityState = {"full_text":source_text[doc], "entities":entities_list, "context_limit": 10000,"output_path":output_path,"special_instructions":"*`Source` is the sentence/s from which entity is extracted*","config":config,"helpers":helpers}
        
        logger.info(f"Classifying Bodhi entities for doc: {doc}")
        classification_graph = build_classification_graph()
        classification_graph.invoke(input=state, config={"recursion_limit": 100})

def load_entities(path:str):
    logger.info(f"Loading entities from {path}")
    with open(path,"r") as f:
        entities_dict = yaml.safe_load(f)
    entities_list = entities_dict["method_entities"] + entities_dict["domain_entities"]
    return entities_dict,entities_list

def eval_metrics(gold_standard,bodhi_entities,new_entities_assessment,matches):
    """
    1. **Method Coverage (MC)** — proportion of expected method-related gold entities recovered (e.g., VAE, KL divergence, loss terms, teacher forcing, encoder/decoder, GRU, RDKit, GAN, etc.). Use a gold list of method entities derived from full-document annotation.
    2. **Domain Coverage (DC)** — proportion of expected domain entities recovered (proteins, diseases, datasets, molecules).
    3. **Balance Score (BS)** — MC / (MC + DC) (range 0..1). Value near 0.5 indicates balanced coverage; skew indicates bias.
    4. **Precision / Recall / F1** — computed against gold annotations (separately for METHOD and DOMAIN).
        - **Precision** - TP / (TP + FP)
        - **Recall** - TP / (TP + FN)
        - **F1 score** - 2 * precision * recall / (precision + recall)

        
    # **The Caveat: Mismatch Between Metrics and Task**

    Formal classification metrics like **precision, recall, and F1 score** are designed to evaluate the performance of **discriminative models**. These models are trained to classify or label existing data points from a fixed, predefined set. The metrics rely on the ability to construct a complete **confusion matrix**, which requires every output to be an element of the original dataset with a known ground truth label.

    Generative models, however, are fundamentally different. Their purpose is not to classify but to **create new, original data**. This capability breaks the foundational assumptions of the classification metrics.

    * **Fixed Dataset Assumption**: Classification metrics assume the model's output is limited to a finite set of possibilities defined by the training and test data.
    * **Known Ground Truth**: The ground truth label for every item in the dataset is known. This is essential for calculating true positives, false positives, etc.

    ### **Why Classification Metrics Fail with Generative Models**

    When applied to generative models, these metrics become unreliable or meaningless for several reasons:

    * **Novel Outputs**: A core function of a generative model is to produce items that were not present in the original training data. These "novel" outputs have no corresponding ground truth label.
        * **Example**: If a text-generating model writes a new poem, we can't classify it as a true or false positive because it was not part of the original positive class of poems we were trying to identify.
    * **Incomplete Evaluation**: Since novel outputs can't be categorized in the confusion matrix, metrics like precision and recall cannot be computed for them. This means the metrics fail to evaluate a key aspect of the model's performance—its ability to generate creative, new content.
    * **No "Total Items"**: The concept of $TP+FP+TN+FN$ equaling a total population of items breaks down. A generative model doesn't classify a fixed set of items; its output is dynamic and potentially infinite.

    ### **Alternative Evaluation for Generative Models**

    Because formal classification metrics are unsuitable, generative models are evaluated using alternative methods tailored to their function. These methods focus on the **quality, diversity, and novelty** of the generated content.

    * **Perceptual/Human Evaluation**: This is often the most reliable method, involving human judges who rate the generated content for attributes like coherence, style, and creativity.
    * **Automatic Metrics**: These metrics are used in a variety of generative tasks to compare the generated output to a reference set.

        * **Text Generation**: Metrics like **BLEU** and **ROUGE** measure the similarity of the generated text to a reference text.  While helpful, they don't fully capture linguistic quality or creativity.

    ## **"LLM as a Judge,"**
    ### 1. The Multi-Step Evaluation Process

    Instead of a single metric, design a pipeline with a few key steps to get a comprehensive view of system's performance.

    #### **Step 1: Baseline F1 Score** First, run LLM-based KG generation system on the SciERC test set and compute the standard, strict-match F1 score. This gives a direct, though potentially pessimistic, baseline that can be compared against other models. This metric is a solid measure of system's ability to extract entities that match the ground truth exactly.

    #### **Step 2: LLM-Based Factual Consistency and Novelty Check**
    This is the core of resource-constrained evaluation. Use a separate, powerful LLM (like GPT-4 or a fine-tuned open-source model) as a "judge."

    * **Objective**: The judge LLM's task is to verify the factual correctness of the entities system extracted that were *not* in the SciERC ground truth. These are **False Positives (FP)**.
    * **Prompting**: Craft a detailed prompt for the judge LLM. The prompt should include:
        * The source text (the scientific paper sentence/paragraph).
        * The entity extracted by system that was marked as an FP.
        * Clear instructions for the judge LLM: "Is the following entity, extracted from the text, factually correct? Please respond with 'Yes' or 'No'. If 'Yes,' please provide a short explanation."
    * **Execution**:
        1.  For the SciERC dataset, get system's entity extractions.
        2.  Compare them to the ground truth to identify all FPs.
        3.  Feed each FP, along with the source text, to judge LLM.
        4.  Collect the judgments.

    #### **Step 3: Calculating an Adjusted Score**

    * **Redefining TP and FP**: The FPs that the judge LLM verified as factually correct are no longer considered "false." Reclassify them as **"True Novelties" (TN)** or simply add them back into True Positive count for a final, adjusted score.
    * **The Adjusted F1 Score**:
        * $Adjusted\ Precision = \frac{TP_{Strict} + TP_{Novel}}{TP_{Strict} + TP_{Novel} + FP_{False}}$
        * $Adjusted\ Recall = \frac{TP_{Strict} + TP_{Novel}}{TP_{Strict} + TP_{Novel}+ FN}$
        * $Adjusted\ F1 = 2 \cdot \frac{Adjusted\ Precision \cdot Adjusted\ Recall}{Adjusted\ Precision + Adjusted\ Recall}$

        Where:
        * $TP_{Strict}$: Entities that exactly match the ground truth.
        * $TP_{Novel}$: Entities that did not match the ground truth but were verified as correct by the judge LLM.
        * $FP_{False}$: Entities that the judge LLM identified as incorrect (hallucinations or mistakes).
        * $FN$: Entities from the ground truth that the system missed.
    """
    
    bodhi_domain = bodhi_entities["domain_entities"]
    bodhi_method = bodhi_entities["method_entities"]

    gs_domain = gold_standard["domain_entities"]
    gs_method = gold_standard["method_entities"]

    # Domain metrics
    domain_tp = [item for item in matches if item in gs_domain]
    method_tp = [item for item in matches if item in gs_method]
    domain_fp = [item for item in bodhi_domain if item not in gs_domain]
    domain_fn = [item for item in gs_domain if item not in bodhi_domain]
    domain_tp_no = len(domain_tp)
    domain_fp_no = len(domain_fp)
    domain_fn_no = len(domain_fn)

    domain_precision = domain_tp_no / (domain_tp_no + domain_fp_no) if (domain_tp_no + domain_fp_no) > 0 else 0
    domain_recall = domain_tp_no / (domain_tp_no + domain_fn_no) if (domain_tp_no + domain_fn_no) > 0 else 0
    domain_f1 = 2 * domain_precision * domain_recall / (domain_precision + domain_recall) if (domain_precision + domain_recall) > 0 else 0

    # Method metrics
    method_tp_no = len(method_tp)
    method_fp_no = len([item for item in bodhi_method if item not in gs_method])
    method_fn_no = len([item for item in gs_method if item not in bodhi_method])

    method_precision = method_tp_no / (method_tp_no + method_fp_no) if (method_tp_no + method_fp_no) > 0 else 0
    method_recall = method_tp_no / (method_tp_no + method_fn_no) if (method_tp_no + method_fn_no) > 0 else 0
    method_f1 = 2 * method_precision * method_recall / (method_precision + method_recall) if (method_precision + method_recall) > 0 else 0


    domain_coverage = len(domain_tp)/len(gs_domain)
    method_coverage = len(method_tp)/len(gs_method)


    # Adjusted domain metrics
    novel_entities = [key for key,item in new_entities_assessment.items() if item["score"]>0.6]
    adjusted_domain_tp = domain_tp + [item for item in novel_entities if item in bodhi_domain] 
    adjusted_domain_fp = [item for item in bodhi_domain if item not in adjusted_domain_tp]
    adjusted_domain_fn = [item for item in gs_domain if item not in adjusted_domain_tp]
    
    adjusted_domain_tp_no = len(adjusted_domain_tp)
    adjusted_domain_fp_no = len(adjusted_domain_fp)
    adjusted_domain_fn_no = len(adjusted_domain_fn)

    adjusted_domain_precision = adjusted_domain_tp_no / (adjusted_domain_tp_no + adjusted_domain_fp_no) if (adjusted_domain_tp_no + adjusted_domain_fp_no) > 0 else 0
    adjusted_domain_recall = adjusted_domain_tp_no / (adjusted_domain_tp_no + adjusted_domain_fn_no) if (adjusted_domain_tp_no + adjusted_domain_fn_no) > 0 else 0
    adjusted_domain_f1 = 2 * adjusted_domain_precision * adjusted_domain_recall / (adjusted_domain_precision + adjusted_domain_recall) if (adjusted_domain_precision + adjusted_domain_recall) > 0 else 0


    # Adjusted Method metrics
    adjusted_method_tp = method_tp + [item for item in bodhi_method if item in novel_entities] 
    adjusted_method_fp = [item for item in bodhi_method if item not in adjusted_method_tp]
    adjusted_method_fn = [item for item in gs_method if item not in adjusted_method_tp]
    
    adjusted_method_tp_no = len(adjusted_method_tp)
    adjusted_method_fp_no = len(adjusted_method_fp)
    adjusted_method_fn_no = len(adjusted_method_fn)

    adjusted_method_precision = adjusted_method_tp_no / (adjusted_method_tp_no + adjusted_method_fp_no) if (adjusted_method_tp_no + adjusted_method_fp_no) > 0 else 0
    adjusted_method_recall = adjusted_method_tp_no / (adjusted_method_tp_no + adjusted_method_fn_no) if (adjusted_method_tp_no + adjusted_method_fn_no) > 0 else 0
    adjusted_method_f1 = 2 * adjusted_method_precision * adjusted_method_recall / (adjusted_method_precision + adjusted_method_recall) if (adjusted_method_precision + adjusted_method_recall) > 0 else 0


    precision = (domain_tp_no+method_tp_no) / ((domain_tp_no+method_tp_no) + (method_fp_no + domain_fp_no))
    recall = (domain_tp_no+method_tp_no) / ((domain_tp_no+method_tp_no) + (domain_fn_no+method_fn_no))
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Adjusted overall metrics
    adjusted_precision = (adjusted_method_tp_no + adjusted_domain_tp_no) / ((adjusted_method_tp_no + adjusted_domain_tp_no) + (adjusted_domain_fp_no + adjusted_method_fp_no))
    adjusted_recall = (adjusted_method_tp_no + adjusted_domain_tp_no) / ((adjusted_method_tp_no + adjusted_domain_tp_no) + (adjusted_domain_fn_no + adjusted_method_fn_no))
    adjusted_f1 = 2 * adjusted_precision * adjusted_recall / (adjusted_precision + adjusted_recall) if (adjusted_precision + adjusted_recall) > 0 else 0

    return {
        "domain_coverage": domain_coverage,
        "method_coverage": method_coverage,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "domain_precision": domain_precision,
        "domain_recall": domain_recall,
        "domain_f1": domain_f1,
        "method_precision": method_precision,
        "method_recall": method_recall,
        "method_f1": method_f1,
        "adjusted_domain_precision": adjusted_domain_precision,
        "adjusted_domain_recall": adjusted_domain_recall,
        "adjusted_domain_f1": adjusted_domain_f1,
        "adjusted_method_precision": adjusted_method_precision,
        "adjusted_method_recall": adjusted_method_recall,
        "adjusted_method_f1": adjusted_method_f1,
        "adjusted_precision": adjusted_precision,
        "adjusted_recall": adjusted_recall,
        "adjusted_f1": adjusted_f1
    }

def evaluate(paths:dict,source_name,config):
    """
    Outputs
    ======
    Classification output path (For bodhi and scierc)
    Metrics output path

    Inputs
    ======
    Bodhi output path
    SciERC dataset path

    Flow
    =====
    Load SciERC and Bodhi content
    Classify them to Method and Domain entities
    Fuzzy + LLM adjudicated matching between SciERC entities and Bodhi entities
    Calculate metrics
    """
    logger.info("Starting evaluation pipeline...")
    
    # Input paths
    scier_dataset_path = paths["scier_dataset_input_path"]
    bodhi_src_paths = paths["bodhi_src_input_path"]

    
    # Output paths
    bodhi_classify_output_path = paths["bodhi_classify_output_path"]
    scier_classify_output_path = paths["scier_classify_output_path"]
    validation_output_path =  paths["validation_output_path"]
    validation_metrics_path = paths["validation_metrics_output_path"]
    

    _,scier_eval_strs = scier_load_dataset(dataset_path=scier_dataset_path,
                                           source_name=source_name)
    
    classify_scier(scier_eval_strs=scier_eval_strs,
                   output_path=scier_classify_output_path,
                   scier_dataset_path=scier_dataset_path,
                   config=config)
    scier_entities_dict,scier_entities = load_entities(path=scier_classify_output_path) 
        
    bodhi_eval_strs_dict,bodhi_eval_strs = bodhi_load_dataset(paths=[bodhi_src_paths])

    # Experiment specific line
    classify_bodhi(bodhi_eval_strs=bodhi_eval_strs,
                   output_path=bodhi_classify_output_path,
                   scier_dataset_path=scier_dataset_path,config=config)
    bodhi_entities_dict,bodhi_entities = load_entities(path=bodhi_classify_output_path) 
    
    llm = get_llm_from_config(config=config)
    logger.info("Running fuzzy adjudication pipeline...")
    results = run_fuzzy_adjudication_pipeline(gold_entities=scier_entities,
                                              bodhi_entities=bodhi_entities,
                                              tokenizer=estimate_tokens_hf_batch,llm_callable=llm)
    
    eval_results = eval_metrics(bodhi_entities=bodhi_entities_dict,gold_standard=scier_entities_dict,
    new_entities_assessment=results["novel_assessment"],matches = results["matches"])
    logger.info(f"Final evaluation results: \n{eval_results}")
    
    with open(validation_output_path,"w") as f:
        yaml.dump(results,stream=f)
    logger.info(f"Evaluation results written to {validation_output_path}")
    
    with open(validation_metrics_path,"w") as f:
        yaml.dump(eval_results,stream=f)
    logger.info(f"Evaluation metrics written to {validation_metrics_path}")
    
if __name__ == "__main__1":
    # validate()
    from infra.utils.utils import Config
    bodhi_outputs = "Bodhi/experiments/prompt_engineering/experiment_A/bodhi_outputs"
    stage = "Stage_2"
    sample = "iter_1"
    token_count = "token_250"
    doc_name = "AAAI2024"
    experiment_name = "A_4"
    bodhi_src_paths = [
        f"{bodhi_outputs}/{stage}_{sample}/{token_count}/doc_{doc_name}/{experiment_name}/doc_{doc_name}_graph.yml",
    ]
    paths={
        "scier_dataset_input_path":"Bodhi/experiments/prompt_engineering/experiment_A/test_data/sciER_dataset_section.jsonl",
        "bodhi_classify_output_path": "Bodhi/experiments/prompt_engineering/experiment_A/validation/classification_outputs/A4_classification_results.yml",
        "scier_classify_output_path": "Bodhi/experiments/prompt_engineering/experiment_A/validation/classification_outputs/scier_classifications.yml",
        "validation_output_path": "Bodhi/experiments/prompt_engineering/experiment_A/validation/classification_outputs/matches.yml",
        "validation_metrics_output_path": "Bodhi/experiments/prompt_engineering/experiment_A/validation/classification_outputs/metrics.yml",
        "bodhi_src_input_path":bodhi_src_paths}
    config = Config(config_path="configs/config.yml")

    evaluate(paths=paths,config=config)

if __name__ == "__main__":
    # scier load dataset bug fix
    scier_dataset_path="Bodhi/kg_quality_analysis/Datasets/SciER/LLM/superset.jsonl"
    _,scier_eval_strs = scier_load_dataset(dataset_path=scier_dataset_path)
    print(f"Length of scier_strs-210920315: {len(scier_eval_strs["210920315"])}")
    with open("scier_strs.yaml","w") as f:
        yaml.dump(scier_eval_strs,f)