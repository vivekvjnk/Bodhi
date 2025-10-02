"""
patterns to search for 
1. "==== Knowledge Graph Extraction Report (extract_knowledge_graph_parallel) ====" : KG extraction result 
    Example : 
        ==== Knowledge Graph Extraction Report (extract_knowledge_graph_parallel) ====
        Source: 244256
        Total Chunks Processed: 11
        Threads Used: 11
        Chunks per Thread: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        Entities Extracted: 160
        Relationships Extracted: 221
        Combined Intermediate File: Bodhi/244256/244256_combined_intermediate_data.yml
        Total Time Taken: 39.02 seconds
        ==========================================

2. "[heimdall.core][WARNING] - Validation failed:" : Heimdall validation failures 
    Example : 
        [heimdall.core][WARNING] - Validation failed: mapping values are not allowed here
        in "<unicode string>", line 1, column 89:
            ... ut there's a missed relationship: "AlexNet-based Faster R-CNN" i ... 
                                                ^

3. "NameAndDescriptionRule Resolution Metrics ---" : Entity resolution metrics
    Example : 
        NameAndDescriptionRule Resolution Metrics --- 244256 
        ******************************
        - Total number of entities before resolution: 104
        - Total number of entities after resolution: 95
        - Total number of descriptions in all resolved nodes before resolution: 67
        - Total number of descriptions in all resolved nodes after resolution: 56
        ******************************
4. "Deduplicated entities:" : dictionary of deduplicated entities
    Example : 
        {'Localization': {'type': ['task', 'task', 'task'], 'description': ['The task of determining the position of objects within an image.', 'The task of determining the location of an object within an image.', 'A task that VGG16 network has achieved high accuracy in.'], 'source_chunk_index': [0, 1, 6]}, 'R-CNN': {'type': ['method', 'method', 'method', 'method', 'method', 'method', 'method', 'method', 'method', 'method'], 'description': ['A method for object detection, which has faster variants.', 'A method that reuses shared convolution features for region proposals.', 'A region-based convolutional neural network used for object detection.', 'A method used for object detection, which involves region proposal and classification.', 'A technique that uses ROI Pooling.', 'A branch within the Faster R-CNN architecture, utilizing fully connected layers.', 'A region-based convolutional neural network model.', 'A region-based convolutional neural network used for object detection.', 'A region-based convolutional neural network model.', 'A method used for object detection, with modifications involving context windows.'], 'source_chunk_index': [0, 1, 2, 2, 4, 5, 7, 8, 9, 10]}, 'Car detection': {'type': ['task', 'task'], 'description': ['The task of identifying and locating cars within images.', 'The objective of identifying and locating cars within images.'], 'source_chunk_index': [0, 10]},...}


"""
import re
from typing import Dict, Any
from collections import defaultdict

from helpers import find_and_read_files

# 1. KG info extraction
def parse_kg_report(log_text: str) -> Dict[str, Any]:
    """
    Parses the 'Knowledge Graph Extraction Report' section from the log text
    and extracts all key-value pairs, converting numeric values to their
    appropriate types (float for time, int for counts).

    Args:
        log_text (str): The full log content as a string.

    Returns:
        Dict[str, Any]: A dictionary containing the extracted key-value pairs.
                        Returns an empty dict if the report is not found.
    """
    results: Dict[str, Any] = {}
    
    # Define markers to find the report section
    start_marker = "==== Knowledge Graph Extraction Report"
    end_marker = "=========================================="
    
    # 1. Find the report section
    try:
        # Find the content between the start and end markers
        start_index = log_text.index(start_marker)
        end_index = log_text.index(end_marker, start_index)
        # Add a buffer for the start marker line itself
        report_section = log_text[start_index:end_index].strip()
    except ValueError:
        print("Error: Knowledge Graph Extraction Report markers not found in the log.")
        return results

    # 2. Use a regex pattern to capture all "Key: Value" lines in the section
    # Pattern: ^([\w\s\/]+):\s*(.*)$
    # ^([\w\s\/]+):    -> Captures the Key (letters, spaces, and '/', followed by a colon)
    # \s*(.*)$         -> Captures the Value (any characters until the end of the line)
    
    # Split the section into lines and iterate
    for line in report_section.split('\n'):
        line = line.strip()
        
        # Skip header lines or empty lines
        if not line or line.startswith("===") or "Knowledge Graph Extraction Report" in line:
            continue

        match = re.match(r"^([\w\s\/]+):\s*(.*)$", line)
        
        if match:
            key = match.group(1).strip()
            value_raw = match.group(2).strip()
            
            # 3. Process and store the result based on the key
            if key == "Total Time Taken":
                # Clean up the value by removing " seconds" and converting to float
                try:
                    time_value = value_raw.replace(" seconds", "").strip()
                    results[key] = float(time_value)
                except ValueError:
                    results[key] = value_raw # Keep as string if conversion fails
                    
            elif key in ["Total Chunks Processed", "Threads Used", "Entities Extracted", "Relationships Extracted"]:
                # Convert known count fields to integers
                try:
                    results[key] = int(value_raw)
                except ValueError:
                    results[key] = value_raw
            
            elif key == "Source":
                # The 'Source' value is often an ID and should be kept as string
                results[key] = value_raw
                
            else:
                # Keep other values (like file paths or lists) as strings
                results[key] = value_raw

    return results


if __name__ == "__main__":
    # Load all main.log files 
    logs = find_and_read_files(file_name="main.log",parent_dir="results")
    kg_reports  = defaultdict()
    for path,log in logs.items():
        kg_reports[path] = parse_kg_report(log_text=log)

    print(f"Length : {len(kg_reports)}")