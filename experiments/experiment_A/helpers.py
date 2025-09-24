from .validation.validation import load_full_text
import yaml,random

def save_doc_names(dataset_path, dest_path, limit=None):
    # If a limit is set, initialize a counter
    dataset = load_full_text(dataset_path=dataset_path)
    doc_names = [str(data) for data in dataset.keys()][:limit]
    doc_limit = limit if limit else len(doc_names)
    possible_indices = range(len(doc_names))
    random_indices = random.sample(possible_indices,doc_limit)
    selected_docs = [doc_names[i] for i in random_indices]
    o_dict = {"doc_names":",".join(selected_docs)}
    with open(dest_path,"w") as f:
        yaml.safe_dump(o_dict,f)
    

if __name__ == "__main__":
    dataset_path ="Bodhi/experiments/Datasets/SciER/LLM/superset.jsonl"
    doc_name_config_path = "configs/general_config/doc_names.yaml"
    save_doc_names(dataset_path=dataset_path,dest_path=doc_name_config_path,limit=10)