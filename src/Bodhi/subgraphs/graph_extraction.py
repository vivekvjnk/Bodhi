from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from typing import Literal
from pathlib import Path
import yaml

from heimdall import heimdall_graph

from ..prompt_engineering.prompt_parser import parse_prompts
from ..states.bodhi import BodhiState,EntityExtractionOutput, EntityValidationFeedback, RelationshipExtractionOutput
from ..utils import save_nodes_n_relns_to_intermediate_file

prompt_dictionary = {}

# --- 3. Extraction Subgraph for Workers ---
def create_extraction_subgraph(prompt_path) -> StateGraph:
    """
    Creates a new LangGraph instance for the core extraction pipeline.
    This subgraph processes ONE text unit at a time.
    Flow: extract_entities -> validate_entities -> extract_relationships -> validate_relationships
    """
    global prompt_dictionary
    subgraph = StateGraph(BodhiState)
    
    subgraph.add_node("extract_graph", extract_graph)    
    subgraph.add_node("extract_entities", extract_entities)
    subgraph.add_node("validate_entities", validate_entities)
    subgraph.add_node("extract_relationships", extract_relationships)
    subgraph.add_node("validate_relationships", validate_relationships)

    subgraph.add_edge(START, "extract_graph")
    subgraph.add_edge("extract_entities", "validate_entities")
    subgraph.add_edge("extract_relationships", "validate_relationships")
    graph = subgraph.compile()
    prompt_dictionary = parse_prompts(prompt_path)
    return graph

# Orchestrator function (No LLM calls) 
def extract_graph(state) -> Command[Literal[END,"extract_entities"]]:
    """
    Processes the input file to extract text units, orchestrates entity and relationship extraction, 
    and manages intermediate file storage for the Bodhi pipeline.

    This function verifies the presence of required files and determines the appropriate next step
    in the extraction pipeline. It ensures continuity by maintaining intermediate states and saving 
    extracted information at each step.

    Args:
        state (dict): The current state of the extraction pipeline, containing metadata and progress details.

    Returns:
        Command: A command object that updates the pipeline state and directs execution to the next node.

    Workflow:
    1. **Graph Database Content Verification**
        - Checks if required artifacts exist in the artifacts directory.
        - Identifies missing artifacts and determines processing needs.
    
    2. **State Management and Orchestration**
        - Determines the appropriate next step based on available intermediate files.
        - If deduplicated intermediate data exists, proceeds to graph building.
        - If partial extraction data exists, resumes entity extraction from the last processed chunk.
     
    3. **Intermediate Data Handling**
        - Saves extracted entities and relationships after each chunk is processed.
        - Maintains continuity by updating chunk indices and resetting temporary state variables.
    
    Transitions:
        - END : If all text chunks are processed, stop.
        - "extract_entities": If text extraction is incomplete, continue extracting entities.
    
    Raises:
        ValueError: If the specified source file does not exist.
    """
    # raise ValueError("hello fool")
    node_name = "extract_graph"
    loc_state = state

    logger = loc_state.get('metadata', {}).get('logger', None)
    thread_id = loc_state.get('metadata', {}).get('thread_id', None)
    storage = loc_state.get('metadata', {}).get('storage', None)
    text_units = loc_state.get('metadata', {}).get('text_units', None)

    logger.info(f"\n---NODE: {node_name}---")

    if 'source_path' not in loc_state or loc_state['source_path'] is None:
        raise ValueError("Missing or None source_path in loc_state")
    source_path = loc_state['source_path']
    source_name = loc_state.get('source_name', Path(source_path).stem)  # Use stem to get the file name without extension
    
    graph_info_storage = f"Bodhi/{source_name}"
    interm_data_path = f"{graph_info_storage}/{thread_id}/{source_name}_intermediate_data.yml"
    
    required_keys = ['text_chunks', 'number_of_chunks', 'chunk_index', 'entities', 'relationships']
    missing_keys = required_keys - loc_state.keys()
    # check if chunks file and intermediate_data files are available 
    # Continue from the intermediate state
    if (missing_keys): # very first call to the extract_graph function
        
        logger.info(f"source chunk:\n{"\n---\n".join(text_units)}")
        
        if storage.file_exists(path= interm_data_path): 
            loc_state['text_chunks'] = text_units
            loc_state['number_of_chunks'] = len(loc_state['text_chunks'])

            intermediate_content = storage.read_file(path= interm_data_path)
            intermediate_content = yaml.safe_load(intermediate_content)

            loc_state['entities'] = intermediate_content.get('entities', [])
            loc_state['relationships'] = intermediate_content.get('relationships', [])

            loc_state['chunk_index'] = max(intermediate_content['chunk_indices']) # start extraction from next chunk
            
            logger.info(f"Found intermediate file, Continuing from index {loc_state['chunk_index']+1} of {loc_state['number_of_chunks']}")
            
            if((loc_state['chunk_index']+1)>=(loc_state['number_of_chunks'])):
                logger.info(f"""---NODE: {node_name}---INFO: All the text units are already processed. Going to END---""")
                goto = END 
            else:
                goto = "extract_entities"
    
        else: # => Very first iteration. Need to extract text chunks from source file
            loc_state['number_of_chunks'] = len(text_units)
            loc_state['chunk_index'] = 0
            loc_state['text_chunks'] = text_units
            goto = "extract_entities" 
    # Check if reached last text chunk
    elif((loc_state['chunk_index'])>=(loc_state['number_of_chunks'])-1): 
        logger.info(f"---NODE: {node_name}---INFO: Reached last chunk. Going to END---")
        
        save_nodes_n_relns_to_intermediate_file(file_path=interm_data_path,
                                                entities=loc_state['entities']['entities'],
                                                relationships=loc_state['relationships'],
                                                chunk_index=loc_state['chunk_index'],
                                                storage=storage
                                                )
        logger.info(f"---NODE: {node_name}---INFO: All the text units are processed and saved. Going to END---")
        goto = END 

    # Neither first chunk, nor last chunk, 
    else: # Repeat extraction for the next chunk 
        # Before repeating the extraction pipeline, we have to store the already extracted information 
        # into yml/json formatted file & then clean up the entity/relations state variables 
        # Save the extracted information
        logger.info(f"---NODE: {node_name}---INFO: saving to intermediate file---")
        save_nodes_n_relns_to_intermediate_file(file_path=interm_data_path,
                                                entities=loc_state['entities']['entities'],
                                                relationships=loc_state['relationships'],
                                                chunk_index=loc_state['chunk_index'],
                                                storage=storage
                                                )
        # Reset the relationships and entitites state variables
        loc_state['entities'] = []
        loc_state['relationships'] = []
        loc_state['chunk_index'] += 1
        goto = "extract_entities"
    
    logger.info(f"\n---NODE: {node_name}---INFO: Chunk Index={loc_state['chunk_index']+1}/{loc_state['number_of_chunks']}---\n")
        
    return Command(update = loc_state,goto=goto)

def extract_entities(state):

    def normalize_entity_types(type_resolved_entities: dict) -> dict:
        for entity in type_resolved_entities.get("entities", []):
            if entity.get("type") is not None:
                # Strip all spaces and convert to lowercase
                normalized = entity["type"].replace(" ", "").lower()
                entity["type"] = normalized
        return type_resolved_entities
        
    node_name = "extract_entities"
    loc_state = state
    logger = loc_state.get('metadata', {}).get('logger', None)
    llm = loc_state.get('metadata', {}).get('llm', None)
    thinking_llm =loc_state.get('metadata', {}).get('thinking_llm', None)
    parent_trace_id = loc_state.get('metadata', {}).get('trace_id', None)
    
    special_instructions = f"""Strict Instructions:\n    - Strictly avoid extracting research paper citations as nodes. They will be processed by a dedicated pipeline\n  - If the given text unit contain only citations, ignore them altogether\n - Strictly avoid extracting research paper authors as nodes. They will be processed by dedicated pipeline"""
    logger.info(f"\n---NODE: {node_name}---")

    entity_types = {key.lower():item for key,item in loc_state['entity_types'].items()}
    priming_flag = loc_state.get('metadata', {}).get('priming_flag', False)
    if priming_flag:
        priming_summary = loc_state['summary']
        priming_instructions = prompt_dictionary.get('PrimingInstructionsWithTypes').text
    if ("entity_validation_feedback" in loc_state and
        loc_state["entity_validation_feedback"]['loop_required'] == True):
        logger.info("\n--entity_validation_feedback--\n")
        # reset loop variable 
        loc_state["entity_validation_feedback"]['loop_required'] = False
        reason_to_loop = f"{loc_state["entity_validation_feedback"]["reason_to_loop"]}"
        content = loc_state['text_chunks'][loc_state['chunk_index']]

        # LLM Call setup and run - Begin
        input_vars = {"content":content,"reason_to_loop":reason_to_loop,"entity_types":entity_types,"special_instructions":special_instructions}
        if priming_flag:
            input_vars |= {"priming_summary":priming_summary,"priming_instructions":priming_instructions}
        prompt = prompt_dictionary['ExtractEntitiesReflection']['system'].text
        entities = heimdall_graph(input_vars=input_vars,llm=llm,prompt=prompt,pydantic_object=EntityExtractionOutput)
        # LLM Call setup and run - End

        # list all entity types in entities dictionary which are not in the entity_types list
        hallucinated_entity_types = set(entity.get('type').lower() for entity in entities.get('entities', [])) - set(entity_types.keys())
        iter_limiter = 0
        new_entities = entities
        while(hallucinated_entity_types):
            flagged_entities = [entity for entity in new_entities["entities"] if entity["type"].lower() in hallucinated_entity_types]
            outlier_feedback = f"Found following hallucinated entity types in the extracted entities.\n {hallucinated_entity_types}\n Following are extracted entities which belong to the hallucinated entity types: \n {flagged_entities}\nUpdate the listed entities with single best-fitting allowed type from the ENTITY TYPES list.\n"
            logger.warning(f"{iter_limiter} :{outlier_feedback}")

            input_vars = {"entity_types":entity_types,"special_instructions":special_instructions,
                          "flagged_entities":flagged_entities,"hallucinated_entity_types":hallucinated_entity_types} 
            if priming_flag:
                input_vars |= {"priming_instructions":priming_instructions,"priming_summary":priming_summary}
            prompt = prompt_dictionary['ResolveEntityTypes']['system'].text            

            if iter_limiter>3:
                type_resolved_entities = normalize_entity_types(
                                                    heimdall_graph(
                                                        input_vars=input_vars,
                                                        llm=thinking_llm,
                                                        prompt=prompt,
                                                        pydantic_object=EntityExtractionOutput
                                                        )
                                                    )

            else:
                type_resolved_entities = normalize_entity_types(
                                                    heimdall_graph(
                                                        input_vars=input_vars,
                                                        llm=llm,
                                                        prompt=prompt,
                                                        pydantic_object=EntityExtractionOutput
                                                        )
                                                    )
            logger.info(f"resolved entities: {type_resolved_entities}")
            new_entities["entities"] = [entity for entity in new_entities["entities"] if entity["type"].lower() not in hallucinated_entity_types]
            new_entities["entities"].extend(type_resolved_entities["entities"]) 

            hallucinated_entity_types = set(entity.get('type').lower() for entity in new_entities.get('entities', [])) - set(entity_types.keys())
            iter_limiter +=1
        loc_state['entities']['entities'].extend(new_entities['entities'])
        loc_state['entity_types'] = entity_types
        
    else:
        logger.info(
            f"\n--entity_extraction--\nchunk index = {loc_state['chunk_index']+1}"
            )
        

        content = loc_state['text_chunks'][loc_state['chunk_index']]
        input_vars = {"special_instructions":special_instructions,"content":content} 
        if priming_flag:
            input_vars |= {"priming_summary":priming_summary,"priming_instructions":priming_instructions}
        
        if entity_types: # no entity types provided, use extract_entities_no_types prompt
            prompt = prompt_dictionary['ExtractEntitiesWithTypes']['system'].text
            input_vars |= {"entity_types":entity_types}    
        else:
            prompt = prompt_dictionary['ExtractEntitiesNoTypes']['system'].text
            
        entities = heimdall_graph(prompt=prompt,
                                  input_vars=input_vars,
                                  llm=llm,
                                  pydantic_object=EntityExtractionOutput)
        
        
        # list all entity types in entities dictionary which are not in the entity_types list
        hallucinated_entity_types = set(entity.get('type').lower() for entity in entities.get('entities', [])) - set(entity_types.keys())
        # if new_entity_types:
        #     logger.warning(f"Found new entity types in extraction: {new_entity_types}. Adding to entity_types.")
        #     entity_types.extend(new_entity_types)
        iter_limiter = 0
        new_entities = entities
        while(hallucinated_entity_types):
            flagged_entities = [entity for entity in new_entities["entities"] if entity["type"].lower() in hallucinated_entity_types]
            outlier_feedback = f"Found following new entity types in the extracted entities.\n {hallucinated_entity_types}\n Following are extracted entities which belong to the hallucinated entity types: \n {flagged_entities}\nUpdate the listed entities with single best-fitting allowed type from the ENTITY TYPES list.\n"
            logger.warning(f"{iter_limiter} :{outlier_feedback}")
            
            # Prompt setup
            prompt = prompt_dictionary['ResolveEntityTypes']["system"].text
            input_vars = {"entity_types":entity_types,"special_instructions":special_instructions,"flagged_entities":flagged_entities,"hallucinated_entity_types":hallucinated_entity_types}
            if priming_flag:
                input_vars |= {"priming_summary":priming_summary,"priming_instructions":priming_instructions}
                
            if iter_limiter>3:
                type_resolved_entities = normalize_entity_types(
                    heimdall_graph(
                        prompt=prompt,
                        input_vars=input_vars,
                        pydantic_object=EntityExtractionOutput,
                        llm=thinking_llm
                    ))
            else:
                type_resolved_entities = normalize_entity_types(
                    heimdall_graph(
                        prompt=prompt,
                        input_vars=input_vars,
                        pydantic_object=EntityExtractionOutput,
                        llm=llm
                    ))
                
            new_entities["entities"] = [entity for entity in new_entities["entities"] if entity["type"].lower() not in hallucinated_entity_types]
            new_entities["entities"].extend(type_resolved_entities["entities"])
            
            logger.info(f"resolved entities: {type_resolved_entities}")
            
            hallucinated_entity_types = set(entity.get('type').lower() for entity in new_entities["entities"]) - set(entity_types.keys())
            iter_limiter +=1
        
        loc_state['entities'] = new_entities
        loc_state['entity_types'] = entity_types
        loc_state['entity_iter_counter'] = 0

    return loc_state

def validate_entities(state)->Command[Literal["extract_relationships","extract_entities"]]:
    node_name="validate_entities"
    loc_state = state
    
    special_instructions = f"""Strict Instructions::\n    - Strictly avoid extracting research paper citations as nodes. They will be processed by a dedicated pipeline\n  - If the given text unit contain only citations, ignore them altogether\n- Strictly avoid extracting research paper authors as nodes. They will be processed by dedicated pipeline"""
    logger = loc_state.get('metadata', {}).get('logger', None)
    llm = loc_state.get('metadata', {}).get('llm', None)
    parent_trace_id = loc_state.get('metadata', {}).get('trace_id', None)
    # thread_id = loc_state.get('metadata', {}).get('thread_id', None)
    # storage = loc_state.get('metadata', {}).get('storage', None)
    # text_units = loc_state.get('metadata', {}).get('text_units', None)
    
    logger.info(f"\n---NODE: {node_name}---")
    loc_state['entity_iter_counter'] += 1
    max_iterations = 4
        
    entity_iter_counter = loc_state['entity_iter_counter']
    entity_types = loc_state['entity_types']
    priming_flag = loc_state.get('metadata', {}).get('priming_flag', False)
    extracted_entities = loc_state['entities']
    content = loc_state['text_chunks'][loc_state['chunk_index']]  
    
    input_vars = {"content":content,"extracted_entities":extracted_entities,
                  "entity_iter_counter":entity_iter_counter,"special_instructions":special_instructions,
                  "entity_types":entity_types,"max_iterations":max_iterations}
    
    if priming_flag:
        priming_summary=loc_state['summary']
        priming_instructions = prompt_dictionary.get('PrimingInstructionsWithTypes').text
        input_vars |= {"priming_summary":priming_summary,"priming_instructions":priming_instructions}

    prompt = prompt_dictionary['MissingEntities']['system'].text

    # Most of the models fail to follow the instruction not to loopback if iteration count > limit
    # Qwen 2.5 coder : aligns well with the requirement
    # llm = OllamaLLM(temperature=0.2, model="qwen2.5-coder:14b")
    loc_state['entity_validation_feedback'] = heimdall_graph(
                                                    input_vars=input_vars,
                                                    llm=llm,
                                                    prompt=prompt,
                                                    pydantic_object=EntityValidationFeedback
                                                )

    if(loc_state['entity_validation_feedback']['loop_required']):
        goto = "extract_entities"
    else:
        goto = "extract_relationships"
    return Command(update=loc_state,goto=goto)

def extract_relationships(state):
    node_name = "extract_relationships"
    loc_state = state
    
    special_instructions = f"""Guidelines:\n    - Strictly avoid extracting relationships of citation authors. They will be processed by a dedicated pipeline\n  - If the given text unit contain only citations, ignore them altogether\n"""
    
    logger = loc_state.get('metadata', {}).get('logger', None)
    llm = loc_state.get('metadata', {}).get('llm', None)
    priming_flag = loc_state.get('metadata', {}).get('priming_flag', False)
    parent_trace_id = loc_state.get('metadata', {}).get('trace_id', None)
    
    logger.info(f"\n---NODE: {node_name}---")
    
    if "relations_validation_feedback" in loc_state and loc_state["relations_validation_feedback"]['loop_required'] == True:
        logger.info("\n--relations_validation_feedback--\n")
        
        # reset loop variable 
        loc_state["relations_validation_feedback"]['loop_required'] = False
        
        validation_reflection = loc_state["relations_validation_feedback"]["reason_to_loop"]
        content = loc_state['text_chunks'][loc_state['chunk_index']]
        extracted_entities = loc_state['entities']
        extracted_entities_names = [entity["name"] for entity in extracted_entities["entities"]]


        input_vars = {"content":content,"extracted_entities_names":extracted_entities_names,
                      "validation_reflection":validation_reflection,"special_instructions":special_instructions}
        if priming_flag:
            priming_summary=loc_state['summary']
            input_vars |= {"priming_summary":priming_summary}

        prompt = prompt_dictionary['ExtractRelationsFeedback']['system'].text
        relations = heimdall_graph(llm=llm,input_vars=input_vars,prompt=prompt,pydantic_object=RelationshipExtractionOutput)
        
        # remove relationships with hallucinated entities
        extracted_relations = [reln for reln in relations['relationships'] if reln['source_entity'] in extracted_entities_names and reln['target_entity'] in extracted_entities_names]

        if(false_extractions:= [reln for reln in relations['relationships'] if reln not in extracted_relations]):
            logger.warning(f"Found false extractions in relationships: {false_extractions}")
        
        # Update new relationships; make sure duplicates are removed 
        loc_state['relationships'] = _update_relationships(loc_state['relationships'],new_relationships=extracted_relations,logger=logger)

        return loc_state
        
    else:
        logger.info("\n--extract_relationships--\n")

        prompt = prompt_dictionary['ExtractRelationships']['system'].text

        extracted_entities = loc_state["entities"]
        content = loc_state['text_chunks'][loc_state['chunk_index']]  
        extracted_entities_names = [entity["name"] for entity in extracted_entities["entities"]]
        
        input_vars = {"content":content,"extracted_entities":extracted_entities,
                      "extracted_entities_names":extracted_entities_names,"special_instructions":special_instructions}
        if priming_flag:
            priming_summary=loc_state['summary']
            input_vars |= {"priming_summary":priming_summary} 
        # repeated code 
        relations = heimdall_graph(llm=llm,input_vars=input_vars,prompt=prompt,pydantic_object=RelationshipExtractionOutput)
        
        extracted_relations = [reln for reln in relations['relationships'] if reln['source_entity'] in extracted_entities_names and reln['target_entity'] in extracted_entities_names]

        if(false_extractions:= [reln for reln in relations['relationships'] if reln not in extracted_relations]):
            logger.warning(f"Found false extractions in relationships: {false_extractions}")
        
        loc_state['relationships'] = extracted_relations
        loc_state['relations_iter_counter'] = 0
    return loc_state

def validate_relationships(state)->Command[Literal["extract_graph","extract_relationships"]]:
    node_name = "validate_relationships"
    loc_state = state

    special_instructions = f"""Guidelines:\n    - Strictly avoid extracting relationships of citation authors. They will be processed by a dedicated pipeline\n  - If the given text unit contain only citations, ignore them altogether\n"""
    
    logger = loc_state.get('metadata', {}).get('logger', None)
    llm = loc_state.get('metadata', {}).get('llm', None)
    parent_trace_id = loc_state.get('metadata', {}).get('trace_id', None)
    priming_flag = loc_state.get('metadata', {}).get('priming_flag', False)

    logger.info(f"\n---NODE: {node_name}---iteration={loc_state['relations_iter_counter']}---")
    
    loc_state['relations_iter_counter'] += 1
    
    extracted_entities = loc_state['entities']
    extracted_entities_names = [entity["name"] for entity in extracted_entities["entities"]]
    extracted_relationships = loc_state['relationships']
    relations_iter_counter = loc_state['relations_iter_counter']
    max_iterations = 4
    
    content = loc_state['text_chunks'][loc_state['chunk_index']]  
    input_vars = {"extracted_relationships":extracted_relationships,"extracted_entities_names":extracted_entities_names,
                            "content":content,"relations_iter_counter":relations_iter_counter,"max_iterations":max_iterations,
                            "special_instructions":special_instructions}
    
    if priming_flag:
        priming_summary=loc_state['summary']
        input_vars |= {"priming_summary":priming_summary}
    
    prompt = prompt_dictionary['MissingRelationships']["system"].text
    
    relation_validation_out = heimdall_graph(llm=llm,
                                             prompt=prompt,
                                             input_vars=input_vars,
                                             pydantic_object=EntityValidationFeedback)
    
    loc_state['relations_validation_feedback'] = relation_validation_out
    if(relation_validation_out['loop_required']):
        goto = "extract_relationships"
        logger.info(f"\n---NODE: {node_name}---INFO: Looping back to extract relationships again---\nReason: {relation_validation_out['reason_to_loop']}")    
    else: 
        goto = "extract_graph"
        logger.info(f"\n---NODE: {node_name}---INFO: Going to graph final graph building---\nReason: {relation_validation_out['reason_to_loop']}")    
    
    return Command(update=loc_state,goto=goto)

# ---- Utility Functions ----

def _update_relationships(global_relationships, new_relationships,logger):
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
