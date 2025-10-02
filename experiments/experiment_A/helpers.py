from validation.validation import load_full_text
import yaml,random

from pathlib import Path
import yaml
from typing import Dict, Any

def find_and_read_files(
    file_name: str = "eval_metrics.yml",
    parent_dir: str = "results"
) -> Dict[str, Any]:
    """
    Finds all files matching the given name under a parent directory using pathlib, 
    reads their content, and returns a dictionary where keys are the relative 
    paths (from the parent directory) and values are the file contents.

    For YAML files (.yml, .yaml), the content is parsed using yaml.safe_load.
    For other file types (text, markdown, etc.), the raw text content is returned.

    Args:
        file_name (str): The name of the file to search for (e.g., 'eval_metrics.yml',
                        'results.txt', 'README.md'). Defaults to 'eval_metrics.yml'.
        parent_dir (str): The path to the parent directory (e.g., 'results').
                          Defaults to 'results'.

    Returns:
        Dict[str, Any]: A dictionary of experiment metrics/content.
    
    Example Usage:
        # For YAML files
        results_data = get_experiment_metrics_pathlib(file_name="eval_metrics.yml", parent_dir="results")
        
        # For text/markdown files
        readme_data = get_experiment_metrics_pathlib(file_name="README.md", parent_dir="docs")
        notes_data = get_experiment_metrics_pathlib(file_name="notes.txt", parent_dir="experiments")
    """
    metrics_dict = {}
    
    # 1. Create a Path object for the parent directory
    parent_path = Path(parent_dir)
    
    # 2. Check if the parent directory exists
    if not parent_path.is_dir():
        print(f"Error: Parent directory '{parent_dir}' not found.")
        return metrics_dict
    
    # 3. Determine file type based on extension
    file_extension = Path(file_name).suffix.lower()
    is_yaml = file_extension in ['.yml', '.yaml']
    
    # 4. Use Path.glob() to find all matching files recursively
    for full_path in parent_path.glob(f"**/{file_name}"):
        # Get the relative path
        relative_path = str(full_path.relative_to(parent_path))

        try:
            if is_yaml:
                # 5a. For YAML files: parse the content
                with full_path.open('r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
            else:
                # 5b. For other files: read raw text content
                content = full_path.read_text(encoding='utf-8')
            
            # 6. Store the content
            metrics_dict[relative_path] = content

        except FileNotFoundError:
            print(f"Error: File not found at {full_path}")
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {full_path}: {e}")
        except UnicodeDecodeError as e:
            print(f"Error reading file {full_path} (encoding issue): {e}")
        except Exception as e:
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