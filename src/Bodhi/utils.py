import os, logging, inspect, yaml, uuid
from sentence_transformers import SentenceTransformer, util
from scipy.spatial.distance import cosine
import numpy as np

from langchain_ollama import OllamaLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from transformers import AutoTokenizer

_GLOBAL_SEED = 0

def set_global_seed(seed):
    # Placeholder for setting global seed
    global _GLOBAL_SEED
    _GLOBAL_SEED = seed
    # Apply the seed to standard libraries here
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    print(f"Global seed set to: {seed}")

def get_global_seed():
    """
    Returns the currently set global seed.
    """
    return _GLOBAL_SEED


def get_llm_from_config(config,model_type="fast",temperature=0):
    inference_engine = config["inference_engine"]
    seed = get_global_seed()
    
    if model_type == "fast":
        f_model = config["fast_model"]
    elif model_type == "thinking":
        f_model = config["thinking_model"]
    else:
        f_model = config["general_model"]

    if inference_engine.lower() == "ollama":
        return OllamaLLM(temperature=temperature, model=f_model,seed=seed)
    elif inference_engine.lower() == "googlegenerativeai":
        os.environ["GOOGLE_API_KEY"] = config["google_api_key"]
        return ChatGoogleGenerativeAI(model=f_model, temperature=temperature)
    elif inference_engine.lower() == "vertexai":
        return ChatVertexAI(model=f_model, temperature=temperature,seed=seed)
    else:
        raise ValueError(f"Unsupported inference_engine: {inference_engine}")


#---------------Token counter-Begin-------------#
def estimate_tokens_hf(text: str, model_name: str = "Qwen/Qwen2.5-Coder-14B") -> int:
    """
    Estimate the number of tokens using Hugging Face tokenizers.

    Args:
        text (str): The input text.
        model_name (str): The Hugging Face model name or path.
    
    Returns:
        int: The estimated number of tokens.
    """    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokens = tokenizer(text, return_tensors="pt")["input_ids"]
        return tokens.size(1)  # Token count
    except Exception as e:
        raise RuntimeError(f"Error loading Hugging Face tokenizer for {model_name}: {e}\nactual content: {type(text)}")
    
def _estimate_tokens_spm(text: str, model_path: str) -> int:
    """
    Estimate tokens using SentencePiece tokenizer.

    Args:
        text (str): The input text.
        model_path (str): Path to the SentencePiece model file (.model).

    Returns:
        int: Estimated token count.
    """
    import sentencepiece as spm
    try:
        sp = spm.SentencePieceProcessor(model_file=model_path)
        tokens = sp.encode(text, out_type=str)
        return len(tokens)
    except Exception as e:
        raise RuntimeError(f"Error loading SentencePiece model from {model_path}: {e}")
    
def _estimate_tokens_tiktoken(text: str, model: str = "gpt-4",fallback: str = "cl100k_base") -> int:
    """
    Estimate the number of tokens in a text string using the tiktoken library.

    Args:
        text (str): The input text to estimate token count for.
        model (str): The model name to determine the tokenizer (default: "gpt-4").
    
    Returns:
        int: The estimated number of tokens.
    """
    import tiktoken
    try:
        tokenizer = tiktoken.encoding_for_model(model)
    except KeyError:
        # Use fallback model
        tokenizer = tiktoken.get_encoding(fallback)
    return len(tokenizer.encode(text))
    

def estimate_tokens(text: str, method: str = "hf", **kwargs) -> int:
    """
    Estimates the number of tokens in a given text using a specified tokenization method.

    This function acts as a wrapper for multiple token estimation methods and dynamically selects the appropriate method based on the `method` parameter. It logs the token estimation process, including the chosen method and the token count. If the token count is zero, a warning is logged.

    Args:
        text (str): 
            The input text for which the token count is to be estimated.
        method (str, optional): 
            The tokenization method to use. Defaults to `"hf"`. Supported methods are:
            - `"hf"`: Hugging Face tokenization.
            - `"spm"`: SentencePiece tokenization.
            - `"tiktoken"`: OpenAI's TikToken tokenization.
        **kwargs: 
            Additional keyword arguments passed to the underlying tokenization method for customization.

    Returns:
        int: 
            The estimated number of tokens in the input text.

    Raises:
        ValueError: 
            If an unsupported tokenization method is specified.

    Workflow:
        1. Log the selected tokenization method.
        2. Use the specified method to estimate the number of tokens:
            - If `method` is `"hf"`, call `estimate_tokens_hf`.
            - If `method` is `"spm"`, call `estimate_tokens_spm`.
            - If `method` is `"tiktoken"`, call `estimate_tokens_tiktoken`.
        3. Log a warning if the estimated token count is zero.
        4. Log the final token count and return it.

    Sub-functions:
        - `estimate_tokens_hf(text: str, **kwargs) -> int`: Estimates tokens using Hugging Face tokenization.
        - `estimate_tokens_spm(text: str, **kwargs) -> int`: Estimates tokens using SentencePiece tokenization.
        - `estimate_tokens_tiktoken(text: str, **kwargs) -> int`: Estimates tokens using OpenAI's TikToken.

    Example Usage:
        ```python
        text = "This is a sample text for token estimation."
        
        # Using Hugging Face tokenization
        token_count_hf = estimate_tokens(text, method="hf")
        
        # Using SentencePiece tokenization
        token_count_spm = estimate_tokens(text, method="spm")
        
        # Using TikToken tokenization
        token_count_tiktoken = estimate_tokens(text, method="tiktoken")
        ```

    Example Output:
        For the input text `"This is a sample text for token estimation."`, the token count may vary based on the method:
        - Hugging Face: 10 tokens
        - SentencePiece: 9 tokens
        - TikToken: 11 tokens

    Logging:
        - Logs the selected tokenization method at the beginning.
        - Logs a warning if the token count is zero, along with the input text.
        - Logs the estimated token count.

    Notes:
        - The function assumes that the tokenization methods `estimate_tokens_hf`, `estimate_tokens_spm`, and `estimate_tokens_tiktoken` are implemented and available in the codebase.
        - The choice of tokenization method should align with the downstream processing system.

    Limitations:
        - The token count may differ across methods due to variations in tokenization algorithms.
        - If the input text is empty or poorly formatted, the token count may be zero, triggering a warning.
    """
    logging.info(f"{inspect.stack()[1].filename}:{inspect.stack()[1].lineno}:Estimating tokens using {method} method.")
    if method == "hf":
        token_count = estimate_tokens_hf(text, **kwargs)
    elif method == "spm":
        token_count = _estimate_tokens_spm(text, **kwargs)
    elif method == "tiktoken":
        token_count = _estimate_tokens_tiktoken(text, **kwargs)
    else:
        raise ValueError(f"Unsupported tokenization method: {method}")
    if(token_count==0):
        logging.warning(f"Zero token count for following chunk:\n{text}\n")
    logging.info(f"Token count: {token_count}")
    return token_count

def estimate_tokens_hf_batch(text_list: list, model_name: str = "Qwen/Qwen2.5-Coder-14B") -> dict:
    """
    Estimate the number of tokens for each string in a list using Hugging Face tokenizers (batch mode).

    Args:
        text_list (list): List of input strings.
        model_name (str): The Hugging Face model name or path.

    Returns:
        dict: Dictionary mapping each string to its token count.
    """
    if type(text_list) == str:
        text_list = [text_list]
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        # Use batch_encode_plus for consistent output
        encodings = tokenizer.batch_encode_plus(text_list, add_special_tokens=True)
        input_ids = encodings["input_ids"]
        token_counts = {}
        for text, ids in zip(text_list, input_ids):
            token_counts[text] = len(ids)
        logging.info(f"Batch token estimation (hf) complete for {len(text_list)} strings.")
        return token_counts
    except Exception as e:
        raise e

#---------------Token counter-End-------------#

#---------------Semantic similarity check class-Begin-------------#

class SemanticSimilarity:
    """
    A class for computing semantic similarity between sentences using a fine-tuned
    SentenceTransformer model. Includes caching to avoid redundant computations.
    """

    def __init__(self, model_path: str, embedding_cache: dict = None,device="cpu"):
        """
        Initializes the SemanticSimilarity class with a fine-tuned model and an optional cache.

        Args:
            model_path (str): Path to the fine-tuned SentenceTransformer model.
            embedding_cache (dict, optional): A dictionary to store sentence embeddings.
        """
        self.model = SentenceTransformer(model_path,local_files_only=True)
        self.embedding_cache = embedding_cache if embedding_cache is not None else {}
        self.device = device

    def compute_similarity(self, sentence1: str, sentence2: str) -> float:
        """
        Computes the cosine similarity between two sentences.

        Args:
            sentence1 (str): The first sentence.
            sentence2 (str): The second sentence.

        Returns:
            float: A similarity score between -1 and 1, where 1 indicates identical sentences.
        """
        embedding1 = self.get_or_compute_embedding(sentence1)
        embedding2 = self.get_or_compute_embedding(sentence2)
        
        return 1 - cosine(embedding1, embedding2)

    def sentence_to_embedding(self, sentence: str) -> np.ndarray:
        """
        Converts a single sentence into its embedding representation, using cache if available.

        Args:
            sentence (str): The sentence to be embedded.

        Returns:
            np.ndarray: The sentence embedding.
        """
        if sentence in self.embedding_cache:
            return self.embedding_cache[sentence]
        
        embedding = self.model.encode(sentence, convert_to_numpy=True)
        self.embedding_cache[sentence] = embedding
        return embedding

    def batch_sentence_to_embeddings(self, sentences: list) -> np.ndarray:
        """
        Converts a batch of sentences into their embeddings.

        Args:
            sentences (list): List of sentences.

        Returns:
            np.ndarray: Matrix of embeddings.
        """
        return self.model.encode(sentences, convert_to_numpy=True)

    def batch_semantic_similarity(self, new_sentence: str, existing_sentences: list) -> list:
        """
        Computes the semantic similarity between a new sentence and a batch of existing sentences.

        Args:
            new_sentence (str): The sentence to compare.
            existing_sentences (list): List of sentences to compare against.

        Returns:
            list: List of similarity scores.
        """
        new_embedding = self.get_or_compute_embedding(new_sentence)
        existing_embeddings = self.batch_sentence_to_embeddings(existing_sentences)

        similarities = 1 - np.array([cosine(new_embedding, emb) for emb in existing_embeddings])
        return similarities.tolist()

    def get_or_compute_embedding(self, sentence: str) -> np.ndarray:
        """
        Retrieves a cached embedding or computes it if not available.

        Args:
            sentence (str): The sentence to get an embedding for.

        Returns:
            np.ndarray: The sentence embedding.
        """
        if sentence in self.embedding_cache:
            return self.embedding_cache[sentence]
        return self.sentence_to_embedding(sentence)

    def batch_to_batch_semantic_similarity(self, sentences_1: list, sentences_2: list) -> np.ndarray:
        """
        Computes the semantic similarity between all pairs from two batches of sentences.

        Args:
            sentences_1 (list): First list of sentences.
            sentences_2 (list): Second list of sentences.

        Returns:
            np.ndarray: Matrix of similarity scores with shape [len(sentences_1), len(sentences_2)]
        """
        # Encode both batches (returned as torch tensors on self.device)
        embeddings_1 = self.model.encode(sentences_1, convert_to_tensor=True, device=self.device)
        embeddings_2 = self.model.encode(sentences_2, convert_to_tensor=True, device=self.device)

        # Compute cosine similarity matrix [len(sentences_1), len(sentences_2)]
        similarity_matrix = util.pytorch_cos_sim(embeddings_1, embeddings_2)

        return similarity_matrix.cpu().numpy()
#---------------Semantic similarity check class-End-------------#


# Function to calculate harmonic mean
def harmonic_mean(values):
    # Ensure values are positive for harmonic mean calculation
    positive_values = [v for v in values if v > 0]
    if not positive_values:
        return 0.0 # Or handle as an error, depending on desired behavior
    
    # Calculate the sum of reciprocals
    sum_of_reciprocals = sum(1 / v for v in positive_values)
    
    # Avoid division by zero if sum_of_reciprocals is 0 (though unlikely with positive_values check)
    if sum_of_reciprocals == 0:
        return 0.0
    return len(positive_values) / sum_of_reciprocals


#---------------Custom yaml loader for tuples-Begin-------------#
# Custom constructor to handle the !!python/tuple tag
def tuple_constructor(loader, node):
    # Extract values from ScalarNode objects and create a tuple
    return tuple([loader.construct_scalar(n) for n in node.value])

# Register the custom constructor with PyYAML
yaml.add_constructor('tag:yaml.org,2002:python/tuple', tuple_constructor,yaml.FullLoader)
#---------------Custom yaml loader for tuples-End---------------#


#---------------Convert multilevel dictionaries of string to string and save as makrdown-Begin-------------#
def format_dict_to_markdown(data, level=1, ign_keys=None):
    """
    Recursively formats a nested dictionary into a markdown string.
    If `ign_keys` is provided, ignore those keys from ouput
    """
    markdown = ""
    for key, value in data.items():
        if ign_keys is None or key not in ign_keys:
            if isinstance(value, dict):
                markdown += f"{'#' * level} {key}\n\n"
                markdown += format_dict_to_markdown(value, level + 1, ign_keys)
            else:
                markdown += f"{'#' * level} {key}\n\n{value}\n\n"
    return markdown
#---------------Convert multilevel dictionaries of string to string and save as makrdown-End---------------#

def create_unique_trace_id():
    """Generate a unique trace ID."""
    return str(uuid.uuid4())
