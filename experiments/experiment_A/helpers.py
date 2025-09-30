from validation.validation import load_full_text
import yaml,random

from pathlib import Path
import yaml
from typing import Dict, Any

def get_experiment_metrics_pathlib(parent_dir: str = "results") -> Dict[str, Any]:
    """
    Finds all 'eval_metrics.yml' files under a parent directory using pathlib, 
    reads their content, and returns a dictionary where keys are the relative 
    paths (from the parent directory) and values are the file contents.

    Args:
        parent_dir (str): The path to the parent directory (e.g., 'results').
                          Defaults to 'results'.

    Returns:
        Dict[str, Any]: A dictionary of experiment metrics.
    
    Example Usage (assuming 'results' directory exists with the structure):
    results_data = get_experiment_metrics_pathlib(parent_dir="results")
    """
    metrics_dict = {}
    
    # 1. Create a Path object for the parent directory
    parent_path = Path(parent_dir)
    
    # 2. Check if the parent directory exists
    if not parent_path.is_dir():
        print(f"Error: Parent directory '{parent_dir}' not found.")
        return metrics_dict
    
    # 3. Use the powerful Path.glob() to find all files recursively
    # '**/eval_metrics.yml' means "look in this directory and all subdirectories
    # for a file named 'eval_metrics.yml'"
    for full_path in parent_path.glob('**/eval_metrics.yml'):
        # The full_path is a Path object for the 'eval_metrics.yml' file
        
        # 4. Get the relative path directly using the Path object's .relative_to() method.
        # This handles the unique key requirement.
        relative_path = str(full_path.relative_to(parent_path))

        try:
            # 5. Read the content. Path objects have a .open() method that works 
            # with 'with open', and using .read_text() is an option for simplicity.
            # Using .open() here for consistency with yaml.safe_load's expectation.
            with full_path.open('r') as f:
                # Load YAML content
                content = yaml.safe_load(f)
            
            # 6. Store the content
            metrics_dict[relative_path] = content

        except FileNotFoundError:
            # This case is unlikely due to glob, but remains for robustness
            print(f"Error: File not found at {full_path}")
        except yaml.YAMLError as e:
            # Handle potential YAML parsing errors
            print(f"Error parsing YAML file {full_path}: {e}")
        except Exception as e:
            # Handle other potential I/O errors
            print(f"An unexpected error occurred while reading {full_path}: {e}")

    return metrics_dict



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