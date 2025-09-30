#!/usr/bin/env python3
"""
Analyze Bodhi run metrics when data is already pre-parsed into a dictionary.

Input:
    - metrics_dict: {run_path: metrics_dict}
      (run_path encodes config, metrics_dict has numeric values)

Usage:
    from analyze_bodhi_dict import analyze_from_dict
    analyze_from_dict(metrics_dict, out_dir="./analysis_output")
"""
import re,random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from helpers import get_experiment_metrics_pathlib

# ---------------- Parsing helpers ----------------

def parse_key(key: str):
    """
    Parse config information from run key string.
    Example key:
    198967567/general_config.generic_type_allowance=False,general_config.priming=False,general_config.token_limit=1000/seed=0/198967567/eval_results/eval_metrics.yml
    """
    # Extract doc_id (first folder name)
    doc_id = key.split("/")[0]

    # Extract config params
    cfg_match = re.search(r"generic_type_allowance=(True|False).*priming=(True|False).*token_limit=(\d+)", key)
    priming = None
    generic = None
    token_limit = None
    if cfg_match:
        generic = cfg_match.group(1) == "True"
        priming = re.search(r"priming=(True|False)", key).group(1) == "True"
        token_limit = int(cfg_match.group(3))

    # Extract seed
    seed_match = re.search(r"seed=(\d+)", key)
    seed = int(seed_match.group(1)) if seed_match else None

    return {
        "doc_id": doc_id,
        "priming": priming,
        "generic": generic,
        "token_limit": token_limit,
        "seed": seed,
        "run_key": key
    }

def dict_to_dataframe(metrics_dict):
    rows = []
    for key, metrics in metrics_dict.items():
        row = parse_key(key)
        row.update(metrics)
        rows.append(row)
    return pd.DataFrame(rows)

# ---------------- Stats helpers ----------------

def bootstrap_ci(data, func=np.mean, n_boot=1000, alpha=0.05, rng=None):
    """
    Compute a bootstrap confidence interval for a given statistic.

    Parameters
    ----------
    data : array-like
        Input data from which to compute the confidence interval.
    func : callable, optional
        Function to compute the statistic of interest (default: numpy.mean).
        Can be any function that takes an array-like input and returns a scalar.
    n_boot : int, optional
        Number of bootstrap resamples to perform (default: 1000).
    alpha : float, optional
        Significance level (default: 0.05). For 95% confidence interval, use 0.05.
    rng : random.Random, optional
        Random number generator instance for reproducibility. 
        If None, defaults to random.Random(0).

    Returns
    -------
    tuple
        (estimate, ci_lower, ci_upper), where:
        - estimate is the statistic computed on the original dataset.
        - ci_lower is the lower bound of the (1 - alpha) bootstrap confidence interval.
        - ci_upper is the upper bound of the (1 - alpha) bootstrap confidence interval.
        Returns (None, None, None) if input data is empty or only NaNs.

    Notes
    -----
    This function uses the percentile method for bootstrap confidence intervals.
    """
    rng = rng or random.Random(0)
    arr = np.array(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return (None, None, None)
    est = func(arr)
    boots = [func(rng.choices(arr, k=len(arr))) for _ in range(n_boot)]
    lo = np.percentile(boots, 100*alpha/2)
    hi = np.percentile(boots, 100*(1-alpha/2))
    return est, lo, hi

def aggregate_by_config(df, metrics_cols, group_cols=["token_limit","priming","generic"]):
    grouped = df.groupby(group_cols)
    records = []
    for name, group in grouped:
        rec = dict(zip(group_cols, name))
        rec["n_runs"] = len(group)
        for m in metrics_cols:
            if m in group:
                vals = group[m].values
                est, lo, hi = bootstrap_ci(vals)
                rec[f"{m}_mean"] = est
                rec[f"{m}_ci_lo"] = lo
                rec[f"{m}_ci_hi"] = hi
        records.append(rec)
    return pd.DataFrame(records)

# ---------------- Plots ----------------

def plot_metric_curve(df, metric, out_dir):
    df_sorted = df.sort_values("token_limit")
    combos = df_sorted.groupby(["priming","generic"])
    plt.figure(figsize=(8,6))
    for (priming,generic), group in combos:
        stats = group.groupby("token_limit")[metric].mean().reset_index()
        xs, ys = stats["token_limit"], stats[metric]
        label = f"priming={priming}, generic={generic}"
        plt.plot(xs, ys, marker="o", label=label)
    plt.xlabel("Token limit")
    plt.ylabel(metric)
    plt.title(f"{metric} vs token_limit")
    plt.legend()
    plt.grid(True)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    plt.savefig(Path(out_dir)/f"{metric}_vs_tokenlimit.png", bbox_inches="tight")
    plt.close()

# ---------------- Main entry ----------------

def analyze_from_dict(metrics_dict, out_dir="./analysis_output"):
    df = dict_to_dataframe(metrics_dict)
    print("Loaded runs:", len(df))

    # Save raw data
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    df.to_csv(Path(out_dir)/"raw_runs_table.csv", index=False)

    # Aggregate
    metrics_cols = [
        "f1","precision","recall",
        "adjusted_f1","adjusted_precision","adjusted_recall",
        "method_f1","method_precision","method_recall","method_coverage",
        "domain_f1","domain_precision","domain_recall","domain_coverage"
    ]
    agg = aggregate_by_config(df, [c for c in metrics_cols if c in df.columns])
    agg.to_csv(Path(out_dir)/"aggregated_by_config.csv", index=False)

    # Example plots
    # for m in ["f1","adjusted_f1","precision","recall"]:
    for m in [
        "f1","precision","recall",
        "adjusted_f1","adjusted_precision","adjusted_recall",
        "method_f1","method_precision","method_recall","method_coverage",
        "domain_f1","domain_precision","domain_recall","domain_coverage"
    ]:
        if m in df.columns:
            plot_metric_curve(df, m, out_dir)

    print("Analysis complete. Outputs in", out_dir)


if __name__ == "__main__":
    metrics = get_experiment_metrics_pathlib(parent_dir="results")
    analyze_from_dict(metrics_dict=metrics)