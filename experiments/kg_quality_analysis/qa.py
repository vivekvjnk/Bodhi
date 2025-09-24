# Code to analyze quality of the generated knowledge graphs
import yaml
import networkx as nx
import itertools
# Step 1 : load the knowledge graph 
def load_graph(path):
    with open(path,"r") as f:
        graph = yaml.safe_load(f)

    print(f"graph : {graph}")
    G = nx.node_link_graph(graph)

    return {"dict":graph,"netx":G}

def main():
    # Find all outlier ontology
    # Load ontology
    ontology_path = "experiments/ontology_discovery/discovered_schemas/ai_agentics.yml"
    with open(ontology_path,"r") as f:
        ontology = yaml.safe_load(f)
    
    source ="2504.01990"
    source ="2503.22625"
    # Load graph 
    graph_path = f"infra/storage/Bodhi/{source}/{source}_graph.yml"
    graph = load_graph(path=graph_path)
    graph_dict = graph["dict"]
    g_node_type_list = []
    for item in graph_dict["nodes"]:
        # print(f"Identified type: {item["type"].split(",")}")
        g_node_type_list.extend(item["type"].split(","))

    g_node_type_list = [item.strip() for item in g_node_type_list]
    graph_node_types = set(g_node_type_list)
    
    ontology_entity_types = [item["name"].strip().upper() for item in ontology]
    ontology_entity_types = set(ontology_entity_types)

    # print(f"Graph node types: {graph_node_types}")
    print(f"Ontology entity types ({len(ontology_entity_types)}):{ontology_entity_types}")

    # new_types = [item for item in graph_node_types if item not in ontology_entity_types]
    new_types = graph_node_types - ontology_entity_types

    print(f"Graph node types ({len(graph_node_types)}):", graph_node_types)
    print(f"New types ({len(new_types)}):", new_types)

    counter = 0
    for item in graph_dict["nodes"]:
        types = item.get("type").split(",")
        if any(element in new_types for element in types):
            counter +=1
        
    print(f"Total number of nodes with new types: {counter} / {len(graph_dict["nodes"])}")

if __name__ == "__main__":
    main()