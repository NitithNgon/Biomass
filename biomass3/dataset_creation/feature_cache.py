#!/usr/bin/env python3
"""
Rasterize each of the 12 plots exactly once into the full 9-channel PDD grid
and cache it, so exp1 (9 single-channel configs), exp2, and exp3 (5 model
sizes) never re-parse the multi-million-point LAS files - they just slice
channels out of the cached grid. Also caches each plot's tree-label table and
raster metadata (needed to place YOLO boxes) alongside it.

Cache layout (default under biomass3/dataset_creation/cache/):
  <plot_name>_grid.npy       - (image_size, image_size, 9) float32, resized
  <plot_name>_meta.json      - rasterization + source metadata
  <plot_name>_trees.csv      - tree X/Y labels loaded from DBHaverage.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "scripts"))

from plots_registry import PlotEntry, discover_plots  # noqa: E402
from pointcloud_multichannel import (  # noqa: E402
    ALL_CHANNELS,
    RasterConfig,
    RubberTreeMultiChannelRasterizer,
)

DEFAULT_CACHE_DIR = SCRIPT_DIR / "cache"


def _find_coordinate_columns(df: pd.DataFrame) -> tuple[str, str]:
    normalized = {col.strip().lower(): col for col in df.columns}
    x_col = normalized.get("x") or normalized.get("x_m") or normalized.get("utm_x")
    y_col = normalized.get("y") or normalized.get("y_m") or normalized.get("utm_y")
    if x_col is None or y_col is None:
        raise ValueError(f"CSV must contain X/Y coordinate columns. Found: {list(df.columns)}")
    return x_col, y_col


def load_tree_labels(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    x_col, y_col = _find_coordinate_columns(df)
    df = df.rename(columns={x_col: "X", y_col: "Y"})
    df = df.dropna(subset=["X", "Y"])
    return df[["X", "Y"]].reset_index(drop=True)


def cache_paths(cache_dir: Path, plot_name: str) -> Dict[str, Path]:
    return {
        "grid": cache_dir / f"{plot_name}_grid.npy",
        "meta": cache_dir / f"{plot_name}_meta.json",
        "trees": cache_dir / f"{plot_name}_trees.csv",
    }


def is_cached(cache_dir: Path, plot_name: str) -> bool:
    paths = cache_paths(cache_dir, plot_name)
    return all(p.exists() for p in paths.values())


def build_plot_cache(
    entry: PlotEntry,
    cache_dir: Path,
    config: RasterConfig,
    overwrite: bool = False,
) -> Dict:
    paths = cache_paths(cache_dir, entry.name)
    if not overwrite and is_cached(cache_dir, entry.name):
        with open(paths["meta"], encoding="utf-8") as f:
            return json.load(f)

    cache_dir.mkdir(parents=True, exist_ok=True)
    rasterizer = RubberTreeMultiChannelRasterizer(config)

    points, source_meta = rasterizer.load_pointcloud(entry.las_path)
    grid, meta = rasterizer.rasterize(points)
    resized_grid = rasterizer.resize_grid(grid)

    trees_df = load_tree_labels(entry.csv_path)

    meta.update(source_meta)
    meta["plot_name"] = entry.name
    meta["las_path"] = str(entry.las_path)
    meta["csv_path"] = str(entry.csv_path)
    meta["resized_to"] = int(config.image_size)
    meta["num_trees_csv"] = int(len(trees_df))

    np.save(paths["grid"], resized_grid)
    trees_df.to_csv(paths["trees"], index=False)
    with open(paths["meta"], "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"  Cached {entry.name}: grid {resized_grid.shape}, {len(trees_df)} trees")
    return meta


def build_all_caches(
    cache_dir: Path = DEFAULT_CACHE_DIR,
    config: RasterConfig | None = None,
    overwrite: bool = False,
) -> List[Dict]:
    config = config or RasterConfig()
    entries = discover_plots()
    print(f"Building PDD feature cache for {len(entries)} plots -> {cache_dir}")
    metas = []
    for entry in entries:
        metas.append(build_plot_cache(entry, cache_dir, config, overwrite=overwrite))
    return metas


def load_plot_cache(cache_dir: Path, plot_name: str) -> tuple[np.ndarray, Dict, pd.DataFrame]:
    paths = cache_paths(cache_dir, plot_name)
    grid = np.load(paths["grid"])
    with open(paths["meta"], encoding="utf-8") as f:
        meta = json.load(f)
    trees_df = pd.read_csv(paths["trees"])
    return grid, meta, trees_df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build the 9-channel PDD feature cache for all 12 plots.")
    parser.add_argument("--cache_dir", type=str, default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--image_size", type=int, default=320)
    parser.add_argument("--pixel_size", type=float, default=0.125)
    args = parser.parse_args()

    cfg = RasterConfig(image_size=args.image_size, pixel_size=args.pixel_size)
    metas = build_all_caches(Path(args.cache_dir), cfg, overwrite=args.overwrite)
    print(f"\nDone. Cached {len(metas)} plots with channels: {', '.join(ALL_CHANNELS)}")
