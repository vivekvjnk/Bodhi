import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

# ---------- Normalization ----------
def normalize_entity(entity: str) -> str:
    """Normalize entity string for comparison (case, spaces, punctuation)."""
    # lowercasing
    e = entity.lower().strip()
    # normalize unicode (remove accents etc.)
    e = unicodedata.normalize("NFKD", e)
    # remove special characters (keep alphanumerics and spaces)
    e = re.sub(r"[^a-z0-9\s]", "", e)
    # collapse multiple spaces
    e = re.sub(r"\s+", " ", e)
    return e

# ---------- Similarity ----------
def string_similarity(a: str, b: str) -> float:
    """Compute string similarity [0,1] using SequenceMatcher."""
    return SequenceMatcher(None, a, b).ratio()

# ---------- Stub Functions (LLM integration points) ----------
def verify_equivalence_with_llm(gold_entity, bodhi_entity, context=None):
    """Stub for LLM semantic equivalence verification."""
    # For now, always return False
    return False

def assess_significance_with_llm(entity, context=None):
    """Stub for LLM novelty significance scoring."""
    # For now, return neutral score
    return 5

# ---------- Core Function ----------
def measure_coverage(gold_dict, bodhi_dict, threshold_k=0.7, threshold_l=0.85):
    """
    Compare gold-standard KG with Bodhi extraction (deterministic part only).
    
    - How many entities from the gold standard dataset are properly detected by Bodhi pipeline?
        - Check if there are any one to one matches
        - Check if there are any entities with more than K semantic similarity(make sure numeric similarity is handled)
        - List all entities with semantic similarity > L. 
            - Pass them to LLM for equivalence verification. Also pass the respective sentences form gold standard as context
    - How many entities which are not present in gold standard are identified by Bodhi pipelin? Are they significant with respect to the context?      
        - List all the extracted entities, which are not present in the gold standard. 
            - Quantify their significance with respect to the source document.
            - Source document content with respective entities are passed to an LLM prompt. Task is to Quantify their significance. Gold standard entities get a  significance of 10 or 9. Use this as baseline for the quantification  
        - Entities with significance 10 or 9 are classified are high quality extractions.
        - Entities with less significance are classified as wrong extractions.

    Input format
    ===========
    Both gold standard dataset and Bodhi extracted data are converted into dictionaries of common format. Each key in the dictionary corresponds to an entity name, values(list of strings) inside each key are the type classifications for the entity. Number of types = number of times the entity is repeated in extraction/gold standard dataset.
    Following is a sample dictionary format:
    {'GxVAEs': ['Method','Method', 'Method'], 'VAEs': ['Method', 'Method'], 'de novo generation': ['Task'], 'computer-aided drug discovery': ['Task', 'Task'] ...}

    """

    # Normalize dictionaries
    def normalize_dict(d):
        normed = defaultdict(list)
        for ent, types in d.items():
            normed[normalize_entity(ent)].extend(types)
        return normed

    gold_norm = normalize_dict(gold_dict)
    bodhi_norm = normalize_dict(bodhi_dict)

    # Reports
    direct_matches = []
    fuzzy_candidates = []
    missed_entities = []
    bodhi_only = []
    type_consistency = []

    # Step 1: Direct Matches
    for g_ent, g_types in gold_norm.items():
        if g_ent in bodhi_norm:
            b_types = bodhi_norm[g_ent]
            direct_matches.append((g_ent, g_types[0], b_types[0]))
            type_consistency.append({
                "entity": g_ent,
                "gold_types": g_types,
                "bodhi_types": b_types
            })
        else:
            # Step 2: Fuzzy Candidate Matches
            best_score, best_match = 0, None
            for b_ent in bodhi_norm:
                score = string_similarity(g_ent, b_ent)
                if score > best_score:
                    best_score, best_match = score, b_ent
            if best_score >= threshold_k:
                fuzzy_candidates.append((g_ent, best_match, best_score))
            else:
                missed_entities.append(g_ent)

    # Step 3: Bodhi-only Entities
    matched_gold = {gm[0] for gm in direct_matches}
    fuzzy_gold = {fc[0] for fc in fuzzy_candidates}
    all_matched_gold = matched_gold.union(fuzzy_gold)

    for b_ent in bodhi_norm:
        if b_ent not in all_matched_gold:
            bodhi_only.append(b_ent)

    # Step 4: Coverage Stats
    total_gold = len(gold_norm)
    coverage_count = len(direct_matches) + len(fuzzy_candidates)
    coverage_pct = (coverage_count / total_gold * 100) if total_gold else 0

    report = {
        "coverage": {
            "total_gold": total_gold,
            "direct": len(direct_matches),
            "fuzzy_candidates": len(fuzzy_candidates),
            "missed": len(missed_entities),
            "coverage_pct": coverage_pct
        },
        "direct_matches": direct_matches,
        "fuzzy_candidates": fuzzy_candidates,
        "missed_entities": missed_entities,
        "bodhi_only": bodhi_only,
        "type_consistency": type_consistency
    }

    return report
