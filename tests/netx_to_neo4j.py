import networkx as nx
import json
from typing import List
import os
import yaml
from networkx.readwrite import json_graph

def _format_properties(props: dict) -> str:
    """
    Formats a dictionary of properties into a Cypher map string.
    Keys like 'id', 'type', 'source', and 'target' are ignored as they are
    handled separately in the node/relationship patterns.

    Args:
        props: The dictionary of properties.

    Returns:
        A string formatted as a Cypher map (e.g., "{key1: 'value1', key2: 123}").
    """
    if not props:
        return ""

    # Create a copy to avoid modifying the original dictionary
    props_to_format = props.copy()
    
    # These keys are structural and not considered properties in the Cypher query
    for key in ['id', 'type', 'source', 'target']:
        props_to_format.pop(key, None)

    if not props_to_format:
        return ""

    # Use json.dumps for each value to handle strings, numbers, booleans, and lists correctly
    cypher_props = [
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in props_to_format.items()
    ]
    
    return f"{{{', '.join(cypher_props)}}}"

def _format_labels(type_str: str, default_label: str = "Node") -> str:
    """
    Formats a comma-separated type string into a Cypher label string.
    Example: "METHOD, METHOD, AI" becomes ":METHOD:AI".

    Args:
        type_str: The string containing node types/labels.
        default_label: The default label to use if type_str is empty.

    Returns:
        A Cypher-compatible label string (e.g., ":Label1:Label2").
    """
    if not type_str or not isinstance(type_str, str):
        return f":{default_label}"
    
    # Split, strip whitespace, get unique, and sort for consistency
    labels = sorted(list({label.strip() for label in type_str.split(',') if label.strip()}))
    
    if not labels:
        return f":{default_label}"
    
    return ":" + ":".join(labels)

def networkx_to_neo4j_cypher(
    G: nx.Graph, 
    node_label: str = "Node", 
    relationship_type: str = "RELATES_TO"
) -> List[str]:
    """
    Converts a NetworkX graph to a list of Neo4j Cypher query strings.

    This function creates idempotent `MERGE` queries. It assumes that each node
    in the graph has a unique identifier that is also its key in the graph object.
    Node labels are derived from a 'type' attribute if it exists.

    Args:
        G: The input NetworkX graph.
        node_label: Default label for nodes if a 'type' attribute is not present.
        relationship_type: Default type for relationships.

    Returns:
        A list of Cypher query strings for creating the graph in Neo4j.
    """
    cypher_queries = []

    # --- 1. Generate Constraint Queries ---
    # This step is crucial for good performance with MERGE.
    all_labels = {node_label}
    for _, data in G.nodes(data=True):
        type_str = data.get('type')
        if type_str and isinstance(type_str, str):
            labels = {label.strip() for label in type_str.split(',') if label.strip()}
            all_labels.update(labels)
            
    cypher_queries.append("// --- 1. Create constraints for node uniqueness (run this part once) ---")
    for label in sorted(list(all_labels)):
        # Note: Neo4j requires constraints to be on a single label.
        cypher_queries.append(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE;")
    cypher_queries.append("")

    # --- 2. Generate Node Creation Queries ---
    cypher_queries.append("// --- 2. Create nodes ---")
    for node_id, data in G.nodes(data=True):
        node_id_json = json.dumps(node_id, ensure_ascii=False)
        labels = _format_labels(data.get('type'), node_label)
        props_str = _format_properties(data)
        
        # Use node_id as the unique 'id' property for merging
        query = f"MERGE (n{labels} {{id: {node_id_json}}})"
        if props_str:
            query += f" SET n += {props_str}"
        query += ";"
        cypher_queries.append(query)
    cypher_queries.append("")

    # --- 3. Generate Relationship Creation Queries ---
    cypher_queries.append("// --- 3. Create relationships ---")
    for source_id, target_id, data in G.edges(data=True):
        source_id_json = json.dumps(source_id, ensure_ascii=False)
        target_id_json = json.dumps(target_id, ensure_ascii=False)
        
        # We must look up the labels for the source and target nodes to create an efficient MATCH
        source_labels = _format_labels(G.nodes[source_id].get('type'), node_label)
        target_labels = _format_labels(G.nodes[target_id].get('type'), node_label)
        
        props_str = _format_properties(data)
        
        query = (
            f"MATCH (a{source_labels} {{id: {source_id_json}}}), (b{target_labels} {{id: {target_id_json}}})\n"
            f"MERGE (a)-[r:{relationship_type}]->(b)"
        )
        if props_str:
            query += f" SET r += {props_str}"
        query += ";"
        cypher_queries.append(query)
        
    return cypher_queries

def save_cypher_script(file_path: str, cypher_queries: List[str]):
    """
    Saves a list of Cypher queries to a file.

    Args:
        file_path: The path to the file where the script will be saved.
        cypher_queries: A list of strings, where each string is a Cypher query.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(cypher_queries))
        print(f"\n--- Cypher script successfully saved to {file_path} ---")
    except IOError as e:
        print(f"Error: Could not write to file {file_path}. Reason: {e}")


if __name__ == '__main__':
    doc_name = "AAAI2024"
    # Load netx graph from the relative path storage/Bodhi/{doc_name}/{doc_name}_graph.yml
    # This yml file is generated through node_link_data() api from netx. Hence loading it back to netx should be straight forward
    # Bodhi/tests/storage_backup/storage/Bodhi/AAAI2024_300_tokens
    graph_path = os.path.join("storage_backup","storage", "Bodhi", f"{doc_name}_300_tokens", f"{doc_name}_graph.yml")
    with open(graph_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    G = json_graph.node_link_graph(data)

    cypher_path = os.path.join("storage_backup","storage", "Bodhi", f"{doc_name}_300_tokens",f"{doc_name}_graph.cypher")

    # --- Convert the graph to a Cypher script ---
    cypher_script_lines = networkx_to_neo4j_cypher(
        G, 
        node_label="Entity", 
        relationship_type="RELATED_TO"
    )

    # --- Print the generated script ---
    print("--- Generated Cypher Script for Neo4j ---")
    print("\n".join(cypher_script_lines))

    # --- Save the script to a file using the new function ---
    save_cypher_script(cypher_path, cypher_script_lines)

# Test code 1 
if __name__ == '__main__1':
    # --- Create a sample NetworkX Graph based on the provided example ---
    G = nx.DiGraph() # Use DiGraph for directed relationships

    G.add_node(
        "HIGH-THROUGHPUT SCREENING (HTS)", 
        type='METHOD', 
        description='A traditional experimental approach for identifying molecules...',
        source_index=[0]
    )
    G.add_node(
        "GXVAES",
        type='METHOD, METHOD, METHOD', # Example of a messy type string
        description="A novel deep generative model for computer-aided drug discovery...",
        source_index=[0, 1, 2]
    )
    G.add_node(
        "COMPUTER-AIDED DRUG DISCOVERY",
        type='FIELD',
        description='The use of computational methods in drug design and development.'
    )
    G.add_node(
        "HIT-LIKE MOLECULES",
        type='CONCEPT',
        description='Molecules identified in a screen that show potential bioactivity.'
    )

    # Add edges with properties
    G.add_edge(
        "GXVAES", 
        "COMPUTER-AIDED DRUG DISCOVERY",
        weight=9.25,
        description='GxVAEs is a novel deep generative model for computer-aided drug discovery.'
    )
    G.add_edge(
        "GXVAES",
        "HIT-LIKE MOLECULES",
        weight=16.5,
        description="GxVAEs generates hit-like molecules that show potential bioactivity and drug-likeness."
    )
    
    # --- Convert the graph to a Cypher script ---
    cypher_script_lines = networkx_to_neo4j_cypher(
        G, 
        node_label="Entity", 
        relationship_type="RELATED_TO"
    )

    # --- Print the generated script ---
    print("--- Generated Cypher Script for Neo4j ---")
    print("\n".join(cypher_script_lines))

    # --- Save the script to a file using the new function ---
    output_filename = "import_graph.cypher"
    save_cypher_script(output_filename, cypher_script_lines)

