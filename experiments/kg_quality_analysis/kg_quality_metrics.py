"""kg_quality_metrics.py
A lightweight, dependency-minimal toolkit for computing quantitative quality metrics
for Knowledge Graphs (KGs) extracted from documents (e.g., via Bodhi).

Usage:
    from kg_quality_metrics import compute_all_metrics, composite_score

    metrics = compute_all_metrics(G,
                                  node_type_attr="type",
                                  node_name_attr="name",
                                  edge_type_attr="relation",
                                  allowed_relations=None,   # optional {(head_type, relation, tail_type)}
                                  evidence_attr="evidence", # edge attribute that holds a list or count
                                  embedding_attr=None,      # optional node/edge embedding key
                                  modality_attr="modality"  # optional node modality key
                                 )
    score = composite_score(metrics)

Notes:
  - Designed to work with networkx.Graph or networkx.DiGraph.
  - All metrics are defensive: if a signal is missing (e.g., no evidence attr), the metric
    is skipped with None and automatically excluded from scoring.
  - You can adjust weights in composite_score() to match project priorities.
"""

from __future__ import annotations
import math
from statistics import mean
from typing import Dict, Any, Iterable, Optional, Set, Tuple, List
import networkx as nx
import csv
from pathlib import Path
import yaml
# ------------------------
# Utility helpers
# ------------------------

def _save_metrics_to_csv(data_list, filename="graph_metrics.csv"):
    """
    Saves a list of dictionaries to a CSV file, preserving key order.

    Args:
        data_list (list): A list of dictionaries, where each dictionary
                          represents a row of data.
        filename (str): The name of the CSV file to save the data to.
    """
    # Check if the list of dictionaries is empty.
    if not data_list:
        print("The list is empty. No data to save.")
        return

    # Extract the header from the keys of the first dictionary.
    # The DictWriter class uses this list to define the column order.
    # We explicitly convert to a list to ensure the order is maintained.
    headers = list(data_list[0].keys())

    try:
        # Open the file in write mode ('w').
        # The 'newline=""' argument is crucial to prevent blank rows.
        with open(filename, 'w', newline='') as csvfile:
            # Create a DictWriter object with explicit fieldnames.
            writer = csv.DictWriter(csvfile, fieldnames=headers)

            # Write the header row to the file.
            writer.writeheader()

            # Iterate through the list of dictionaries and write each
            # dictionary as a row.
            for row_dict in data_list:
                writer.writerow(row_dict)

        print(f"Successfully saved {len(data_list)} rows to '{filename}'.")

    except IOError as e:
        print(f"I/O error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default

def _gini(values: Iterable[float]) -> float:
    vals = sorted([v for v in values if v is not None and v >= 0])
    n = len(vals)
    if n == 0:
        return 0.0
    cumvals = [sum(vals[:i+1]) for i in range(n)]
    total = cumvals[-1]
    if total == 0:
        return 0.0
    # Gini using Lorenz curve discretization
    g = 1 + (1/n) - 2 * sum((cumvals[i] / total) * ((n - i) / n) for i in range(n))
    return max(0.0, min(1.0, g))

def _entropy(counts: Iterable[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log2(p)
    return ent

def _normalize_name(s: str) -> str:
    return ''.join(ch for ch in (s or "").lower() if ch.isalnum())

# ------------------------
# Topology metrics
# ------------------------
def topology_metrics(G: nx.Graph) -> Dict[str, Any]:
    """
    Compute key topology metrics for a Knowledge Graph (KG).

    This function applies network science measures to evaluate the structure, 
    connectivity, and navigability of a KG. The metrics provide insights into 
    how well the graph supports knowledge integration, retrieval, and reasoning.

    Parameters
    ----------
    G : nx.Graph or nx.DiGraph
        The input Knowledge Graph, where nodes represent entities and 
        edges represent relationships.

    Returns
    -------
    Dict[str, Any]
        A dictionary of graph metrics:

        - n_nodes : int
            Number of entities in the KG.
        - n_edges : int
            Number of relationships in the KG.
        - density : float
            Fraction of possible edges that exist. Indicates graph connectivity; 
            very high values may suggest spurious links.
        - avg_degree : float
            Average number of relationships per entity. Reflects relational richness.
        - degree_gini : float
            Inequality in degree distribution. High values indicate hub-dominated structure.
        - degree_entropy : float
            Diversity of node connectivity. Higher values mean richer structural variation.
        - n_components : int
            Number of disconnected subgraphs. Indicates fragmentation of the KG.
        - giant_cc_ratio : float
            Proportion of nodes in the largest connected component. 
            Higher values = more globally navigable knowledge.
        - avg_shortest_path_gcc : float or None
            Average shortest path length within the giant component. 
            Lower values = easier reasoning and traversal.
        - diameter_gcc : int or None
            Longest shortest path in the giant component. Reflects depth of knowledge space.
        - avg_clustering : float or None
            Average clustering coefficient. Measures tendency to form local semantic clusters.
        - assortativity : float or None
            Degree correlation between connected nodes. Positive = hub-to-hub,
            negative = hub-to-spoke (hierarchical).
        - modularity : float or None
            Strength of domain/community separation. Higher values = well-defined domains.
        - n_communities : int or None
            Number of detected communities (approximate domain count).

    Notes
    -----
    - Most real-world KGs are sparse (low density).
    - A healthy KG typically has a large giant component, moderate clustering,
      and meaningful community structure.
    - These metrics are useful for evaluating KG growth, structural health,
      and retrieval efficiency.
    """
    n = G.number_of_nodes()   # Number of entities in the KG (scale of knowledge)
    m = G.number_of_edges()   # Number of relationships in the KG

    # Ensure undirected view for metrics that require it
    undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G

    density = nx.density(undirected)  
    # Density → how interconnected the KG is.
    # Sparse is normal; too high may mean over-linking (spurious edges).

    degrees = [deg for _, deg in undirected.degree()]
    avg_degree = mean(degrees) if degrees else 0.0  
    # Avg degree → typical number of relationships per entity.
    # Reflects how relational the KG is; high values mean hubs dominate.

    degree_gini = _gini(degrees)  
    # Degree Gini → inequality in degree distribution.
    # High = few hubs dominate connections, risking retrieval bias.

    degree_entropy = _entropy(degrees)  
    # Degree entropy → diversity of node connectivity.
    # Higher entropy means richer structural variation.

    comps = list(nx.connected_components(undirected))
    num_components = len(comps)  
    # Number of connected components → fragmentation of KG.
    # More components = isolated knowledge “islands”.

    giant_cc_size = max((len(c) for c in comps), default=0)
    giant_cc_ratio = _safe_div(giant_cc_size, n, 0.0)  
    # Giant CC ratio → proportion of nodes in largest connected component.
    # Higher ratio = knowledge is more globally navigable.

    # Avg shortest path & diameter computed on the giant component
    aspl = None
    diameter = None
    if giant_cc_size >= 2:
        GCC = undirected.subgraph(max(comps, key=len)).copy()
        try:
            aspl = nx.average_shortest_path_length(GCC)  
            # Avg shortest path → reasoning efficiency.
            # Lower values = easier traversal between concepts.

            diameter = nx.diameter(GCC)  
            # Diameter → “size” of knowledge space in hops.
            # Large = deep hierarchies; small = flat, dense linking.
        except Exception:
            aspl = None
            diameter = None

    try:
        avg_clustering = nx.average_clustering(undirected)  
        # Clustering coefficient → tendency of neighbors to form semantic clusters.
        # High = well-formed local domains, too high may mean redundancy.
    except Exception:
        avg_clustering = None

    try:
        assortativity = nx.degree_assortativity_coefficient(undirected)  
        # Degree assortativity → hub-to-hub vs hub-to-spoke connections.
        # Positive = clustered hubs; negative = hierarchical (hub–spoke).
    except Exception:
        assortativity = None

    try:
        comms = list(nx.algorithms.community.greedy_modularity_communities(undirected))
        modularity = (
            nx.algorithms.community.quality.modularity(undirected, comms) if comms else None
        )  
        # Modularity → strength of domain/community separation.
        # High modularity = distinct domains (e.g., medicine vs physics).
        num_comms = len(comms)  
        # Number of detected communities → domain count estimate.
    except Exception:
        modularity = None
        num_comms = None

    return {
        "n_nodes": n,
        "n_edges": m,
        "density": density,
        "avg_degree": avg_degree,
        "degree_gini": degree_gini,
        "degree_entropy": degree_entropy,
        "n_components": num_components,
        "giant_cc_ratio": giant_cc_ratio,
        "avg_shortest_path_gcc": aspl,
        "diameter_gcc": diameter,
        "avg_clustering": avg_clustering,
        "assortativity": assortativity,
        "modularity": modularity,
        "n_communities": num_comms,
    }

# ------------------------
# Ontology adherence & typing metrics
# ------------------------
def ontology_metrics(G: nx.Graph,
                     node_type_attr: str = "type",
                     edge_type_attr: str = "relation",
                     allowed_relations: Optional[Set[Tuple[str, str, str]]] = None
                    ) -> Dict[str, Any]:
    n = G.number_of_nodes()
    m = G.number_of_edges()

    # Node typing coverage and conflicts
    types = []
    multi_type_conflicts = 0
    missing_type = 0
    type_counts = {}
    for node, data in G.nodes(data=True):
        t = data.get(node_type_attr).split(",") # node type is comma separated list in string format
        if t is None:
            missing_type += 1
        else:
            if isinstance(t, (list, tuple, set)):
                tset = set(t)
                types.append(next(iter(tset)))  # pick one for coarse stats
                if len(tset) > 1:
                    multi_type_conflicts += 1
                for ti in tset:
                    type_counts[ti] = type_counts.get(ti, 0) + 1
            else:
                types.append(t)
                type_counts[t] = type_counts.get(t, 0) + 1

    typing_coverage = _safe_div(n - missing_type, n, 1.0) if n else 1.0
    type_diversity_entropy = _entropy(type_counts.values())

    # Edge schema violations (if allowed_relations provided)
    schema_violations = None
    if allowed_relations is not None:
        violations = 0
        checked = 0
        for u, v, edata in G.edges(data=True):
            r = edata.get(edge_type_attr)
            tu = G.nodes[u].get(node_type_attr)
            tv = G.nodes[v].get(node_type_attr)
            if r is None or tu is None or tv is None:
                continue
            # normalize to single string types
            tu_set = {tu} if not isinstance(tu, (list, set, tuple)) else set(tu)
            tv_set = {tv} if not isinstance(tv, (list, set, tuple)) else set(tv)
            for t1 in tu_set:
                for t2 in tv_set:
                    checked += 1
                    if (t1, r, t2) not in allowed_relations:
                        violations += 1
        schema_violations = _safe_div(violations, checked, 0.0) if checked else 0.0

    return {
        "typing_coverage": typing_coverage,              # 0..1 (higher is better)
        "multi_type_conflict_rate": _safe_div(multi_type_conflicts, n, 0.0),
        "type_diversity_entropy": type_diversity_entropy,
        "edge_schema_violation_rate": schema_violations, # 0..1 (lower is better), or None
    }

# ------------------------
# Redundancy & normalization metrics
# ------------------------
def redundancy_metrics(G: nx.Graph, node_name_attr: str = "name") -> Dict[str, Any]:
    n = G.number_of_nodes()
    names = []
    for _, data in G.nodes(data=True):
        nm = data.get(node_name_attr) or data.get("label") or data.get("id")
        if isinstance(nm, str):
            names.append(_normalize_name(nm))
    norm_counts = {}
    for nm in names:
        norm_counts[nm] = norm_counts.get(nm, 0) + 1
    # duplicates => counts > 1 but ignore empty strings
    dup_total = sum(c-1 for k, c in norm_counts.items() if k and c > 1)
    redundancy_rate = _safe_div(dup_total, max(n,1), 0.0)
    unique_ratio = _safe_div(len([k for k in norm_counts if k]), max(n,1), 1.0)
    return {
        "redundancy_rate": redundancy_rate,  # 0..1 (lower is better)
        "unique_name_ratio": unique_ratio,   # 0..1 (higher is better)
    }

# ------------------------
# Evidence & provenance metrics
# ------------------------
def evidence_metrics(G: nx.Graph, evidence_attr: str = "evidence") -> Dict[str, Any]:
    m = G.number_of_edges()
    if m == 0:
        return {"edge_evidence_coverage": None, "avg_evidence_per_edge": None}
    covered = 0
    counts = []
    for _, _, edata in G.edges(data=True):
        ev = edata.get(evidence_attr)
        if ev is None:
            continue
        covered += 1
        if isinstance(ev, (list, tuple, set)):
            counts.append(len(ev))
        elif isinstance(ev, (int, float)):
            counts.append(float(ev))
        else:
            counts.append(1.0)
    edge_evidence_coverage = _safe_div(covered, m, 0.0)
    avg_evidence_per_edge = mean(counts) if counts else 0.0
    return {
        "edge_evidence_coverage": edge_evidence_coverage,  # 0..1 (higher is better)
        "avg_evidence_per_edge": avg_evidence_per_edge,    # unbounded
    }

# ------------------------
# Modality & community purity (optional)
# ------------------------
def modality_purity_metrics(G: nx.Graph, modality_attr: str = "modality") -> Dict[str, Any]:
    # Computes how "pure" communities are with respect to a node attribute (e.g., type or modality)
    undirected = G.to_undirected() if isinstance(G, nx.DiGraph) else G
    try:
        comms = list(nx.algorithms.community.greedy_modularity_communities(undirected))
    except Exception:
        return {"community_purity": None}
    if not comms:
        return {"community_purity": None}

    def impurity(nodes: Iterable) -> float:
        counts = {}
        total = 0
        for u in nodes:
            val = undirected.nodes[u].get(modality_attr)
            if val is None:
                continue
            counts[val] = counts.get(val, 0) + 1
            total += 1
        if total == 0:
            return 0.0
        # Gini impurity
        return 1.0 - sum((c/total)**2 for c in counts.values())

    impurities = [impurity(c) for c in comms]
    # purity = 1 - average impurity
    purity = 1.0 - mean(impurities) if impurities else None
    return {"community_purity": purity}  # 0..1 higher is better

# ------------------------
# Composite: gather + score
# ------------------------
def compute_all_metrics(G: nx.Graph,
                        node_type_attr: str = "type",
                        node_name_attr: str = "name",
                        edge_type_attr: str = "relation",
                        allowed_relations: Optional[Set[Tuple[str, str, str]]] = None,
                        evidence_attr: str = "evidence",
                        embedding_attr: Optional[str] = None,  # reserved
                        modality_attr: str = "modality") -> Dict[str, Any]:
    M = {}
    M.update(topology_metrics(G))
    M.update(ontology_metrics(G, node_type_attr=node_type_attr,
                                 edge_type_attr=edge_type_attr,
                                 allowed_relations=allowed_relations))
    M.update(redundancy_metrics(G, node_name_attr=node_name_attr))
    M.update(evidence_metrics(G, evidence_attr=evidence_attr))
    M.update(modality_purity_metrics(G, modality_attr=modality_attr))
    return M

def composite_score(metrics: Dict[str, Any],
                    weights: Optional[Dict[str, float]] = None) -> float:
    """Compute a 0..100 composite quality score.
    Missing metrics (None) are skipped and weights renormalized.
    Default weights reflect priorities for research-gap KGs.
    """
    # Default weights (sum to ~1); adjust to your needs
    default_weights = {
        # Topology
        "giant_cc_ratio":        0.10,
        "avg_clustering":        0.06,
        "modularity":            0.06,
        "assortativity":         0.02,
        "avg_shortest_path_gcc": 0.03,  # inverted
        # Ontology
        "typing_coverage":       0.14,
        "multi_type_conflict_rate": 0.06,  # inverted
        "edge_schema_violation_rate": 0.10, # inverted
        "type_diversity_entropy": 0.04,
        # Redundancy
        "redundancy_rate":       0.10,  # inverted
        "unique_name_ratio":     0.06,
        # Evidence
        "edge_evidence_coverage": 0.10,
        "avg_evidence_per_edge":  0.05,
        # Purity
        "community_purity":       0.08,
    }
    W = dict(default_weights)
    if weights:
        W.update(weights)

    # Normalization functions per metric (map to 0..1 where 1 is better)
    def nz(x): return 0.0 if x is None else x

    norm = {
        # Topology (reasonable bounds; tuned for document-scale KGs)
        "giant_cc_ratio":        lambda x: min(max(nz(x), 0.0), 1.0),
        "avg_clustering":        lambda x: min(max(nz(x), 0.0), 1.0),
        "modularity":            lambda x: min(max(nz(x), 0.0), 1.0),
        "assortativity":         lambda x: (nz(x)+1)/2 if x is not None else 0.5,  # map [-1,1] -> [0,1]
        "avg_shortest_path_gcc": lambda x: 1.0 / (1.0 + max(nz(x), 0.0)),  # lower path length is better
        # Ontology
        "typing_coverage":       lambda x: min(max(nz(x), 0.0), 1.0),
        "multi_type_conflict_rate": lambda x: 1.0 - min(max(nz(x), 0.0), 1.0),
        "edge_schema_violation_rate": lambda x: 1.0 - min(max(nz(x), 0.0), 1.0),
        "type_diversity_entropy": lambda x: min(max(nz(x) / 6.0, 0.0), 1.0),  # cap at ~6 bits
        # Redundancy
        "redundancy_rate":       lambda x: 1.0 - min(max(nz(x), 0.0), 1.0),
        "unique_name_ratio":     lambda x: min(max(nz(x), 0.0), 1.0),
        # Evidence
        "edge_evidence_coverage": lambda x: min(max(nz(x), 0.0), 1.0),
        "avg_evidence_per_edge":  lambda x: min(max(nz(x) / 5.0, 0.0), 1.0),  # saturate at ~5 cites/edge
        # Purity
        "community_purity":       lambda x: min(max(nz(x), 0.0), 1.0),
    }

    # Aggregate with weight renormalization over available signals
    used_weights = {}
    for k, w in W.items():
        if k in metrics and metrics[k] is not None and k in norm:
            used_weights[k] = w
    total_w = sum(used_weights.values()) or 1.0
    used_weights = {k: w/total_w for k, w in used_weights.items()}

    score01 = 0.0
    for k, w in used_weights.items():
        score01 += w * norm[k](metrics[k])

    return round(100.0 * score01, 2)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_statistical_graphs(csv_file_path, output_dir="graphs"):
    """
    Reads a CSV file, calculates statistical properties, and generates
    and saves various statistical graphs.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        df = pd.read_csv(csv_file_path)
        numeric_df = df.drop(columns=['source'])

        print("--- Generating descriptive statistics... ---")
        desc_stats = numeric_df.describe()
        print(desc_stats)

        # --- 1. Histograms for each numerical feature ---
        print("\n--- Generating histograms... ---")
        numeric_df.hist(figsize=(15, 12), bins=10, grid=False)
        plt.suptitle('Histograms of Numerical Features', fontsize=16)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(os.path.join(output_dir, "histograms.png"))
        plt.close()
        print("Histograms saved to histograms.png")
        
        # --- 2. Box plots for each numerical feature ---
        print("\n--- Generating box plots... ---")
        # Dynamically determine the grid size based on the number of columns
        num_cols = len(numeric_df.columns)
        ncols = 4  # A good number of columns for a plot grid
        nrows = (num_cols + ncols - 1) // ncols  # Calculate rows needed
        
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(18, 5 * nrows)) # Adjust figsize dynamically
        axes = axes.flatten()
        
        for i, col in enumerate(numeric_df.columns):
            sns.boxplot(x=numeric_df[col], ax=axes[i], color='skyblue')
            axes[i].set_title(col)
        
        # Hide any unused subplots
        for j in range(num_cols, len(axes)):
            axes[j].axis('off')

        plt.suptitle('Box Plots of Numerical Features', fontsize=16)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(os.path.join(output_dir, "box_plots.png"))
        plt.close()
        print("Box plots saved to box_plots.png")

        # --- 3. Pair plot (Scatter matrix) for key features ---
        print("\n--- Generating pair plot... ---")
        key_features = ['n_nodes', 'n_edges', 'density', 'avg_degree', 'avg_shortest_path_gcc']
        sns.pairplot(numeric_df[key_features])
        plt.suptitle('Pair Plot of Key Features', y=1.02, fontsize=16)
        plt.savefig(os.path.join(output_dir, "pair_plot.png"))
        plt.close()
        print("Pair plot saved to pair_plot.png")

        # --- 4. Correlation Heatmap ---
        print("\n--- Generating correlation heatmap... ---")
        corr_matrix = numeric_df.corr()
        plt.figure(figsize=(12, 10))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f")
        plt.title('Correlation Heatmap', fontsize=16)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "correlation_heatmap.png"))
        plt.close()
        print("Correlation heatmap saved to correlation_heatmap.png")

        return f"✅ Successfully generated statistical graphs and saved them to the '{output_dir}' directory."

    except FileNotFoundError:
        return f"❌ Error: The file at '{csv_file_path}' was not found. Please check the path."
    except Exception as e:
        return f"❌ An unexpected error occurred: {e}"

if __name__ == "__main__":

    def get_graphs_starting_with(directory, prefix=""):
        directory_path = Path(directory)
        graph_paths = [file for file in directory_path.glob(f"**/{prefix}*_graph.yml")]
        return graph_paths
    
    dir = "infra/storage/Bodhi"
    
    graph_paths = get_graphs_starting_with(directory=dir)
    print(graph_paths)
    
    # metrics = []
    # for graph_path in graph_paths:
    #     try:
    #         with open(graph_path.absolute(),"r") as f:
    #             serial_netx_graph = yaml.safe_load(stream=f)
    #             nx_graph = nx.node_link_graph(serial_netx_graph)
    #     except FileNotFoundError:
    #         print("File not found")
    #         continue
    #     graph_topology_metrics = {"source":Path(graph_path.name).stem}
    #     graph_topology_metrics.update(topology_metrics(G=nx_graph))
    #     metrics.append(graph_topology_metrics)
    
    # _save_metrics_to_csv(metrics)
    print(generate_statistical_graphs("graph_metrics.csv"))


if __name__ == "__main__1":
    # Minimal self-test on a tiny graph
    G = nx.Graph()
    G.add_node("a", type="Algorithm", name="A*")
    G.add_node("b", type="Tool", name="Toolkit-A")
    G.add_node("c", type="Dataset", name="Data Set")
    G.add_edge("a", "b", relation="implements", evidence=["p1", "p2"])
    G.add_edge("a", "c", relation="evaluated_on", evidence=[])
    
    allowed = {("Algorithm", "implements", "Tool"),
               ("Algorithm", "evaluated_on", "Dataset")}

    M = compute_all_metrics(G, allowed_relations=allowed)
    S = composite_score(M)
    print("METRICS:", M)
    print("SCORE:", S)
