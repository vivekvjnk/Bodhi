from typing import Tuple, Dict, List

STOPWORDS = {
    "a","an","the","and","or","of","in","on","to","for","with","by","at","from","as",
    "is","are","was","were","be","have","has","had","we","you","they","he","she","it",
    "that","this","these","those"
}

def _tokenize(text: str) -> List[str]:
    # simple, regex-free split that keeps punctuation as separate tokens
    toks = []
    for raw in text.split():
        # split off trailing/leading punctuation
        left = 0
        right = len(raw)
        while left < right and not raw[left].isalnum():
            toks.append(raw[left])
            left += 1
        while right > left and not raw[right-1].isalnum():
            toks.append(raw[right-1])
            right -= 1
        if left < right:
            toks.append(raw[left:right])
    return toks

def _is_numberish(tok: str) -> bool:
    # contains any digit OR is a float-like/ID-like token (no regex)
    if any(ch.isdigit() for ch in tok):
        return True
    return False

def _line_shape(tokens: List[str]) -> List[str]:
    # map tokens to coarse shapes: D (numberish), W (word), P (punct)
    shape = []
    for t in tokens:
        if _is_numberish(t):
            shape.append("D")
        elif t.isalpha():
            shape.append("W")
        else:
            shape.append("P")
    return shape

def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))

def is_structured_text(
    text: str,
    *,
    dr_thresh: float = 0.36,    # tuned: digit_ratio
    sw_thresh: float = 0.03,    # tuned: stopword_ratio
    ls_thresh: float = 0.88,    # tuned: line_similarity (used only with low stopwords)
    min_lines: int = 3          # tiny guard against very short snippets
) -> Tuple[bool, Dict[str, float]]:
    # lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < min_lines:
        return (False, {"digit_ratio": 0.0, "stopword_ratio": 0.0, "sentence_end_ratio": 0.0, "line_similarity": 0.0})

    # tokenize whole text (regex-free)
    tokens = _tokenize(text)
    if not tokens:
        return (False, {"digit_ratio": 0.0, "stopword_ratio": 0.0, "sentence_end_ratio": 0.0, "line_similarity": 0.0})

    # metrics
    digit_ratio = sum(1 for t in tokens if _is_numberish(t)) / len(tokens)
    stopword_ratio = sum(1 for t in tokens if t.lower() in STOPWORDS) / len(tokens)
    sentence_end_ratio = sum(1 for ln in lines if ln.endswith((".", "!", "?"))) / len(lines)

    # line-shape similarity across adjacent lines
    shapes = []
    for ln in lines:
        shapes.append(_line_shape(_tokenize(ln)))
    sims = []
    for i in range(len(shapes)-1):
        sims.append(_jaccard(shapes[i], shapes[i+1]))
    line_similarity = (sum(sims)/len(sims)) if sims else 0.0

    # decision rule (tuned on your sample)
    flag = (digit_ratio >= dr_thresh) or ((stopword_ratio <= sw_thresh) and (line_similarity >= ls_thresh))

    return flag, {
        "digit_ratio": digit_ratio,
        "stopword_ratio": stopword_ratio,
        "sentence_end_ratio": sentence_end_ratio,
        "line_similarity": line_similarity,
    }


def evaluate_text_units(text_units: list[str]) -> list:
    """
    Evaluate all text units and return a matrix of results.
    Each text unit is identified by its index in the list.
    """
    results = []
    for idx, text in enumerate(text_units):
        structured,scores = is_structured_text(text)
        results.append({"index": idx, "is_structured": structured,"scores":scores})

    return results
