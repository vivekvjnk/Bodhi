from langgraph.graph import StateGraph, END
from Bodhi.utils import get_llm_from_config, estimate_tokens, estimate_tokens_hf_batch

import yaml
from omegaconf import DictConfig
from pydantic import BaseModel,Field
from typing import Literal,List,Any,Dict


from heimdall import heimdall_graph

# -----------------
# State definition
# -----------------
class EntityState(dict):
    # Keys we will pass around
    full_text: str
    entities: list[str]
    context_limit: int
    classified: list[dict]
    entity_groups: list[list[str]]
    special_instructions:str
    output_path:str
    config: DictConfig
    helpers:Dict[str,Any]
# -----------------
# Node: Split entities into groups
# -----------------
def split_entities(state: EntityState):
    full_text = state["full_text"]
    entities = state["entities"]
    context_limit = state.get("context_limit", 10000)
    logger = state["helpers"]["logger"]

    text_tokens = estimate_tokens(full_text)
    instructions_tokens = 500  # fixed estimate for prompt instructions

    budget_for_entities = context_limit - (text_tokens + instructions_tokens)
    if budget_for_entities < 0:
        budget_for_entities = 0

    # dynamically compute tokens per entity
    entity_token_count = estimate_tokens_hf_batch(entities)
    # entity_token_lengths = [estimate_tokens(e) for e in entities]
    entity_token_lengths = list(entity_token_count.values())
    avg_entity_tokens = max(1, sum(entity_token_lengths) // len(entity_token_lengths)) if entities else 1

    max_entities = max(1, budget_for_entities // avg_entity_tokens)

    groups = [entities[i:i+max_entities] for i in range(0, len(entities), max_entities)]
    
    logger.info(
        f"first_5_entities: {entities[:5]}"
        f"split_entities: text_tokens={text_tokens}, instructions_tokens={instructions_tokens}, "
        f"budget_for_entities={budget_for_entities}, number_of_entities={len(entity_token_lengths)}, "
        f"avg_entity_tokens={avg_entity_tokens}, max_entities={max_entities}, "
        f"num_groups={len(groups)}, entities_per_group={[len(g) for g in groups]}"
    )
    return {**state, "entity_groups": groups}



def classify_entities(state: EntityState):

    # -----------------
    # Node: LLM classification
    # -----------------
    class ClassifiedEntity(BaseModel):
        entity:str = Field(...,description="Name of the entity")
        type:Literal["METHOD","DOMAIN"] = Field(...,description="METHOD if AI related general entity. DOMAIN if highly specific to the source text")

    class ClassificationOutput(BaseModel):
        entities:List[ClassifiedEntity] = Field(...,description="List of classified entities")
    logger = state["helpers"]["logger"]
    prompt_template = """You are an expert in NLP entity classification.
    Source Text:
    -------------------
    {full_text}
    -------------------

    Entities to classify:
    -------------------
    {entities}
    
    {special_instructions}
    -------------------
    Source text is a research publication from AI/ML domain. Objective is to classify listed entities into two classes based on their domain specificity. Here by the word domain, we mean the context specific to the research publication. Entities which are general across AI/ML research are considered as METHOD type. Entities highly specific to the research paper, considering AI/ML domain belong to DOMAIN type.
    Classify each entity into one of the categories: METHOD, DOMAIN.
    Definitions:
    - METHOD: AI related generic entities.
    - DOMAIN: Domain specific entities. Highly specific to the Source Text.

    {format_instructions}
    """
    llm = get_llm_from_config(config=state["config"],model_type="thinking")
    results = []
    special_instructions = state["special_instructions"]
    full_text = state["full_text"]
    for i,group in enumerate(state["entity_groups"]):
        entities = "\n".join(group)
        input_vars = {"full_text":full_text,"entities":entities,"special_instructions":special_instructions}
        
        resp = heimdall_graph(pydantic_object=ClassificationOutput,input_vars=input_vars,llm=llm,prompt=prompt_template)
        logger.info(f"Group {i} of {len(state["entity_groups"])}")
        
        results.extend(resp["entities"])

    
    return {**state, "classified": results}

# -----------------
# Node: Merge results
# -----------------

def merge_results(state: EntityState):
    classified = state["classified"]
    method_entities = [c["entity"] for c in classified if c["type"] == "METHOD"]
    domain_entities = [c["entity"] for c in classified if c["type"] == "DOMAIN"]
    unclassified = [c["entity"] for c in classified if c["type"] == "OTHER"]
    results = {"method_entities": method_entities,
        "domain_entities": domain_entities,
        "unclassified": unclassified,}
    with open(state["output_path"],"w") as f:
        yaml.dump(results,f)

    return {
        **state,
        "method_entities": method_entities,
        "domain_entities": domain_entities,
        "unclassified": unclassified,
    }

# -----------------
# Build Graph
# -----------------
def build_classification_graph():
    workflow = StateGraph(EntityState)
    workflow.add_node("split", split_entities)
    workflow.add_node("classify", classify_entities)
    workflow.add_node("merge", merge_results)

    workflow.set_entry_point("split")
    workflow.add_edge("split", "classify")
    workflow.add_edge("classify", "merge")
    workflow.add_edge("merge", END)

    entity_classifier_graph = workflow.compile()
    return entity_classifier_graph