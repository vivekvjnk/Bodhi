from pydantic import BaseModel, Field, ConfigDict
from typing import List,Optional,TypedDict,Dict,  Any

import networkx as nx

from Sanchayam import Sanchayam

#---------------Bodhi Graph Extraction-Begin-------------#
class Relationship(BaseModel):
    source_entity: str = Field(..., description="Name of the source entity.")
    target_entity: str = Field(..., description="Name of the target entity.")
    description: str = Field(..., description="Explanation of the relationship between the source and target entity.")
    strength: float = Field(..., description="A numeric score indicating the strength of the relationship.", ge=0, le=10)

class RelationshipState(BaseModel):
    source_entity: str = Field(..., description="Name of the source entity.")
    target_entity: str = Field(..., description="Name of the target entity.")
    description: str = Field(..., description="Explanation of the relationship between the source and target entity.")
    strength: float = Field(..., description="A numeric score indicating the strength of the relationship.", ge=0, le=10)
    source_chunk_index: int = Field(..., description="Index of the text chunk from which the relationship was extracted.")

class RelationshipExtractionOutput(BaseModel):
    relationships: List[Relationship] = Field(..., description="A list of all relationships extracted from the text.")

class EntityValidationFeedback(BaseModel):
    reason_to_loop: str = Field(..., description="Reason for the decision to loop")  # List of reasons why a loop-back is necessary
    loop_required: bool = Field(..., description="Decision to loop or not")  # Boolean indicating if looping is needed
    # additional_comments: Optional[str] = None  # Optional additional feedback or context


class Entity(BaseModel):
    name: str = Field(..., description="Capitalized name of the entity.")
    type: str = Field(..., description="Entity type (must align with the provided or introduced types).")
    description: str = Field(..., description="Comprehensive description of the entity.")

class EntityState(BaseModel):
    name: str = Field(..., description="Capitalized name of the entity.")
    type: str = Field(..., description="Entity type (must align with the provided or introduced types).")
    description: str = Field(..., description="Comprehensive description of the entity.")
    source_chunk_index: int = Field(..., description="Index of the text chunk from which the entity was extracted.")

class EntityExtractionOutput(BaseModel):
    entities: List[Entity] = Field(..., description="A list of all entities extracted from the text.")
#---------------Bodhi Graph Extraction-End---------------#

#---------------Bodhi Graph metadata-Begin-------------#
class BodhiGraphMetadata(TypedDict):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    text_units: List[str] = Field(..., description="List of text units (chunks) from which the graph is constructed.")
    llm_logger: Any = Field(...,description="Logger instance for LLM")
    logger: Any = Field(..., description="Logger instance for logging messages.")
    llm: Any = Field(..., description="LLM instance used for processing.")
    thinking_llm: Any = Field(..., description="Thinking LLM instance used for processing.")
    storage: Sanchayam = Field(..., description="Storage instance for persisting data.")
    trace_id: hex = Field(..., description="Unique identifier for langfuse llm tracing during the execution of the graph extraction process.")
    thread_id: hex = Field(..., description="Unique identifier for graph extraction thread, used for tracking the execution context.")
#---------------Bodhi Graph metadata-End-------------#

# text_units=text_chunks, logger=logger, llm=llm, storage=storage, trace_id=parent_trace_id

#---------------Bodhi state information-Begin-------------#
class BodhiState(TypedDict):
    source_path : str = Field("Path to input text file") 
    relationships: List[RelationshipState] = Field("Dictionary with list of relationships")
    entities : List[EntityState] = Field("Dictionary with list of entities")
    entity_types: Dict[str,Any] = Field("List of entity types")
    entity_iter_counter: int = Field("Iteration counter for EntityExtraction-Validation loop")
    relations_iter_counter: int = Field("Iteration counter for RelationExtraction-Validation loop") 
    entity_validation_feedback: EntityValidationFeedback = Field("Validation feedback for extracted entities")
    relations_validation_feedback: EntityValidationFeedback = Field("Validation feedback for extracted relations")
    text_chunks : List[str] = Field("List of text chunks extracted from document")
    number_of_chunks: int = Field("Total number of text chunks to be processed")
    chunk_index : int = Field("Current chunk index")
    global_graph:nx.Graph = Field("Global graph of the document") # Graph embedding, Leiden Clustering etc
    metadata: BodhiGraphMetadata = Field("Metadata for the Bodhi graph extraction process")
    summary: str = Field("Priming summary about the source document")

    
class BodhiInputState(TypedDict):
    source_path : str = Field("Path to input text file") 
#---------------Bodhi state information-End---------------#
