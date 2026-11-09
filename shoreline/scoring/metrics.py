"""
Scoring metrics for the Selenga shoreline benchmark.

Three metrics are computed:

    1. mean_distance_error  -- average nearest-neighbour distance (metres)
                               between submitted and reference polylines
    2. pixel_f1             -- F1 score after rasterizing both polylines onto
                               the benchmark grid
    3. roughness_agreement  -- relative % difference in the area-normalised
                               shoreline roughness  R = L / sqrt(A_land)
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from scipy.spatial import cKDTree
from shapely.geometry import mapping
from shapely.ops import unary_union


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _load_line(path: str | Path) -> gpd.GeoDataFrame:
    """Load a GeoJSON polyline into a GeoDataFrame."""
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError(f"Input GeoJSON has no CRS: {path}")
    return gdf


def _reproject_to_match(gdf: gpd.GeoDataFrame, target_crs) -> gpd.GeoDataFrame:
    """Reproject a GeoDataFrame to target_crs if needed."""
    if gdf.crs != target_crs:
        gdf = gdf.to_crs(target_crs)
    return gdf


def _densify_line(gdf: gpd.GeoDataFrame, spacing_m: float = 10.0) -> np.ndarray:
    """
    Return (N, 2) array of points sampled along all geometries at spacing_m
    intervals (in the CRS units, assumed metres).
    """
    pts = []
    for geom in gdf.geometry:
        line = geom if geom.geom_type != "MultiLineString" else unary_union(geom)
        length = line.length
        num = max(2, int(math.ceil(length / spacing_m)))
        for i in range(num + 1):
            pt = line.interpolate(i / num, normalized=True)
            pts.append([pt.x, pt.y])
    return np.array(pts)


def _rasterize_line(gdf: gpd.GeoDataFrame, transform, shape_px) -> np.ndarray:
    """Burn polyline geometries into a boolean raster of shape_px (rows, cols)."""
    geoms = [mapping(geom) for geom in gdf.geometry]
    burned = rasterize(
        geoms,
        out_shape=shape_px,
        transform=transform,
        fill=0,
        default_value=1,
        dtype="uint8",
        all_touched=True,
    )
    return burned.astype(bool)


# ---------------------------------------------------------------------------
# public metric functions
# ---------------------------------------------------------------------------

def mean_distance_error(
    submitted_path: str | Path,
    reference_path: str | Path,
    densify_spacing_m: float = 10.0,
) -> float:
    """
    Compute mean nearest-neighbour distance (metres) between the submitted
    and reference shoreline polylines.

    Both lines are densified to points at ``densify_spacing_m`` intervals
    before the nearest-neighbour search, so the result is not sensitive to
    the original vertex density of the input lines.  The metric is computed
    symmetrically: distances from submitted→reference and reference→submitted
    are averaged together.

    Parameters
    ----------
    submitted_path:
        Path to the submitted result GeoJSON (polyline).
    reference_path:
        Path to the reference shoreline GeoJSON (polyline).
    densify_spacing_m:
        Point spacing (m) used when densifying lines before distance calc.

    Returns
    -------
    float
        Mean distance in CRS units (metres if CRS is projected in metres).
    """
    ref = _load_line(reference_path)
    sub = _load_line(submitted_path)
    sub = _reproject_to_match(sub, ref.crs)

    ref_pts = _densify_line(ref, spacing_m=densify_spacing_m)
    sub_pts = _densify_line(sub, spacing_m=densify_spacing_m)

    tree_ref = cKDTree(ref_pts)
    tree_sub = cKDTree(sub_pts)

    d_sub_to_ref, _ = tree_ref.query(sub_pts, k=1)
    d_ref_to_sub, _ = tree_sub.query(ref_pts, k=1)

    return float(np.mean(np.concatenate([d_sub_to_ref, d_ref_to_sub])))


def pixel_f1(
    submitted_path: str | Path,
    reference_path: str | Path,
    mask_path: str | Path,
) -> dict[str, float]:
    """
    Compute pixel-wise precision, recall, and F1 score by rasterizing the
    submitted and reference polylines onto the benchmark grid.

    Parameters
    ----------
    submitted_path:
        Path to the submitted result GeoJSON (polyline).
    reference_path:
        Path to the reference shoreline GeoJSON (polyline).
    mask_path:
        Path to the benchmark input GeoTIFF (used only for grid/transform).

    Returns
    -------
    dict with keys ``precision``, ``recall``, ``f1``.
    """
    with rasterio.open(mask_path) as src:
        transform = src.transform
        shape_px = (src.height, src.width)
        crs = src.crs

    ref = _load_line(reference_path)
    sub = _load_line(submitted_path)

    ref = _reproject_to_match(ref, crs)
    sub = _reproject_to_match(sub, crs)

    ref_raster = _rasterize_line(ref, transform, shape_px)
    sub_raster = _rasterize_line(sub, transform, shape_px)

    tp = int(np.sum(ref_raster & sub_raster))
    fp = int(np.sum(sub_raster & ~ref_raster))
    fn = int(np.sum(ref_raster & ~sub_raster))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    return {"precision": precision, "recall": recall, "f1": f1}


def roughness_agreement(
    submitted_path: str | Path,
    reference_path: str | Path,
    mask_path: str | Path,
) -> dict[str, float]:
    """
    Compute area-normalised shoreline roughness  R = L / sqrt(A_land)  for
    both the submitted and reference shorelines, then report the relative
    percentage difference.

    Land area is taken from the benchmark binary mask (pixel value == 1).
    Shoreline length is the total polyline length in CRS units.

    Parameters
    ----------
    submitted_path:
        Path to the submitted result GeoJSON (polyline).
    reference_path:
        Path to the reference shoreline GeoJSON (polyline).
    mask_path:
        Path to the benchmark input GeoTIFF (binary land/water mask).

    Returns
    -------
    dict with keys ``roughness_reference``, ``roughness_submitted``,
    ``relative_difference_pct``.
    """
    with rasterio.open(mask_path) as src:
        data = src.read(1)
        transform = src.transform
        crs = src.crs
        pixel_area_m2 = abs(transform.a * transform.e)

    land_pixels = int(np.sum(data == 1))
    area_land_m2 = land_pixels * pixel_area_m2

    ref = _load_line(reference_path)
    sub = _load_line(submitted_path)
    sub = _reproject_to_match(sub, crs)

    def _total_length(gdf):
        return float(sum(geom.length for geom in gdf.geometry))

    L_ref = _total_length(ref)
    L_sub = _total_length(sub)

    R_ref = L_ref / math.sqrt(area_land_m2)
    R_sub = L_sub / math.sqrt(area_land_m2)

    rel_diff_pct = abs(R_sub - R_ref) / R_ref * 100.0 if R_ref > 0 else float("nan")

    return {
        "roughness_reference": R_ref,
        "roughness_submitted": R_sub,
        "relative_difference_pct": rel_diff_pct,
    }
