#!/usr/bin/env python3
"""
Discover the 12-plot LAS/CSV dataset and expose a stable, sorted plot list.

All biomass3 experiments (PDD selection + all 3 experiments) share this same
12-plot registry so that plot names, LAS paths, and label CSV paths are
resolved identically everywhere (dataset caching, k-fold assignment, and
per-fold YOLO dataset generation).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_PLOTS_DIR = REPO_ROOT / "biomass1" / "notebooks_density" / "processed"
DEFAULT_CSV_DIR = REPO_ROOT / "biomass1" / "dataset" / "ข้อมูลแปลง"
DEFAULT_LAS_PATTERN = "*_rotated.las"
DEFAULT_CSV_NAME = "DBHaverage.csv"


@dataclass(frozen=True)
class PlotEntry:
    name: str
    las_path: Path
    csv_path: Path


def _plot_name_from_las(las_file: Path) -> str:
    stem = las_file.stem
    if "_scans" in stem:
        return stem.split("_scans", 1)[0]
    if "_optimized" in stem:
        return stem.split("_optimized", 1)[0]
    if "_rotated" in stem:
        return stem.split("_rotated", 1)[0]
    return stem


def discover_plots(
    plots_dir: Path = DEFAULT_PLOTS_DIR,
    csv_dir: Path = DEFAULT_CSV_DIR,
    las_pattern: str = DEFAULT_LAS_PATTERN,
    csv_name: str = DEFAULT_CSV_NAME,
) -> List[PlotEntry]:
    plots_dir = Path(plots_dir)
    csv_dir = Path(csv_dir)
    las_files = sorted(plots_dir.glob(las_pattern))

    entries: List[PlotEntry] = []
    for las_file in las_files:
        plot_name = _plot_name_from_las(las_file)
        csv_path = csv_dir / plot_name / csv_name
        if not csv_path.exists():
            print(f"  Skip {las_file.name}: missing {csv_path}")
            continue
        entries.append(PlotEntry(name=plot_name, las_path=las_file, csv_path=csv_path))

    # Stable order (by plot name) so fold assignment is reproducible regardless
    # of filesystem glob order.
    entries.sort(key=lambda e: e.name.lower())
    return entries


if __name__ == "__main__":
    plots = discover_plots()
    print(f"Found {len(plots)} plots:")
    for p in plots:
        print(f"  {p.name}: {p.las_path.name}")
