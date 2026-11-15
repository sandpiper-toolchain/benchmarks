"""
Identification metrics for sandpiper benchmarks.

Provides summary statistics for distributions of detected object attributes
(e.g. bedform heights, lengths, depths).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def distribution_stats(series: pd.Series) -> dict:
    """
    Return summary statistics for a numeric Series.

    Parameters
    ----------
    series:
        A pandas Series of numeric values.  NaN values are dropped before
        computing statistics.

    Returns
    -------
    dict
        Keys: ``min``, ``mean``, ``median``, ``std``, ``p25``, ``p75``, ``max``.
        All values are rounded to 4 decimal places.  When the series is
        empty (after dropping NaNs) all values are ``None``.
    """
    arr = series.dropna().to_numpy(dtype=float)
    if len(arr) == 0:
        return {"min": None, "mean": None, "median": None, "std": None, "p25": None, "p75": None, "max": None}
    return {
        "min":    round(float(np.min(arr)),               4),
        "mean":   round(float(np.mean(arr)),              4),
        "median": round(float(np.median(arr)),            4),
        "std":    round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 4),
        "p25":    round(float(np.percentile(arr, 25)),    4),
        "p75":    round(float(np.percentile(arr, 75)),    4),
        "max":    round(float(np.max(arr)),               4),
    }
