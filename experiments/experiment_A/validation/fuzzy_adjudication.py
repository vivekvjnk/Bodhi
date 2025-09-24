"""
bodhi_fuzzy_adjudicator.py

Fuzzy matching + LLM adjudication pipeline for comparing a system extraction (Bodhi)
against a gold standard (SciER or other). Implements the three-stage workflow:

Stage 1: Normalize & exact match
Stage 2: Fuzzy pattern matching (difflib) with numeric-aware comparison
Stage 3: LLM adjudication with token-budgeted prompts and caching

Usage:
- Provide `gold_entities` and `bodhi_entities` as lists of strings (optionally with metadata).
- Provide an `llm_callable(prompt: str) -> str` function (sync) and optionally a tokenizer function.
"""

from typing import List, Tuple, Dict, Callable, Any, Optional
import difflib
import re
import logging
import json
import os
import pickle
import hashlib
import time

validation_path = "Bodhi/experiments/prompt_engineering/experiment_A/validation"
logger = logging.getLogger(__name__)

# -------------------------
# CONFIG / DEFAULTS
# -------------------------
CACHE = False
DEFAULT_FUZZY_THRESHOLD = 0.85  # similarity threshold for difflib (0..1)
CACHE_DIR = f"{validation_path}/fuzzy_adjudication_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# -------------------------
# Tokenizer utilities
# -------------------------
def simple_tokenize(text: str) -> List[str]:
    tokens = re.findall(r"\w+|[^\s\w]", text)
    logger.debug(f"Tokenized text: {text[:30]}... -> {tokens[:10]}...")
    return tokens

def token_count(text: str, tokenizer: Optional[Callable[[str], List[str]]] = None) -> int:
    if tokenizer:
        try:
            count = tokenizer(text)
            logger.debug(f"Token count using custom tokenizer for text: {text[:30]}... -> {count}")
            return count[text]
        except Exception as e:
            logger.warning(f"Custom tokenizer failed for text: {text[:30]}... Error: {e}")
    count = len(simple_tokenize(text))
    logger.debug(f"Token count using fallback tokenizer for text: {text[:30]}... -> {count}")
    return count

def batch_token_count(
    texts: List[str],
    tokenizer: Optional[Callable[[List[str]], List[int]]] = None
) -> Dict[str, int]:
    """
    Counts tokens for a list of strings using a batch tokenizer callback.
    Returns a dict mapping each string to its token count.
    """
    result = {}
    if tokenizer:
        try:
            counts = tokenizer(texts)
            return counts
        except Exception as e:
            raise e
            # logger.warning(f"Batch tokenizer failed: {e}")
            # counts = [len(simple_tokenize(t)) for t in texts]
    else:
        counts = [len(simple_tokenize(t)) for t in texts]
    for text, count in zip(texts, counts):
        logger.debug(f"Token count for text: {text[:30]}... -> {count}")
        result[text] = count
    return result
# -------------------------
# Normalization utilities
# -------------------------
NUMERIC_RE = re.compile(r"\d+(\.\d+)?")

def normalize_entity(e: str) -> str:
    if not isinstance(e, str):
        e = str(e)
    e = re.sub(r'([a-zA-Z])-\s*\n\s*([a-zA-Z])', r'\1\2', e)
    e = e.replace("\n", " ").strip()
    e = re.sub(r'\s+', ' ', e)
    e = e.strip(" .,;:()[]\"'`")
    e = re.sub(r'(?<!\d)-(?=[^\d])|(?<=[^\d])-(?!\d)', '', e)
    e_low = e.lower()
    e_low = re.sub(r'\s+', ' ', e_low)
    logger.debug(f"Normalized entity: '{e}' -> '{e_low}'")
    return e_low

def normalize_list(entities: List[str]) -> Dict[str, str]:
    norm_to_orig = {}
    for ent in entities:
        n = normalize_entity(ent)
        if n not in norm_to_orig:
            norm_to_orig[n] = ent
    logger.debug(f"Normalized entity list: {len(entities)} entities -> {len(norm_to_orig)} normalized")
    return norm_to_orig

# -------------------------
# Stage 1: Exact matching
# -------------------------
def stage1_exact_match(gold: List[str], bodhi: List[str]) -> Tuple[Dict[str,str], List[str]]:
    logger.info("Stage 1: Performing exact match between gold and bodhi entities.")
    gold_map = normalize_list(gold)
    bodhi_map = normalize_list(bodhi)
    matched = {}
    for nb, ob in bodhi_map.items():
        if nb in gold_map:
            matched[nb] = gold_map[nb]
    bodhi_unmatched = [bodhi_map[n] for n in bodhi_map if n not in matched]
    logger.info(f"Stage 1: Found {len(matched)} exact matches, {len(bodhi_unmatched)} unmatched bodhi entities.")
    return matched, bodhi_unmatched

# -------------------------
# Stage 2: Fuzzy matching with numeric-aware similarity
# -------------------------
def numeric_aware_similarity(a: str, b: str) -> float:
    a_n = normalize_entity(a)
    b_n = normalize_entity(b)
    base_ratio = difflib.SequenceMatcher(None, a_n, b_n).ratio()
    a_nums = NUMERIC_RE.findall(a_n)
    b_nums = NUMERIC_RE.findall(b_n)
    if a_nums or b_nums:
        if a_nums != b_nums:
            penalty = 0.15
            base_ratio = max(0.0, base_ratio - penalty)
            logger.debug(f"Numeric mismatch penalty applied: '{a}' vs '{b}'")
    logger.debug(f"Similarity between '{a}' and '{b}': {base_ratio}")
    return base_ratio

def stage2_fuzzy_match(gold: List[str],
                       bodhi_unmatched: List[str],
                       threshold: float = DEFAULT_FUZZY_THRESHOLD) -> Tuple[Dict[str,Tuple[str,float]], List[str], List[Tuple[str,str,float]]]:
    logger.info("Stage 2: Performing fuzzy matching for unmatched bodhi entities.")
    gold_map = normalize_list(gold)
    reversed_gold = list(gold_map.values())
    matches = {}
    candidate_pairs = []
    remaining = []
    for b in bodhi_unmatched:
        best_score = 0.0
        best_gold = None
        for g in reversed_gold:
            score = numeric_aware_similarity(b, g)
            candidate_pairs.append((b, g, score))
            if score > best_score:
                best_score = score
                best_gold = g
        if best_score >= threshold:
            matches[b] = (best_gold, best_score)
            logger.debug(f"Fuzzy match: '{b}' -> '{best_gold}' (score={best_score:.3f})")
        else:
            remaining.append(b)
            logger.debug(f"No fuzzy match for '{b}' (best score={best_score:.3f})")
    candidate_pairs.sort(key=lambda x: x[2], reverse=True)
    logger.info(f"Stage 2: Found {len(matches)} fuzzy matches, {len(remaining)} unmatched bodhi entities remain.")
    logger.debug(f"Candidate pair list\n---------\n{candidate_pairs}")
    return matches, remaining, candidate_pairs

# -------------------------
# Caching for LLM adjudication
# -------------------------
def make_cache_key(prefix: str, payload: Any) -> str:
    j = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    h = hashlib.sha256(j).hexdigest()
    key = f"{prefix}_{h}.pkl"
    logger.debug(f"Generated cache key: {key}")
    return key

def cache_write(key: str, obj: Any):
    path = os.path.join(CACHE_DIR, key)
    try:
        with open(path, "wb") as f:
            pickle.dump(obj, f)
        logger.debug(f"Cache write: {path}")
    except Exception as e:
        logger.error(f"Failed to write cache at {path}: {e}")
    

def cache_read(key: str) -> Optional[Any]:
    path = os.path.join(CACHE_DIR, key)
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                logger.debug(f"Cache hit: {path}")
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to read cache at {path}: {e}")
    else:
        logger.debug(f"Cache miss: {path}")
    return None

# -------------------------
# Stage 3: LLM adjudication
# -------------------------
def split_into_chunks(items: List[str], tokenizer: Callable[[str], List[str]],
                      token_budget: int, token_format_instructions: int) -> List[List[str]]:
    chunks = []
    current_chunk = []
    current_tokens = 0
    per_chunk_limit = token_budget - token_format_instructions
    if per_chunk_limit <= 0:
        logger.error("Token budget too small relative to format instruction size.")
        raise ValueError("token_budget too small relative to format instruction size")
    tokenized_items = batch_token_count(texts=items,tokenizer=tokenizer)
    logger.info(f"Tokenized items: {tokenized_items}")
    for it,tcount in tokenized_items.items():
        if current_tokens + tcount <= per_chunk_limit or not current_chunk:
            current_chunk.append(it)
            current_tokens += tcount
        else:
            chunks.append(current_chunk)
            current_chunk = [it]
            current_tokens = tcount
    if current_chunk:
        chunks.append(current_chunk)
    logger.debug(f"Split {len(items)} items into {len(chunks)} chunks for token budget {token_budget}.")
    return chunks

def build_stage3_prompt(gold_chunk: List[str], bodhi_list: List[str],
                        format_instructions: str) -> str:
    prompt_lines = []
    prompt_lines.append("You are an expert adjudicator. Given a gold list of canonical entities and a list of extracted entities from a system, identify which gold entity best matches each extracted entity. If none match, reply NO_MATCH.")
    prompt_lines.append("")
    prompt_lines.append("GOLD LIST (canonical):")
    for i, g in enumerate(gold_chunk, 1):
        prompt_lines.append(f"{i}. {g}")
    prompt_lines.append("")
    prompt_lines.append("EXTRACTED (bodhi) LIST:")
    for j, b in enumerate(bodhi_list, 1):
        prompt_lines.append(f"{j}. {b}")
    prompt_lines.append("")
    prompt_lines.append("FORMAT INSTRUCTIONS:")
    prompt_lines.append(format_instructions)
    prompt = "\n".join(prompt_lines)
    logger.debug(f"Built stage 3 prompt with {len(gold_chunk)} gold and {len(bodhi_list)} bodhi entities.")
    return prompt

def stage3_llm_adjudicate(gold: List[str],
                          bodhi_remaining: List[str],
                          llm_callable: Callable[[str], str],
                          tokenizer: Optional[Callable[[str], List[str]]] = None,
                          usable_context_limit: int = 4000,
                          format_instructions: str = "Return JSON mapping: {\"extracted_entity\": \"matched_gold_or_NO_MATCH\"}."
                          ) -> Dict[str,str]:
    logger.info("Stage 3: Performing LLM adjudication for remaining unmatched bodhi entities.")
    token_fi = token_count(format_instructions, tokenizer)
    UCL_half = usable_context_limit // 2
    # token_budget_per_prompt = usable_context_limit
    # gold_tokens_total = sum(token_count(g, tokenizer) for g in gold)
    # per_gold_chunk_limit = max(10, UCL_half - token_fi)
    gold_chunks = split_into_chunks(gold, tokenizer, UCL_half, token_fi)
    bodhi_token_total = sum(values for key,values in batch_token_count(texts=bodhi_remaining,tokenizer=tokenizer).items())
    if bodhi_token_total > UCL_half:
        bodhi_chunks = split_into_chunks(bodhi_remaining, tokenizer, UCL_half, token_fi)
    else:
        bodhi_chunks = [bodhi_remaining]

    adjudicated_map = {}

    for gchunk in gold_chunks:
        for bchunk in bodhi_chunks:
            payload_cache_key = make_cache_key("stage3", {"gchunk": gchunk, "bchunk": bchunk, "fi": format_instructions})
            if CACHE:
                cached = cache_read(payload_cache_key)
                if cached is not None:
                    try:
                        res_map = cached
                        adjudicated_map.update(res_map)
                        logger.info(f"Cache hit for LLM adjudication chunk: {payload_cache_key}")
                        continue
                    except Exception as e:
                        logger.error(f"Failed to use cached result for {payload_cache_key}: {e}")
            prompt = build_stage3_prompt(gchunk, bchunk, format_instructions)
            logger.info(f"Invoking LLM for adjudication chunk: {payload_cache_key}")
            try:
                raw = llm_callable.invoke([("human",prompt)])
            except Exception as e:
                logger.error(f"LLM invocation failed for chunk {payload_cache_key}: {e}")
                continue
            parsed = {}
            try:
                parsed = json.loads(raw.content)
            except Exception:
                m = re.search(r'\{.*\}', raw.content, flags=re.S)
                if m:
                    try:
                        parsed = json.loads(m.group(0))
                    except Exception as e:
                        logger.error(f"Failed to parse JSON from LLM output for chunk {payload_cache_key}: {e}")
                        parsed = {}
            normalized_parsed = {}
            for k, v in parsed.items():
                k_norm = k.strip()
                v_norm = v.strip() if isinstance(v, str) else v
                normalized_parsed[k_norm] = v_norm
            adjudicated_map.update(normalized_parsed)
            if CACHE:
                try:
                    cache_write(payload_cache_key, normalized_parsed)
                except Exception as e:
                    logger.error(f"Failed to cache LLM adjudication result for {payload_cache_key}: {e}")
            time.sleep(0.2)
    logger.info(f"Stage 3: LLM adjudication completed for {len(adjudicated_map)} entities.")
    return adjudicated_map

# -------------------------
# Second LLM cycle: importance scoring of novel extractions
# -------------------------
def assess_novel_entities_with_text(novel_entities: List[str],
                                    source_text: str,
                                    llm_callable: Callable[[str], str],
                                    tokenizer: Optional[Callable[[str], List[str]]] = None,
                                    usable_context_limit: int = 10000,
                                    format_instructions: str = "Return JSON mapping: {\"entity\": {\"score\": 0..1, \"reason\": \"short explanation\"}}"
                                    ) -> Dict[str, Dict[str, Any]]:
    if not novel_entities:
        logger.info("No novel entities to assess.")
        return {}
    token_fi = token_count(format_instructions, tokenizer)
    UCL_half = usable_context_limit // 2
    novel_chunks = split_into_chunks(novel_entities, tokenizer, UCL_half, token_fi)
    results = {}
    for chunk in novel_chunks:
        cache_key = make_cache_key("novel_assess", {"chunk": chunk, "text_hash": hashlib.sha256(source_text.encode()).hexdigest()})
        if CACHE:
            cached = cache_read(cache_key)
            if cached:
                logger.info(f"Cache hit for novel entity assessment chunk: {cache_key}")
                results.update(cached)
                continue
        prompt_lines = [
            "You are an expert AI evaluator for scientific knowledge graphs. Your task is to rate extracted entities on a **0.0 to 1.0 scale** based on their relevance to the source text, factual accuracy and boundary precision. Assess each entity's validity, even if it is not in a ground truth set.",
            "",
            """
**Boundary Precision Guide:**

  * **Perfect:** The exact span of text is captured (e.g., `support vector machine`).
  * **Minor Error:** Slightly too broad or narrow (e.g., `novel convolutional neural network` instead of `convolutional neural network`).
  * **Significant Error:** Includes surrounding context or is critically incomplete (e.g., `model, the Transformer-XL` instead of `Transformer-XL`).

**Scoring Rubric:**

  * **1.0 [Perfect]:** Factual, highly relevant, and has a perfect boundary.
  * **0.8 - 0.9 [Good]:** Factual, highly relevant, but has a **minor boundary error**.
  * **0.6 - 0.7 [Adequate]:** Factual and relevant, but has a **significant boundary error** or a minor misclassification.
  * **0.3 - 0.5 [Poor]:** Points to a real concept but is badly flawed (boundary, fact, or classification).
  * **0.1 - 0.2 [Irrelevant]:** Factually correct but not relevant to the text's core scientific meaning.
  * **0.0 [Incorrect]:** Factually wrong, a hallucination, or a major misclassification.

**Required Output Format:**
For each entity, provide a score and a brief justification.""",
            "SOURCE TEXT:",
            source_text[:2000],
            "",
            "CANDIDATES:"
        ]
        for e in chunk:
            prompt_lines.append(f"- {e}")
        prompt_lines.append("")
        prompt_lines.append("FORMAT INSTRUCTIONS:")
        prompt_lines.append(format_instructions)
        prompt = "\n".join(prompt_lines)
        logger.info(f"Invoking LLM for novel entity assessment chunk: {cache_key}")
        try:
            raw = llm_callable.invoke([("human", prompt)])
        except Exception as e:
            logger.error(f"LLM invocation failed for novel entity assessment chunk {cache_key}: {e}")
            continue
        parsed = {}
        try:
            parsed = json.loads(raw.content)
        except Exception:
            m = re.search(r'\{.*\}', raw.content, flags=re.S)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except Exception as e:
                    logger.error(f"Failed to parse JSON from LLM output for novel entity assessment chunk {cache_key}: {e}")
                    parsed = {}
        normalized = {}
        for k, v in parsed.items():
            normalized[k.strip()] = v
        results.update(normalized)
        if CACHE:
            try:
                cache_write(cache_key, normalized)
            except Exception as e:
                logger.error(f"Failed to cache novel entity assessment result for {cache_key}: {e}")
        time.sleep(0.2)
    logger.info(f"Novel entity assessment completed for {len(results)} entities.")
    return results


def get_all_scier_matches(exact_matches,fuzzy_matches,adjudicated_matches):
    matches = [entity for entity in exact_matches.values()]
    matches += [entity["gold"] for entity in fuzzy_matches.values()]
    matches += [match for match in adjudicated_matches.values() if match!="NO_MATCH"]
    matches = list(set(matches))
    logger.debug(f"Total matches collected: {len(matches)}")
    return matches

# -------------------------
# High-level runner function
# -------------------------
def run_fuzzy_adjudication_pipeline(gold_entities: List[str],
                                    bodhi_entities: List[str],
                                    llm_callable: Callable[[str], str],
                                    tokenizer: Optional[Callable[[str], List[str]]] = None,
                                    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
                                    usable_context_limit: int = 10000,
                                    format_instructions_stage3: str = "Return JSON mapping: {\"extracted_entity\": \"matched_gold_or_NO_MATCH\"}",
                                    format_instructions_assess: str = "Return JSON mapping: {\"entity\": {\"score\": 0..1, \"reason\": \"short explanation\"}}",
                                    perform_novel_assessment: bool = True,
                                    source_text_for_assessment: str = ""):
    logger.info("Running fuzzy adjudication pipeline...")
    # Stage 1
    exact_matches, bodhi_unmatched = stage1_exact_match(gold_entities, bodhi_entities)

    # Stage 2
    fuzzy_matches, bodhi_remaining_after2, candidate_pairs = stage2_fuzzy_match(gold_entities, bodhi_unmatched, threshold=fuzzy_threshold)

    # Stage 3
    adjudication_map = stage3_llm_adjudicate(gold_entities, bodhi_remaining_after2, llm_callable,
                                             tokenizer=tokenizer,
                                             usable_context_limit=usable_context_limit,
                                             format_instructions=format_instructions_stage3)

    normalized_exact_matches = {k: v for k, v in exact_matches.items()}
    normalized_fuzzy_matches = {b: {"gold": g, "score": s} for b, (g, s) in fuzzy_matches.items()}
    normalized_adjudicated = adjudication_map

    novel_entities = [e for e in bodhi_remaining_after2 if (adjudication_map.get(e) in (None, "NO_MATCH"))]
    for e, v in adjudication_map.items():
        if isinstance(v, str) and v.upper() == "NO_MATCH" and e not in novel_entities:
            novel_entities.append(e)

    novel_assessment = {}
    if perform_novel_assessment and novel_entities:
        novel_assessment = assess_novel_entities_with_text(novel_entities, source_text_for_assessment,
                                                           llm_callable, tokenizer=tokenizer,
                                                           usable_context_limit=usable_context_limit,
                                                           format_instructions=format_instructions_assess)
    matches = get_all_scier_matches(adjudicated_matches=normalized_adjudicated,
                                    exact_matches=normalized_exact_matches,
                                    fuzzy_matches=normalized_fuzzy_matches)
    fuzzy_adjudication_metrics = {
        "number_of_scier_entities": len(gold_entities),    
        "number_of_matches": len(matches),
        "number_of_exact_matches":len(normalized_exact_matches),
        "number_of_fuzzy_matches":len(normalized_fuzzy_matches),
        "number_of_adjudicated_matches":len(normalized_adjudicated),
        "number_of_novel_entities":len(normalized_adjudicated),
    }
    results = {
        "metadata":fuzzy_adjudication_metrics,
        "matches":matches,
        "exact_matches": normalized_exact_matches,
        "fuzzy_matches": normalized_fuzzy_matches,
        "adjudicated_matches": normalized_adjudicated,
        "novel_entities": novel_entities,
        "novel_assessment": novel_assessment,
    }
    logger.info("Fuzzy adjudication pipeline completed.")
    return results
