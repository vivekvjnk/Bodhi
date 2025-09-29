"""
Author: Prophet System Team
"""
import networkx as nx

from pathlib import Path
import yaml
import logging
from omegaconf import DictConfig

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph


from .states.bodhi import BodhiState,BodhiInputState
from .resolution.entity_resolution import HybridResolver,RuleBasedResolver
from .resolution.resolution_rules import NameAndDescriptionRule
from .utils import harmonic_mean, create_unique_trace_id,SemanticSimilarity,save_nodes_n_relns_to_intermediate_file
from .structured_text_detection.reference_detector import isolate_references_section

# Storage
from Sanchayam import Sanchayam

from .parallel_kg_extractor import extract_knowledge_graph_parallel

logger = logging.getLogger(__name__)

class Bodhi:
    def __init__(self,config:DictConfig=None): # Pass base configuration
        # Langfuse
        self.parent_trace_id = create_unique_trace_id() # Unique identifier for bodhi run
        if not config:
            raise ValueError(f"No config found: {config}")
        
        self.config = config
        #storage 
        self.storage = Sanchayam(storage_backend=self.config["storage_backend"],storage_dir=self.config["storage_dir"])

        self.artifacts_dir = "Bodhi"        
        self.dedup_interm_data_path = None
        self.interm_data_path = None # Need to review code related to this var
    
        self.prompt_path = config.get("prompt_path","Bodhi.prompt_engineering.bodhi")    
        self.paths = {}

    def invoke(self,state:dict):

        source_path = state.get("source_path")
        ontology = state.get("ontology", {})

        intermediate_graph, goto = self.generate_graph(source_path=source_path,ontology=ontology)

        if goto == "resolve_graph":
            resolved_graph = self.resolve_graph(self.paths, intermediate_graph)
            return resolved_graph
        elif goto == "END":
            # Load the graph from the file
            logger.info(f"Loading resolved graph from {self.paths.get('graph_path')}")
            f = self.storage.read_file(path=self.paths.get("graph_path"))
            # Deserialize the graph
            serial_netx_graph = yaml.safe_load(f)
            logger.debug(f"Deserialized graph: {serial_netx_graph}")
            # Convert to NetworkX graph
            resolved_graph = nx.node_link_graph(serial_netx_graph)
            logger.info(f"Resolved graph loaded successfully from {self.paths.get('graph_path')}")

            if not resolved_graph:
                raise ValueError(f"Resolved graph file {self.paths.get('graph_path')} is empty. Cannot proceed.")
            return resolved_graph
        else:
            raise ValueError(f"Unexpected goto value: {goto}")
        
    
    def resolve_graph(self,paths,intermediate_graph):
        '''
        Objectives 
        1. Deduplication of entities and relations 
        2. Save the deduplicated information to intermediate file
        2. Generate networkX graph from the optimized entity-relation information
        '''
        node_name = "resolve_graph"
        logger.info(f"\n---NODE: {node_name}---")
        dedup_interm_data_path = paths.get("dedup_interm_data_path")
        # Check if deduplicated graph is already available 
        if(self.storage.file_exists(path=dedup_interm_data_path)):
            dd_file = self.storage.read_file(path=dedup_interm_data_path)
            logger.info(f"Found deduplication file.Loading..")
            dd_content = yaml.load(dd_file,Loader=yaml.FullLoader)
            deduplicated_entities = dd_content['entities']
            updated_relationships = dd_content['relationships']
        else:
            # TODO : Replace following state preservation logic with langgraph persistence 
            logger.info(f"Deduplication pipeline started")
            if intermediate_graph is None:
                entities,relations = self.load_nodes_n_relns_from_intermediate_data(paths=paths)
            else:
                # Convert the intermediate graph to entities and relationships
                logger.info(f"Converting intermediate graph to entities and relationships")
                entities, relations = self.load_nodes_n_relns_from_intermediate_data(
                    entities=intermediate_graph.get("entities", []),
                    relationships=intermediate_graph.get("relationships", []),
                ) 
            # log first few entities and relationships
            # logger.debug(f"Entities:\n {intermediate_graph.get("entities", [])}\n{entities}")
            # logger.debug(f"Relationships:\n{intermediate_graph.get("relationships", [])}\n {relations}")
            #---------------Deduplication logic-Begin-------------#
            # TODO: replace with hybridresolver
            resolution_rules = [
                NameAndDescriptionRule(name_threshold=0.88, 
                                       desc_threshold=0.85,
                                       source_name=self.paths.get("source_name")
                                       ),
                # You can easily add more rules here later!
                # e.g., AcronymMatchRule(), SameAddressRule(), etc.
            ]
            model_path = "all-mpnet-base-v2"
            similarity_model = SemanticSimilarity(model_path,device="cuda")
            system1_engine = RuleBasedResolver(
                rules=resolution_rules, 
                similarity_model=similarity_model
            )
            resolver = HybridResolver(
                system1_resolver=system1_engine, 
                similarity_model=similarity_model
            )
            
            deduplicated_entities, deduplication_map = resolver.resolve(entities)
            logger.info(f"Deduplicated entities:\n {deduplicated_entities}")
            updated_relationships, relationship_updates = self._update_deduplicate_relationships(relationships=relations,
                                                                                                 deduplication_map=deduplication_map)
            #---------------Deduplication logic-End-------------#
            
            # logger.debug(f"Deduplicated relationships:\n {updated_relationships}")
            #---------------<source>_dd_intermediate_data.yml-Begin-------------#
            # self.save_nodes_n_relns_to_intermediate_file(deduplicated_entities,
            #                                     updated_relationships,type=False)
            save_nodes_n_relns_to_intermediate_file(file_path=paths.get("dedup_interm_data_path"),
                                                entities=deduplicated_entities,
                                                relationships=updated_relationships,
                                                storage=self.storage)

            logger.info(f"Deduplication pipeline end. Saved to intermediate file.")
        #---------------<source>_dd_intermediate_data.yml-End---------------#
        
        nx_graph = self._generate_graph_from_dict(deduplicated_entities,updated_relationships)
        # Serialize graph before attaching to state. Checkpointer doesn't support networX graphs
        ser_graph = nx.node_link_data(nx_graph)
        
        # Save the graph to yaml file
        relation_dict_string = b"".join(s.encode('utf-8') for s in yaml.dump(ser_graph,default_flow_style=False, sort_keys=False)) # convert to bytes
        self.storage.save_file(path=self.paths.get("graph_path"),
                                data=relation_dict_string)

        # NetworkX graph is the final output of Bodhi. All other information in State of Bodhi is not supposed to 
        # be used outside Bodhi. 
        return nx_graph
    
    def generate_graph(self,source_path,ontology:dict=None):
        # Set up paths 
        source_name = Path(source_path).stem  # Remove file extension
        graph_info_storage = f"{self.artifacts_dir}/{source_name}"
        self.paths = {
            "source_path": source_path,
            "source_name": source_name,  
            "dedup_interm_data_path": f"{graph_info_storage}/{source_name}_dd_intermediate_data.yml",
            "interm_data_path": f"{graph_info_storage}/{source_name}_combined_intermediate_data.yml",
            "text_unit_path": f"{graph_info_storage}/{source_name}_text_units.yml",
            "raw_text_path": f"{graph_info_storage}/{source_name}_text.yml",
            "ref_separated_raw_text_path":f"{graph_info_storage}/{source_name}_ref_separated_text.yml",
            "graph_path": f"{graph_info_storage}/{source_name}_graph.yml",
            "graph_info_storage": graph_info_storage,
            "prompt_path": self.prompt_path
        }


        # Check if resolved_intermediate_graph exists in storage
        if self.storage.file_exists(path= self.paths.get("graph_path")):
            logger.info(f"Found final graph:{self.paths.get("graph_path")}\n...")
            f = self.storage.read_file(path=self.paths.get("graph_path"))
            resolved_graph = yaml.safe_load(f)
            if not resolved_graph:
                raise ValueError(f"Resolved graph file {self.paths.get("graph_path")} is empty. Cannot proceed.")
            intermediate_graph = None # No need to generate intermediate graph
            goto = "END"

        elif self.storage.file_exists(path= self.paths.get("interm_data_path")):
            logger.info(f"Found combined intermediate file:{self.paths.get("interm_data_path")}\n. Proceeding with graph resolution..")
            # Load the intermediate graph
            f = self.storage.read_file(path=self.paths.get("interm_data_path"))
            intermediate_graph = yaml.safe_load(f)
            if not intermediate_graph:
                raise ValueError(f"Intermediate graph file {self.paths.get("interm_data_path")} is empty. Cannot proceed.")
            goto = "resolve_graph"
        
        else:
            logger.info(f"Generating graph for source: {source_name}")
            intermediate_graph = extract_knowledge_graph_parallel(
                storage=self.storage,
                config=self.config,
                paths=self.paths,
                parent_trace_id=self.parent_trace_id,
                text_extraction_func=_extract_text_chunks,
                max_num_threads=self.config["max_num_threads"],
                entity_types= ontology.get("entity_types", None) if ontology else None,
            )
            goto = "resolve_graph"

        return intermediate_graph, goto

    #---------------Support functions-Begin-------------#
    #---------------Intermediate file handling-Begin-------------#    
    def load_nodes_n_relns_from_intermediate_data(self,paths=None,entities=None, relationships=None):
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
        
        file_path = paths.get("interm_data_path",None)
        try:
            data = {}
            if entities and relationships:
                logger.info("Using provided entities and relationships.")
                data = {
                    "entities": entities,
                    "relationships": relationships
                }
            elif(file_path == None): 
                raise ValueError("Either `paths` or `entities` and `relationships` should be provided")
            else:
                logger.info(f"Loading intermediate graph from {file_path}")
                file = self.storage.read_file(path=file_path)
                data = yaml.safe_load(file)
            if data is None:
                logger.error(f"Warning: File {file_path} is empty. Returning empty dictionaries.")
                return {}, {}

            if not isinstance(data, dict) or "entities" not in data or "relationships" not in data:
                logger.error(f"Warning: File {file_path} does not contain expected 'entities' and 'relationships' structure. Returning empty dictionaries.")
                return {}, {}
            
            entities_dict = {}
            relationships_dict = {}

            for entity in data["entities"]:
                name = entity["name"]
                entities_dict.setdefault(name, {"type": [], "description": [], "source_chunk_index": []})
                entities_dict[name]["type"].append(entity.get("type")) #Use get to avoid keyerror
                entities_dict[name]["description"].append(entity.get("description"))
                entities_dict[name]["source_chunk_index"].append(entity.get("source_chunk_index", 0)) # Default to 0 if not present
                

            for relationship in data["relationships"]:
                source = relationship["source_entity"]
                target = relationship["target_entity"]
                key = (source, target)
                relationships_dict.setdefault(key, {"description": [], "strength": [], "source_chunk_index": []})
                relationships_dict[key]["description"].append(relationship.get("description"))
                relationships_dict[key]["strength"].append(relationship.get("strength"))
                relationships_dict[key]["source_chunk_index"].append(relationship.get("source_chunk_index", 0)) # Default to 0 if not present
            return entities_dict, relationships_dict

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}. Returning empty dictionaries.")
            return {}, {}
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}. Returning None, None.")
            return None, None
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}. Returning None, None.")
            return None, None
    #---------------Intermediate file handling-End-------------# 
    
    def _generate_graph_from_dict(self,entities, relationships):
        """
        Generates a NetworkX graph from dictionaries of entities and relationships.

        Args:
            entities (dict): A dictionary where keys are entity names, and values are attributes like type and description.
            relationships (dict): A dictionary where keys are tuples of (source_entity, target_entity), 
                                and values are attributes like description and strength.

        Returns:
            nx.Graph: The constructed graph.
        """
        import networkx as nx
        
        graph = nx.Graph()
        # Add nodes (entities) to the graph
        for entity_name, attributes in entities.items():
            graph.add_node(
                entity_name.strip().upper(),
                # type=", ".join(attributes.get("type", [])).strip().upper(),
                type = ", ".join(map(lambda x: str(x) if x is not None else "None", attributes.get("type", []))).strip().upper(),
                description=" ; ".join(attributes.get("description", [])).strip(),
                source_index=attributes.get("source_chunk_index", []),
            )

        # Add edges (relationships) to the graph
        for relation, attributes in relationships.items():
            # Convert relationship string to source and target tuple(In case if we are reading from yml file)
            (source_entity, target_entity) = relation
            source = source_entity.strip().upper()
            target = target_entity.strip().upper()
            weight = sum(attributes.get("strength", [5.0]))/len(attributes.get("strength", [5.0]))  # Sum all strengths if multiple are provided
            description = " ; ".join(attributes.get("description", [])).strip()
            source_index=attributes.get("source_chunk_index", [])

            # Add or update the edge
            if graph.has_edge(source, target):
                # Update weight and append description if edge already exists
                edge_data = graph.get_edge_data(source, target)
                edge_data['weight'] += weight
                edge_data['description'] += f" | {description}"
            else:
                graph.add_edge(
                    source,
                    target,
                    weight=weight,
                    description=description,
                    source_index=source_index
                )

        return graph
    
    def _update_entities(self,global_entities, new_entities):
        """
        Updates the global entity list with new entities, ensuring no duplicates are added.

        Args:
            global_entities (list): The current list of global entities.
            new_entities (list): The list of new entities to be added.

        Returns:
            list: The updated global entity list.
        """

        for new_entity in new_entities['entities']:
            if new_entity.get("type") is None:
                raise ValueError(f"Entity type is None for entity: {new_entity}")
            # Check if the new entity is already in the global list
            is_duplicate = any(
                existing_entity["name"].strip().lower() == new_entity["name"].strip().lower() and
                existing_entity["type"].strip().lower() == new_entity["type"].strip().lower()
                for existing_entity in global_entities['entities']
            )
            # Add new entity if not a duplicate
            if not is_duplicate:
                global_entities['entities'].append(new_entity)
        logger.info(f"\n--final entities after update entities--\n{global_entities}\n")
        return global_entities

    def _update_relationships(self,global_relationships, new_relationships):
        """
        Updates the global relationships list with new relationships, ensuring no duplicates are added.

        Args:
            global_relationships (list): The current list of global relationships.
            new_relationships (list): The list of new relationships to be added.

        Returns:
            list: The updated global relationships list.
        """
        for new_relationship in new_relationships:
            # Check if the new relationship is already in the global list
            is_duplicate = any(
                existing_relationship["source_entity"].strip().lower() == new_relationship["source_entity"].strip().lower() and
                existing_relationship["target_entity"].strip().lower() == new_relationship["target_entity"].strip().lower() and
                existing_relationship["description"].strip().lower() == new_relationship["description"].strip().lower() and
                existing_relationship["strength"] == new_relationship["strength"]
                for existing_relationship in global_relationships
            )
            # Add new relationship if not a duplicate
            if not is_duplicate:
                global_relationships.append(new_relationship)
        logger.info(f"\n--final relationships after update--\n{global_relationships}\n")
        return global_relationships

    def _update_deduplicate_relationships(self,relationships, deduplication_map):
        """
        Updates relationships based on deduplications made on entities and tracks changes.

        Args:
            relationships (dict): Dictionary containing relationships in the format:
                { (source, destination): {"description": [...], "strength": [...]}}
            deduplication_map (dict): Map of deduplicated entities in the format:
                { original_entity: deduplicated_entity }

        Returns:
            tuple: (updated_relationships, relationship_updates)
                - updated_relationships (dict): Updated relationships with deduplicated entities.
                - relationship_updates (dict): Map of original relationships to their updated relationships.
        TODO: Implement semantic similarity check for descriptions.
        """
        updated_relationships = {}
        relationship_updates = {}

        for (source, destination), rel_data in relationships.items():
            # Check if source or destination has been deduplicated
            updated_source = deduplication_map.get(source, source)
            updated_destination = deduplication_map.get(destination, destination)

            # Define the updated relationship key
            updated_key = (updated_source, updated_destination)
            original_key = (source, destination)

            # Track the relationship update
            if original_key != updated_key:
                relationship_updates[original_key] = updated_key

            # Merge data if the relationship already exists with the updated key
            if updated_key in updated_relationships:
                existing_data = updated_relationships[updated_key]

                # Merge descriptions
                existing_data["description"].extend(rel_data["description"])
                existing_data["description"] = list(set(existing_data["description"]))  # Remove duplicates
                
                # Merge source chunk indices
                existing_data["source_chunk_index"].extend(rel_data.get("source_chunk_index", [])) # Dont remove duplicates

                # Merge strengths
                existing_data["strength"].extend(rel_data["strength"])
                existing_data["strength"] = list(set(existing_data["strength"]))  # Remove duplicates

            else:
                # Add the relationship to the updated relationships
                updated_relationships[updated_key] = {
                    "description": rel_data["description"][:],  # Copy the list
                    "strength": rel_data["strength"][:],        # Copy the list
                    "source_chunk_index": rel_data.get("source_chunk_index", []),  # Copy the list
                }

        return updated_relationships, relationship_updates

    #TODO : Integrate this function in next version 
    def _update_deduplicate_relationships_optimized(
        relationships, deduplication_map, similarity_threshold=0.8
    ):
        """
        Updates relationships based on deduplications made on entities and tracks changes.

        Args:
            relationships (dict): Dictionary containing relationships in the format:
                { (source, destination): {"description": [...], "strength": [...]}}
            deduplication_map (dict): Map of deduplicated entities in the format:
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
        similarity_checker = SemanticSimilarity(model_path=model_path)  # Use your semantic similarity class

        for (source, destination), rel_data in relationships.items():
            # Check if source or destination has been deduplicated
            updated_source = deduplication_map.get(source, source)
            updated_destination = deduplication_map.get(destination, destination)

            # Define the updated relationship key
            updated_key = (updated_source, updated_destination)
            original_key = (source, destination)

            # Track the relationship update
            if original_key != updated_key:
                relationship_updates[original_key] = updated_key

            # Merge data if the relationship already exists with the updated key
            if updated_key in updated_relationships:
                existing_data = updated_relationships[updated_key]

                # Merge descriptions using semantic similarity
                for new_desc in rel_data["description"]:
                    if not any(
                        similarity_checker.is_similar(new_desc, existing_desc, similarity_threshold)
                        for existing_desc in existing_data["description"]
                    ):
                        existing_data["description"].append(new_desc)
                        # Merge source chunk indices
                        existing_data["source_chunk_index"].extend(rel_data.get("source_chunk_index", [])) # Dont remove duplicates


                # Merge strengths with an aggregation method
                if isinstance(rel_data["strength"][0], (int, float)):
                    
                    # Combine existing and new strengths
                    all_strengths = existing_data["strength"] + rel_data["strength"] # This is a list concatenation operation
                    
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
                    "strength": rel_data["strength"][:],        # Copy the list
                }

        return updated_relationships, relationship_updates

    #---------------Support functions-End-------------#

#--- Helpler functions ---#

def _extract_text_chunks(file_path: str, token_limit: int = 400) -> list[str]:
    """
    Extract meaningful/complete text chunks from a source file.

    Args:
        file_path (str): The path to the source document (text format).
        token_limit (int): Maximum token limit per chunk.

    Returns:
        list[str]: List of text chunks, each below the token limit.
    """
    import spacy
    # Load spaCy for tokenization
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 2700000
    def extract_text_from_file(file_path: str) -> str:
        """Extract text from a file (text or PDF)."""
        try:
            if file_path.lower().endswith(".pdf"):  # Check if it's a PDF
                import pymupdf4llm
                output = pymupdf4llm.to_markdown(file_path)
                print(f"Extracted text from PDF: {output[:100]}...")  # Print first 100 characters

                return output  # Return the markdown output
            elif file_path.lower().endswith(('.txt', '.text','.md')): # if it is a text file
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                    print(f"Extracted text from PDF: {text[:100]}...")  # Print first 100 characters
                    return text
            else:
                return "Unsupported file type" # if it is of any other type

        except Exception as e: # Handle any exception
            raise(ValueError(f"Error extracting text: {e}")) 

    def split_into_chunks(text: str, token_limit: int) -> list[str]:
        """Split text into chunks based on the token limit."""
        chunks = []
        current_chunk = ""
        current_token_count = 0

        # Tokenize the entire text
        doc = nlp(text)

        for sentence in doc.sents:
            sentence_text = sentence.text.strip()
            sentence_token_count = len(sentence)

            if current_token_count + sentence_token_count <= token_limit:
                current_chunk += f"{sentence_text} "
                current_token_count += sentence_token_count
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence_text
                current_token_count = sentence_token_count

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    # Step 1: Extract raw text from the file 
    raw_text = extract_text_from_file(file_path)
    
    ref_separated_raw_text = isolate_references_section(raw_text)
    # Step 2: Split text into chunks based on token limit
    text_units = split_into_chunks(ref_separated_raw_text["text"], token_limit)

    return {"text_units":text_units,"raw_text":raw_text,"ref_separated_raw_text":ref_separated_raw_text}    


# Bodhi test code 
if __name__ == "__main__1":
    # Langfuse tracing 
    parent_trace_id = create_unique_trace_id()

    bodhi = Bodhi(parent_trace_id=parent_trace_id)
    
    init_state = {"source_path":"2504.06821.pdf"}
    
    final_state = bodhi.invoke(init_state)
    
# Bodhi v2 test code 

if __name__ == "__main__":
    parent_trace_id = 109
    
    def get_pdfs_starting_with(directory, prefix):
        directory_path = Path(directory)
        pdf_files = [file.name for file in directory_path.glob(f"{prefix}*.pdf")]
        return pdf_files
    
    def get_mds_starting_with(directory, prefix):
        directory_path = Path(directory)
        pdf_files = [file.name for file in directory_path.glob(f"{prefix}*.md")]
        return pdf_files
    # load entity types 
    # with open("experiments/ontology_discovery/discovered_schemas/ai_agentics.yml","r") as f:
    #     entity_type_dict = yaml.safe_load(stream=f) 
    # print(f"Entity types:\n{entity_type_dict}")
    # entity_types = [entity["name"] for entity in entity_type_dict]
    entity_types = {"Task":"Represents a scientific or application-oriented objective that the method is designed to accomplish","Method":"Refers to a specific algorithm, model, computational technique, statistical tool, or approach used in the study","Dataset":"Refers to a structured collection of data, often from biological, chemical, or clinical sources, used to train, validate, or test methods","generic":"Generic type. Use this if extracted entity doesn't not belong to any other types. Consider this as a type failure fallback. Try not to use this entity type as much as possible"}
    
    ontology = {"entity_types":entity_types}
    source_list = get_mds_starting_with(directory="infra/storage/data",prefix="doc")
    
    # source_list = get_pdfs_starting_with(directory="infra/storage/data",prefix="250")
    # = ["2504.14603.pdf"] 
    # = ["2503.22625.pdf","2504.01990.pdf"]
    
    bodhi = Bodhi(parent_trace_id=parent_trace_id)

    # extract graph for each of the source files
    for source in source_list:
        # if source == "2504.06821.pdf":
        #     continue
        init_state = {"source_path": source,"ontology": ontology}
        bodhi.invoke(init_state) # Bodhi will save extracted knowledge graph in a spe
    