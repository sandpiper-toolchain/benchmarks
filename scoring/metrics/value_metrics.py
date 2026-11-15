"""
Generic value metrics for sandpiper benchmarks.

These functions are suitable for any value benchmark that compares submitted
scalar or array results against reference values.  They are intentionally
generic — not tied to any particular physical quantity.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


def abs_error(submitted: float, reference: float) -> float:
    """
    Absolute error between a submitted value and a reference value.

    Parameters
    ----------
    submitted:
        The submitted scalar value.
    reference:
        The reference (ground-truth or theoretical) scalar value.

    Returns
    -------
    float
        ``|submitted - reference|``
    """
    return abs(submitted - reference)


def rel_error_pct(submitted: float, reference: float) -> float:
    """
    Relative error as a percentage.

    Parameters
    ----------
    submitted:
        The submitted scalar value.
    reference:
        The reference scalar value.  Must not be zero.

    Returns
    -------
    float
        ``|submitted - reference| / |reference| * 100``

    Raises
    ------
    ValueError
        If *reference* is zero (relative error is undefined).
    """
    if reference == 0.0:
        raise ValueError("Reference value is zero; relative error is undefined.")
    return abs(submitted - reference) / abs(reference) * 100.0


def mae(
    submitted: Sequence[float] | np.ndarray,
    reference: Sequence[float] | np.ndarray,
) -> float:
    """
    Mean absolute error over paired arrays.

    Parameters
    ----------
    submitted:
        Array of submitted values.
    reference:
        Array of reference values (same length as *submitted*).

    Returns
    -------
    float
        Mean of ``|submitted_i - reference_i|`` over all elements.
    """
    s = np.asarray(submitted, dtype=float)
    r = np.asarray(reference, dtype=float)
    return float(np.mean(np.abs(s - r)))


def rmse(
    submitted: Sequence[float] | np.ndarray,
    reference: Sequence[float] | np.ndarray,
) -> float:
    """
    Root mean squared error over paired arrays.

    Parameters
    ----------
    submitted:
        Array of submitted values.
    reference:
        Array of reference values (same length as *submitted*).

    Returns
    -------
    float
        ``sqrt(mean((submitted_i - reference_i)^2))`` over all elements.
    """
    s = np.asarray(submitted, dtype=float)
    r = np.asarray(reference, dtype=float)
    return float(np.sqrt(np.mean((s - r) ** 2)))
