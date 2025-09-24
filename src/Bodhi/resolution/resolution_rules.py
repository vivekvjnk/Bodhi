import re,logging,csv, numpy as np
from collections import defaultdict

from ..utils import create_unique_trace_id

from .rule_based_resolution import ResolutionRule, MERGE, NO_MATCH, DEFER

OBSERVABILITY = 1

logger = logging.getLogger(__name__)

class UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))
    
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x, y):
        self.parent[self.find(x)] = self.find(y)

def deduplicate_lists(list1, list2, mask):
    """
    Deduplicate two list of strings using unionfind 
    mask should point to the indices list which should be deduplicated
    """
    n = len(list1)
    m = len(list2)
    total = n + m
    uf = UnionFind(total)

    # Step 1: Merge duplicates based on mask
    for i in range(n):
        for j in range(m):
            if mask[i][j]:
                uf.union(i, n + j)  # i from list1, j from list2

    # Step 2: Build final representative map
    index_to_string = {i: s for i, s in enumerate(list1 + list2)}
    rep_to_strings = {}
    
    # TODO : retain longest descriptions. 
    #        ie the parent of each union should be longest string in the union
    for i in range(total):
        rep = uf.find(i)
        if rep not in rep_to_strings:
            rep_to_strings[rep] = index_to_string[i]

    # Step 3: Return deduplicated values
    return list(rep_to_strings.values())


def find_names_differing_only_by_numbers(names):
    """
    Finds groups of names from a list that differ only by numbers.

    Args:
        names: A list of strings (names).

    Returns:
        A list of lists, where each inner list contains names that
        differ only by numbers.
    """
    
    # A helper function to strip numbers and whitespace
    def strip_numbers(s):
        return re.sub(r'\d+', '', s).strip()

    # Use a dictionary to group names by their stripped form
    groups = defaultdict(list)
    for name in names:
        stripped_name = strip_numbers(name)
        groups[stripped_name].append(name)
    
    # Filter for groups that have more than one element
    # and have at least two distinct names
    result_groups = []
    for group_list in groups.values():
        if len(group_list) > 1 and len(set(group_list)) > 1:
            result_groups.append(group_list)    
    return result_groups


def differ_only_by_numbers(name1, name2):
    """Helper function to check if strings differ only by numbers."""
    def strip_numbers(s):
        return re.sub(r'\d+', '', s).strip()
    return strip_numbers(name1) == strip_numbers(name2) and name1 != name2


# --- REFINED RULES ---
# Rule 1: A "Veto" rule that defers if names differ only by numbers
class DifferByNumberRule(ResolutionRule):
    def __init__(self, name_field='name'):
        """
        Configures the rule with the field to check for numeric differences.
        """
        self.name_field = name_field
    def evaluate(self,entities,**kwargs):
        decision = MERGE
        entity_names = list(entities.keys())
        entities_differring_by_number = find_names_differing_only_by_numbers(entity_names)
        if entities_differring_by_number:
            decision = DEFER    
        return {"decision":decision,"similar_entities":entities_differring_by_number}
    

# Rule 2: A rule for high-confidence merges based on name and description
class NameAndDescriptionRule(ResolutionRule):
    def __init__(self, name_field='name', desc_field='description', name_threshold=0.9, desc_threshold=0.85,source_name=None):
        """
        Configures the rule with fields for name and description, and their thresholds.
        """
        self.name_field = name_field
        self.desc_field = desc_field
        self.name_threshold = name_threshold
        self.desc_threshold = desc_threshold
        self.source_name = source_name
    
    def evaluate_old(self,entities,**kwargs):

        entity_name_list = list(entities.keys())
        
        # TODO: Full description similarity calculation will be done in later stage, version 2 
        # entity_desc_list = [data.get("description") for data in entities.values()]
        # flattened_entity_desc_list = list(itertools.chain.from_iterable(entity_desc_list))
        
        logger.info(f"Entity name list:\n{"*"*30}\n{entity_name_list[:4]}...\nNumber of elements: {len(entity_name_list)}")
        

        similarity_model = kwargs.get("similarity_model",None)
        # temp backup logic 
        # if os.path.exists("name_tensor.pt"):
        #     logger.info("loading from file")
        #     entity_name_semantic_distances = torch.load("name_tensor.pt") 
        #     torch.save(entity_name_semantic_distances,"name_tensors.pt")
        # else:
        #     logger.info("loading from memory")
        entity_name_semantic_distances = similarity_model.batch_to_batch_semantic_similarity(entity_name_list,entity_name_list)
        
            
        # Get upper triangle indices (excluding diagonal)
        i_indices, j_indices = np.triu_indices(entity_name_semantic_distances.shape[0], k=1)
         
        # i/j_indices represent upper triangular elements of entity name distances in coo format
        # name mask represent indices of i/j_indices for which semantic similarity is above a threshold
        # name_mask_coo_i/j_indices represent indices of filtered similar entities in coo format 
        # Filter based on threshold
        name_mask = entity_name_semantic_distances[i_indices, j_indices] > self.name_threshold
        original_positions = np.where(name_mask)[0]

        name_mask_coo_i_indices = i_indices[name_mask]
        name_mask_coo_j_indices = j_indices[name_mask]

        new_name_mask_coo_i_indices = np.array([])
        new_name_mask_coo_j_indices = np.array([])
        
        # Remove all matches which differ by just numbers 
        for i in range(len(name_mask_coo_i_indices)):
            if differ_only_by_numbers(entity_name_list[name_mask_coo_i_indices[i]],entity_name_list[name_mask_coo_j_indices[i]]):
                continue
            new_name_mask_coo_i_indices = np.append(new_name_mask_coo_i_indices, name_mask_coo_i_indices[i])
            new_name_mask_coo_j_indices = np.append(new_name_mask_coo_j_indices, name_mask_coo_j_indices[i])

        
    
        survivors = np.isin(name_mask_coo_i_indices,new_name_mask_coo_i_indices)
        
        new_name_mask = np.zeros_like(name_mask,dtype=bool)
        new_name_mask[original_positions[survivors]]= True
        
        # Extract (i, j, score) for matches
        similar_name_pairs = [
            (entity_name_list[i],int(i),entity_name_list[j], int(j), float(entity_name_semantic_distances[i, j]))
            for i, j in zip(i_indices[new_name_mask], j_indices[new_name_mask])
        ]
        if OBSERVABILITY:
            uid = create_unique_trace_id()[:5]
            extension = self.source_name[:5] if self.source_name is not None else uid
            log_path = kwargs.get("log_path",f"Bodhi/logs/name_rsln_log_{extension}.csv")
            # Write all pairwise similarities to CSV
            with open(log_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["entity_1_name", "entity_1_index", "entity_2_name", "entity_2_index", "similarity_score"])

                for row in similar_name_pairs:
                    writer.writerow(list(row))
                
        resolved_entities = {}
        resolved_keys = []

        no_resolved_descs = 0 
        no_extracted_descs = 0 
        similar_nodes = {}
        # calculate semantic similarities of descriptions of entities in similar_name_pairs
        for (entity1,_,entity2,_,_) in similar_name_pairs:
            # build a map 
            similar_nodes[entity1] = entity2
            try:
                descriptions_pair = [entities.get(entity1).get("description"),entities.get(entity2).get("description")]
            except Exception as e:
                logger.error(f"Error:{e}\n-----------\n entity1:{entity1}, content:{entities.get(entity1)}, entity2:{entity2}, content:{entities.get(entity2)}")
                raise e
            
            description_distances = similarity_model.batch_to_batch_semantic_similarity(descriptions_pair[0],descriptions_pair[1])
            
            desc_mask = description_distances > self.desc_threshold
            
            desc_mask_coo_i_indices, desc_mask_coo_j_indices = np.nonzero(desc_mask)
            
            # TODO : implement differ_only_by_numbers() for descriptions also
            #  - We don't do it now, because few more similar patterns were observed in entity deduplication.
            #  - Lets process few more domain specific content. Then we try to generalize outliers.
            #    - Semantic similarity models fail to differentiate equations 
            #  - Implementing simple numeric rules seem like an immature step

            deduplicated_descriptions = deduplicate_lists(descriptions_pair[0],descriptions_pair[1],desc_mask)
            resolved_types = list(set(entities.get(entity1).get("type") + entities.get(entity2).get("type")))
            resolved_sources = list(set(entities.get(entity1).get("source_chunk_index") + entities.get(entity2).get("source_chunk_index")))

            # create entity with entity1 name and deduplicated_descriptions
            resolved_entities[entity1] = {"description":deduplicated_descriptions,"type":resolved_types,"source_chunk_index":resolved_sources}

            resolved_keys.append(entity1)
            resolved_keys.append(entity2)

            if OBSERVABILITY:
                if desc_mask.any():
                    extension = self.source_name[:5] if self.source_name is not None else uid
                    log_path = kwargs.get("log_path",f"Bodhi/logs/desc_rsln_log_{extension}.csv")
                    similar_desc_pairs = [
                        (descriptions_pair[0][i],int(i),descriptions_pair[1][j], int(j), float(description_distances[i, j]))
                        for i, j in zip(desc_mask_coo_i_indices, desc_mask_coo_j_indices)
                    ]
                    with open(log_path, mode='a+', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow([f"Nodes: {entity1}<==>{entity2}"])
                        for item in similar_desc_pairs:
                            writer.writerow(item)

                no_resolved_descs += len(np.nonzero(desc_mask)[0])
                no_extracted_descs += (len(descriptions_pair[0]) + len(descriptions_pair[1]))
            

        resolved_nodes = {key:entities[key] for key in entities if key not in resolved_keys}
        resolved_nodes = resolved_nodes | resolved_entities
        

        # logger.info(f"name_mask({len(np.nonzero(name_mask)[0])}): {np.nonzero(name_mask)[:10]}")
        # logger.info(f"name mask indices({len(name_mask_coo_i_indices)}): {name_mask_coo_i_indices[:4]}\n{name_mask_coo_j_indices[:4]}")
        # logger.info(f"new_name_mask_coo_i_indices({len(new_name_mask_coo_i_indices)}): {new_name_mask_coo_i_indices[:10]}")
        
        # logger.info(f"i_indices({len(i_indices)}): {i_indices[:5]}")
        # logger.info(f"original positions({len(original_positions)}): {original_positions[:10]}")
        # logger.info(f"survivors({len(np.nonzero(survivors)[0])}): {np.nonzero(survivors)[0][:10]}")

        # logger.info(f"old mask indices({len(np.nonzero(name_mask)[0])}): {np.nonzero(name_mask)[0][:10]}")

        # logger.info(f"new mask indices({len(np.nonzero(new_name_mask)[0])}): {np.nonzero(new_name_mask)[0][:10]}")

        
        
        logger.info(f"NameAndDescriptionRule Resolution Metrics \n{"*"*30}\n - Total number of entities before resolution: {len(list(entities.keys()))}\n - Total number of entities after resolution: {len(list(resolved_nodes.keys()))}\n - Total number of descriptions in all resolved nodes before resolution: {no_extracted_descs}\n - Total number of descriptions in all resolved nodes after resolution: {no_extracted_descs-no_resolved_descs}\n{"*"*30}\n")
       
        decision = MERGE if any(new_name_mask) else NO_MATCH

        result = {"decision":decision,"similar_names":similar_nodes,"resolved_nodes":resolved_nodes}
        return result

    def evaluate(self, entities, **kwargs):
        """
        Main evaluation method that performs name and description resolution on entities.
        """
        entity_name_list = list(entities.keys())
        logger.info(f"Entity name list:\n{'*'*30}\n{entity_name_list[:4]}...\nNumber of elements: {len(entity_name_list)}")

        similarity_model = kwargs.get("similarity_model", None)
        uid = create_unique_trace_id()[:5] if OBSERVABILITY else None
        extension = self.source_name[:10] if self.source_name is not None else uid
        log_path = kwargs.get("log_path", f"storage/Bodhi/name_resolution_{extension}.csv") if OBSERVABILITY else None

        # Step 1: Name Resolution
        similar_name_pairs, new_name_mask, similar_nodes = resolve_names(
                                                                        numeric_filter_func=differ_only_by_numbers,
                                                                        string_list=entity_name_list,
                                                                        similarity_model=similarity_model,
                                                                        name_threshold=self.name_threshold,
                                                                        )

        if OBSERVABILITY:
            with open(log_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["entity_1_name", "entity_1_index", "entity_2_name", "entity_2_index", "similarity_score"])
                for row in similar_name_pairs:
                    writer.writerow(list(row))

        # Step 2: Description Resolution
        resolved_entities, resolved_keys, (no_resolved_descs, no_extracted_descs) = \
            self._resolve_descriptions(similar_name_pairs, entities, similarity_model, extension, log_path)

        resolved_nodes = {key: entities[key] for key in entities if key not in resolved_keys}
        resolved_nodes.update(resolved_entities)

        logger.info(f"NameAndDescriptionRule Resolution Metrics --- {self.source_name} \n{'*'*30}\n"
                    f" - Total number of entities before resolution: {len(entities)}\n"
                    f" - Total number of entities after resolution: {len(resolved_nodes)}\n"
                    f" - Total number of descriptions in all resolved nodes before resolution: {no_extracted_descs}\n"
                    f" - Total number of descriptions in all resolved nodes after resolution: {no_extracted_descs - no_resolved_descs}\n"
                    f"{'*'*30}\n")

        decision = MERGE if any(new_name_mask) else NO_MATCH
        return {"decision": decision, "similar_names": similar_nodes, "resolved_nodes": resolved_nodes}

    def _resolve_descriptions(self, similar_name_pairs, entities, similarity_model, uid=None, log_path=None):
        """
        Resolves entity descriptions for pairs of entities found in name resolution.
        Returns:
            resolved_entities: dict with merged entity data
            resolved_keys: list of merged entity keys
            metrics: (no_resolved_descs, no_extracted_descs)
        """
        resolved_entities = {}
        resolved_keys = []
        no_resolved_descs = 0
        no_extracted_descs = 0

        for (entity1, _, entity2, _, _) in similar_name_pairs:
            descriptions_pair = [
                entities.get(entity1).get("description"),
                entities.get(entity2).get("description")
            ]

            description_distances = similarity_model.batch_to_batch_semantic_similarity(
                descriptions_pair[0], descriptions_pair[1]
            )

            desc_mask = description_distances > self.desc_threshold
            desc_mask_coo_i_indices, desc_mask_coo_j_indices = np.nonzero(desc_mask)

            deduplicated_descriptions = deduplicate_lists(
                descriptions_pair[0], descriptions_pair[1], desc_mask
            )

            resolved_types = list(set(entities.get(entity1).get("type") + entities.get(entity2).get("type")))
            resolved_sources = list(set(entities.get(entity1).get("source_chunk_index") +
                                        entities.get(entity2).get("source_chunk_index")))

            resolved_entities[entity1] = {
                "description": deduplicated_descriptions,
                "type": resolved_types,
                "source_chunk_index": resolved_sources
            }

            resolved_keys.extend([entity1, entity2])

            no_resolved_descs += len(np.nonzero(desc_mask)[0])
            no_extracted_descs += len(descriptions_pair[0]) + len(descriptions_pair[1])

            if OBSERVABILITY and desc_mask.any():
                desc_log_path = log_path or f"Bodhi/logs/desc_resolution_{uid}.csv"
                similar_desc_pairs = [
                    (descriptions_pair[0][i], int(i), descriptions_pair[1][j], int(j),
                    float(description_distances[i, j]))
                    for i, j in zip(desc_mask_coo_i_indices, desc_mask_coo_j_indices)
                ]
                with open(desc_log_path, mode='a+', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([f"Nodes: {entity1}<==>{entity2}"])
                    for item in similar_desc_pairs:
                        writer.writerow(item)

        return resolved_entities, resolved_keys, (no_resolved_descs, no_extracted_descs)


def resolve_names(
    string_list,
    similarity_model,
    name_threshold=0.9,
    numeric_filter_func=None
):
    """
    Resolves name similarities based on semantic similarity and optional numeric filtering.

    Args:
        string_list (list[str]): The list of strings to compare.
        similarity_model: Model with batch_to_batch_semantic_similarity method.
        name_threshold (float): Similarity threshold.
        numeric_filter_func (callable): Optional func(str1, str2) -> bool
                                        Returns True if pair should be excluded.

    Returns:
        similar_pairs (list[tuple]): (str1, idx1, str2, idx2, similarity_score)
        new_mask (np.ndarray[bool]): Mask for selected upper-triangle elements.
        similar_nodes (dict): Mapping str1 -> str2 for matched names.
    """
    print("Starting resolve_names...")
    distances = similarity_model.batch_to_batch_semantic_similarity(
        string_list, string_list
    )
    print(f"Distances shape: {distances.shape}")

    i_indices, j_indices = np.triu_indices(distances.shape[0], k=1)
    print(f"Upper triangle indices: i_indices({len(i_indices)}), j_indices({len(j_indices)})")

    name_mask = distances[i_indices, j_indices] > name_threshold
    print(f"Name mask (threshold {name_threshold}): {np.sum(name_mask)} matches found")

    original_positions = np.where(name_mask)[0]
    print(f"Original positions of matches: {original_positions}")

    name_mask_coo_i = i_indices[name_mask]
    name_mask_coo_j = j_indices[name_mask]
    print(f"Filtered indices: name_mask_coo_i({len(name_mask_coo_i)}), name_mask_coo_j({len(name_mask_coo_j)})")

    new_i_indices = np.array([])
    new_j_indices = np.array([])

    for i in range(len(name_mask_coo_i)):
        str1, str2 = string_list[name_mask_coo_i[i]], string_list[name_mask_coo_j[i]]
        if numeric_filter_func and numeric_filter_func(str1, str2):
            print(f"Excluding pair due to numeric filter: {str1}, {str2}")
            continue
        new_i_indices = np.append(new_i_indices, name_mask_coo_i[i])
        new_j_indices = np.append(new_j_indices, name_mask_coo_j[i])

    print(f"Survivor indices after numeric filter: {len(new_i_indices)}")

    survivors = np.isin(name_mask_coo_i, new_i_indices)
    new_mask = np.zeros_like(name_mask, dtype=bool)
    new_mask[original_positions[survivors]] = True

    similar_pairs = [
        (string_list[i], int(i), string_list[j], int(j), float(distances[i, j]))
        for i, j in zip(i_indices[new_mask], j_indices[new_mask])
    ]
    print(f"Similar pairs found: {len(similar_pairs)}")

    similar_nodes = {pair[2]: pair[0] for pair in similar_pairs}
    print(f"Similar nodes mapping size: {len(similar_nodes)}")

    print("resolve_names completed.")
    return similar_pairs, new_mask, similar_nodes
