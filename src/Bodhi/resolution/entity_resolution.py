from ..utils import (
    SemanticSimilarity,
    harmonic_mean,
    tuple_constructor,
)
from .rule_based_resolution import MERGE, NO_MATCH
import re, yaml, tqdm, logging

yaml.add_constructor(
    "tag:yaml.org,2002:python/tuple", tuple_constructor, yaml.FullLoader
)

# --- Logger ---
logger = logging.getLogger(__name__)

# --- Utility functions ---
def differ_only_by_numbers(name1, name2):
    """
    Returns True if name1 and name2 differ only in numeric substrings.
    E.g. "ABC 1" vs "ABC 2" -> True; "ABC" vs "XYZ" -> False
    """

    def strip_numbers(s):
        return re.sub(r"\d+", "", s)

    return strip_numbers(name1) == strip_numbers(name2) and name1 != name2

def load_nodes_n_relns_from_intermediate_file(file_path):
    """
    Loads entities and relationships from a YAML file into separate dictionaries.
    Why do we convert entity and relationship dictionaries into different format?
        During deduplication, content of each entity and relationship element can
        have multiple values for a single key.
        For example, an entity can have multiple types, descriptions, and source_chunk_indices.
        Hence, we convert the entity and relationship dictionaries into a format where each key
        maps to a list of values. This allows us to handle multiple values for a single key
        without losing any information during deduplication.
    """

    try:
        with open(file_path) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)

        if data is None:
            logger.info(f"Warning: File {file_path} is empty. Returning empty dictionaries.")
            return {}, {}

        if (
            not isinstance(data, dict)
            or "entities" not in data
            or "relationships" not in data
        ):
            logger.info(
                f"Warning: File {file_path} does not contain expected 'entities' and 'relationships' structure. Returning empty dictionaries."
            )
            return {}, {}

        entities_dict = {}
        relationships_dict = {}

        # First level of deduplication. 
        # By making entity names as keys, we ensure that entities with the same name
        # are merged together. This is a simple deduplication based on names.
        for entity in data["entities"]:
            name = entity["name"].lower()
            entities_dict.setdefault(
                name, {"type": [], "description": [], "source_chunk_index": []}
            )
            entities_dict[name]["type"].append(
                entity.get("type")
            )  # Use get to avoid keyerror
            entities_dict[name]["description"].append(entity.get("description"))
            entities_dict[name]["source_chunk_index"].append(
                entity.get("source_chunk_index", 0)
            )  # Default to 0 if not present
        
        # By making relationship tuple keys, we ensure that links with the same source and target
        # are merged together. This is a simple deduplication based on source and target names.
        for relationship in data["relationships"]:
            source = relationship["source_entity"]
            target = relationship["target_entity"]
            key = (source, target)
            relationships_dict.setdefault(
                key, {"description": [], "strength": [], "source_chunk_index": []}
            )
            relationships_dict[key]["description"].append(
                relationship.get("description")
            )
            relationships_dict[key]["strength"].append(relationship.get("strength"))
            relationships_dict[key]["source_chunk_index"].append(
                relationship.get("source_chunk_index", 0)
            )  # Default to 0 if not present
        return entities_dict, relationships_dict

    except FileNotFoundError:
        logger.info(f"File not found: {file_path}. Returning empty dictionaries.")
        return {}, {}
    except yaml.YAMLError as e:
        logger.info(f"YAML parsing error: {e}. Returning None, None.")
        return None, None
    except Exception as e:
        logger.info(f"An unexpected error occurred: {e}. Returning None, None.")
        return None, None
# --- Utility functions ---



# ---------------Method for updating deduplicated relationships-Begin-------------#
def link_resolution(relationships, node_resolution_map, similarity_threshold=0.8):
    """
    Updates relationships based on deduplications made on entities and tracks changes.

    Args:
        relationships (dict): Dictionary containing relationships in the format:
            { (source, destination): {"description": [...], "strength": [...]}}
        node_resolution_map (dict): Map of deduplicated entities in the format:
            { original_entity: deduplicated_entity }
        similarity_threshold (float): Threshold for semantic similarity of descriptions (default=0.8).

    Returns:
        tuple: (updated_relationships, relationship_updates)
            - updated_relationships (dict): Updated relationships with deduplicated entities.
            - relationship_updates (dict): Map of original relationships to their updated relationships.
    """
    updated_relationships = {}
    relationship_updates = {}
    # model_path = "experiments/fine_tuned_scada_model"
    model_path = "all-mpnet-base-v2"
    similarity_checker = SemanticSimilarity(model_path=model_path)

    logger.info(f"Starting batch relationship resolution...\n")
    for (source, destination), rel_data in tqdm.tqdm(relationships.items()):
        # Check if source or destination has been deduplicated
        updated_source = node_resolution_map.get(source, source)
        updated_destination = node_resolution_map.get(destination, destination)

        # What if updated source&destination and original source&destination are same?

        # Define the updated relationship key
        updated_key = (updated_source, updated_destination)
        original_key = (source, destination)

        # Track the relationship update
        if original_key != updated_key:  # Only for tracking purpose
            relationship_updates[original_key] = updated_key

        # Merge data if the relationship already exists with the updated key
        if updated_key in updated_relationships:
            existing_data = updated_relationships[updated_key]

            # Merge descriptions using semantic similarity
            for new_desc in rel_data["description"]:
                if not any(
                    [
                        similarity_checker.compute_similarity(new_desc, existing_desc)
                        >= similarity_threshold
                    ]
                    for existing_desc in existing_data["description"]
                ):
                    existing_data["description"].append(new_desc)
                    # Merge source chunk indices
                    existing_data["source_chunk_index"].extend(
                        rel_data.get("source_chunk_index", [])
                    )  # Dont remove duplicates

            # Merge strengths with an aggregation method
            if isinstance(rel_data["strength"][0], (int, float)):
                # Combine existing and new strengths
                all_strengths = (
                    existing_data["strength"] + rel_data["strength"]
                )  # This is a list concatenation operation

                # Calculate the harmonic mean
                calculated_strength = harmonic_mean(all_strengths)

                # Ensure the strength does not exceed the maximum of 10
                existing_data["strength"] = [min(calculated_strength, 10.0)]
            else:
                # Default to deduplicating categorical strengths
                existing_data["strength"].extend(rel_data["strength"])
                existing_data["strength"] = list(set(existing_data["strength"]))

        else:
            # Add the relationship to the updated relationships
            updated_relationships[updated_key] = {
                "description": rel_data["description"][:],  # Copy the list
                "strength": rel_data["strength"][:],  # Copy the list
                "source_chunk_index": rel_data.get(
                    "source_chunk_index", []
                ),  # Copy the list
            }

    return updated_relationships, relationship_updates
# ---------------Method for updating deduplicated relationships-End-------------#



# === Two system approach === #
# Detailed design documentation is available in Bodhi/resolution.md
# System 1 : Rule based Resolution
class RuleBasedResolver:
    """
    System 1: Executes a sequence of rules to find a match.
    The first rule that returns a decision other than NO_MATCH wins.
    """

    def __init__(self, rules, similarity_model):
        self.rules = rules  # A list of rule objects
        self.similarity_model = similarity_model
        logger.info(f"Rule-based resolver initialized with {len(self.rules)} rules.")

    def check_for_merge(self, entities):
        """
        Iterates through its rules to evaluate the entity pair.
        """
        resolution_results = {}
        # This implementation evaluates all system 1 rules for all the entities
        for rule in self.rules:
            response = rule.evaluate(entities, similarity_model=self.similarity_model)
            resolution_results[type(rule).__name__] = response
        return resolution_results
    
    def inference(self, entities):
        """
        This method infers the final decision based on the decisions from all rules.
        Implements a truth table:
            - If NameAndDescriptionRule returns MERGE, then check DifferByNumberRule:
                - If DifferByNumberRule returns MERGE, return MERGE.
                - If DifferByNumberRule returns DEFER, return DEFER.
            - If NameAndDescriptionRule returns NO_MATCH, return NO_MATCH.
            - If DifferByNumberRule returns NO_MATCH, return NO_MATCH.
        The implementation is designed to make sure dependency injection for the truth table logic is 
        possible in future.
        """
        
        resolution_results = self.check_for_merge(entities)

        
        # Decouple the decision logic for future dependency injection
        # --- Decision1 logic begin ---
        # name_desc_decision = decisions_scores.get("NameAndDescriptionRule", {}).get("decision", NO_MATCH)
        # number_rule_decision = decisions_scores.get("DifferByNumberRule", {}).get("decision", NO_MATCH)

        # logger.debug(f"name_desc_decision: {name_desc_decision}, number_rule_decision:{number_rule_decision}")
        # final_decision = DEFER  # Default decision

        # if name_desc_decision == MERGE:
        #     if number_rule_decision == NO_MATCH:
        #         final_decision = MERGE
        #     elif number_rule_decision == DEFER:
        #         final_decision = DEFER
        #     else:  # number_rule_decision will either be DEFER or NO_MATCH. Logic should never reach here
        #         raise ValueError("Unexpected logic branch")
        # elif name_desc_decision == NO_MATCH:
        #     final_decision = NO_MATCH
        # else: # name_desc_decision will either be NO_MATCH or MERGE. Logic should never reach here
        #     raise ValueError("Unexpected logic branch")
        # --- Decision1 logic end ---

        # --- Decision2 logic begin ---
        
        name_desc_decision = resolution_results.get("NameAndDescriptionRule", {}).get("decision", NO_MATCH)
        if name_desc_decision == MERGE:
            final_decision = MERGE
        elif name_desc_decision == NO_MATCH:
            final_decision = NO_MATCH
        else:
            raise(ValueError(f"Wrong name_desc_decisoin: {name_desc_decision}"))
        # --- Decision2 logic end ---

        result = {"decision":final_decision,**resolution_results}
        return result
    
# System 2 : LLM based Resolution
class LLMResolver:
    def resolve_ambiguity(self, entities):
        logger.info(
            f"    - LLM System 2: Resolving ambiguity for '{entities}'..."
        )
        if len(list(entities.keys()))>10: # Mock logic for now
            logger.info(
                "    - LLM Decision: Distinct entities (e.g., different years/versions). Result: NO_MERGE."
            )
            return "NO_MERGE"
        return "MERGE"


class HybridResolver:
    """
    A hybrid entity resolution system that combines rule-based and LLM-based approaches.

    This resolver first attempts to deduplicate entities using a rule-based system (System 1).
    If ambiguity is detected (i.e., the rule-based system defers the decision), it leverages
    a language model-based resolver (System 2) to resolve the ambiguity.

    Attributes:
        system1 (RuleBasedResolver): The rule-based entity resolver.
        system2 (LLMResolver): The language model-based entity resolver.
        similarity_model: A model used to compute similarity between entities.

    Methods:
        resolve(entities):
            Deduplicates a dictionary of entities using both rule-based and LLM-based logic.
            Returns a dictionary of deduplicated entities and a map of merged entity names.
            
            - assumptions on entities:
                - sample input data:
                    {
                    "Google": {"type": ["Company"], "description": ["A technology company."]}, 
                    "Alphabet Inc.": { "type": ["Corporation"],"description": ["Parent company of Google."]},
                    }
                - Key of each entity is its name.
                - Each entity is a dictionary with fields like "type", "description", etc.
                - Each field can have multiple values, hence stored as a list.
                - There are no constraints on the number of fields or their types. This allows for flexible schemas,
                hence reuse the HybridResolver for entities with different schemas, relationships with different properties, etc.
    """
    def __init__(self, system1_resolver, similarity_model):
        self.system1 = system1_resolver  # This is our RuleBasedResolver instance
        self.system2 = LLMResolver()
        self.similarity_model = similarity_model

    def resolve(self, entities):
        """
        System 2 resolution is disabled for now. Further R&D is required to integrate a robust system 2 entity resolution pipeline.
        """
        logger.info("\nStarting hybrid entity resolution with pluggable rules...\n")
        resolution_results= self.system1.inference(entities)
        # logger.info(f"Resolution results from System 1: {resolution_results}")
        resolved_nodes = resolution_results.get("NameAndDescriptionRule").get("resolved_nodes")
        resolution_map = resolution_results.get("NameAndDescriptionRule").get("similar_names")
       
        return resolved_nodes, resolution_map


# ==================================
# EXAMPLE USAGE
# ==================================
def test_main_2():
    from .resolution_rules import DifferByNumberRule, NameAndDescriptionRule


    # 1. Define the rules you want to use
    # The order is important! We check for the "number" ambiguity first.
    resolution_rules = [
        NameAndDescriptionRule(name_threshold=0.9, desc_threshold=0.85),
        # DifferByNumberRule(),
        # You can easily add more rules here later!
        # e.g., AcronymMatchRule(), SameAddressRule(), etc.
    ]

    # 2. Instantiate the system with these rules
    model_path = "all-mpnet-base-v2"
    similarity_model = SemanticSimilarity(model_path,device="cuda")
    system1_engine = RuleBasedResolver(
        rules=resolution_rules, similarity_model=similarity_model
    )
    resolver = HybridResolver(
        system1_resolver=system1_engine, similarity_model=similarity_model
    )

    f_path = "infra/storage/Bodhi/AI_Foundations_of_Computational_Agents/AI_Foundations_of_Computational_Agents_intermediate_data.yml"
    intermediate_entities_ts_2,_ = load_nodes_n_relns_from_intermediate_file(f_path)

    # 3. Run the resolution
    intermediate_entities_ts_1 = {
        "SEC Filing 2023": {
            "type": ["Report"],
            "description": ["Annual report for fiscal year 2023"],
        },
        "SEC Filing 2024": {
            "type": ["Report"],
            "description": ["Annual report for fiscal year 2024"],
        },
        "Google": {"type": ["Tools"], "description": ["A search engine."]},
        "Google inc.": {"type": ["Company"], "description": ["A technology company."]},
        "Alphabet Inc.": {
            "type": ["Corporation"],
            "description": ["Parent company of Google."],
        },
    }

    final_entities, final_map = resolver.resolve(intermediate_entities_ts_2)

    # logger.info("\n--- Final Deduplicated Entities ---")
    # logger.info(final_entities)
    # logger.info("\n--- Deduplication Map ---")
    # logger.info(final_map)


if __name__ == "__main__":
    test_main_2()
