"""
Scoring metrics for the compensation-index benchmark.

Datasets and scoring approach
------------------------------
Two datasets have theoretical reference κ values (Straub et al., 2009) and are
scored against those values:

    compensational_stacking   κ_reference = 0.75  (typical compensational)
    random_stacking           κ_reference = 0.50  (Poissonian / random walk)

Two datasets have no universal theoretical reference.  Their κ and T_c values
are reported as-is for cross-submission comparison:

    compensational_stacking_meanX    (mean avulsion period = 15 events)
    compensational_stacking_mean2X   (mean avulsion period = 30 events)

Metrics computed for theoretically-referenced datasets
-------------------------------------------------------
    1. kappa_abs_error     -- |κ_submitted − κ_reference|
    2. kappa_rel_error_pct -- |κ_submitted − κ_reference| / κ_reference × 100
"""

from __future__ import annotations

# Theoretical reference κ values (Straub et al., 2009).
KAPPA_REFERENCE = {
    "compensational_stacking": 1.0,
    "random_stacking": 0.50,
}

# Datasets with no theoretical reference — submitted values are reported as-is.
COMPARATIVE_DATASETS = (
    "compensational_stacking_meanX",
    "compensational_stacking_mean2X",
)

ALL_DATASETS = tuple(KAPPA_REFERENCE) + COMPARATIVE_DATASETS


def kappa_abs_error(kappa_sub: float, kappa_ref: float) -> float:
    """
    Absolute error in κ.

    Parameters
    ----------
    kappa_sub:
        κ value from the submission.
    kappa_ref:
        Theoretical reference κ value.

    Returns
    -------
    float
        |κ_sub − κ_ref|
    """
    return abs(kappa_sub - kappa_ref)


def kappa_rel_error_pct(kappa_sub: float, kappa_ref: float) -> float:
    """
    Relative error in κ, expressed as a percentage.

    Parameters
    ----------
    kappa_sub:
        κ value from the submission.
    kappa_ref:
        Theoretical reference κ value.

    Returns
    -------
    float
        |κ_sub − κ_ref| / κ_ref × 100
    """
    if kappa_ref == 0.0:
        raise ValueError("Reference κ is zero; relative error is undefined.")
    return abs(kappa_sub - kappa_ref) / abs(kappa_ref) * 100.0


def score_theoretical(dataset: str, kappa_sub: float) -> dict:
    """
    Score κ for a dataset with a theoretical reference value.

    Parameters
    ----------
    dataset:
        One of the keys in ``KAPPA_REFERENCE``.
    kappa_sub:
        Submitted κ value.

    Returns
    -------
    dict with keys ``kappa_reference``, ``kappa_submitted``,
    ``kappa_abs_error``, and ``kappa_rel_error_pct``.
    """
    if dataset not in KAPPA_REFERENCE:
        raise KeyError(
            f"'{dataset}' has no theoretical reference. "
            f"Expected one of: {list(KAPPA_REFERENCE)}"
        )
    kappa_ref = KAPPA_REFERENCE[dataset]
    return {
        "kappa_reference": kappa_ref,
        "kappa_submitted": kappa_sub,
        "kappa_abs_error": kappa_abs_error(kappa_sub, kappa_ref),
        "kappa_rel_error_pct": kappa_rel_error_pct(kappa_sub, kappa_ref),
    }


def report_comparative(dataset: str, kappa_sub: float, Tc_sub: float) -> dict:
    """
    Collect the submitted κ and T_c for a comparative (no-reference) dataset.

    Parameters
    ----------
    dataset:
        One of the ``COMPARATIVE_DATASETS`` names.
    kappa_sub:
        Submitted κ value.
    Tc_sub:
        Submitted T_c value (depositional-event units).

    Returns
    -------
    dict with keys ``kappa_submitted`` and ``Tc_submitted``.
    """
    if dataset not in COMPARATIVE_DATASETS:
        raise KeyError(
            f"'{dataset}' is not a comparative dataset. "
            f"Expected one of: {list(COMPARATIVE_DATASETS)}"
        )
    return {
        "kappa_submitted": kappa_sub,
        "Tc_submitted": Tc_sub,
    }
