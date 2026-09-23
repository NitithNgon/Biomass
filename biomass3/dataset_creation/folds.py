#!/usr/bin/env python3
"""
Plot-level k-fold assignment for the 12-plot biomass3 dataset.

Each fold partitions all 12 plots into train=7 / val=2 / test=3, never
splitting a plot across tiles (trees within a plot are spatially correlated).
val is the YOLO training-time validation split used for early stopping only;
test is the held-out set accuracy is reported on. The same folds serve every
model. With k=4 folds of 3 test plots each, 4x3=12 exactly covers all 12
plots as test once each (full leave-plots-out coverage on the split that
matters for reporting); val only gets 4x2=8<12, so 8 of 12 plots get a val
turn and 4 never do. Train/val/test are each internally disjoint within a
fold (no leakage).

The 12 plots are shuffled once with a fixed seed, then rotated by
round(n_plots / k) positions per fold so successive folds' held-out plots
don't overlap until the rotation wraps around.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np

DEFAULT_K = 4
DEFAULT_N_TRAIN = 7
DEFAULT_N_VAL = 2
DEFAULT_N_TEST = 3
DEFAULT_SEED = 42


@dataclass(frozen=True)
class Fold:
    index: int
    train: List[str]
    val: List[str]
    test: List[str]

    def as_dict(self) -> Dict[str, List[str]]:
        return {"train": list(self.train), "val": list(self.val), "test": list(self.test)}


def build_folds(
    plot_names: Sequence[str],
    k: int = DEFAULT_K,
    n_train: int = DEFAULT_N_TRAIN,
    n_val: int = DEFAULT_N_VAL,
    n_test: int = DEFAULT_N_TEST,
    seed: int = DEFAULT_SEED,
) -> List[Fold]:
    n = len(plot_names)
    if n_train + n_val + n_test != n:
        raise ValueError(
            f"train+val+test ({n_train}+{n_val}+{n_test}={n_train + n_val + n_test}) "
            f"must equal the plot count ({n})"
        )

    names = sorted(plot_names, key=str.lower)
    rng = np.random.default_rng(seed)
    order = list(names)
    rng.shuffle(order)

    shift_step = round(n / k)
    folds: List[Fold] = []
    for fold_idx in range(k):
        shift = (fold_idx * shift_step) % n
        rolled = order[shift:] + order[:shift]
        train = rolled[:n_train]
        val = rolled[n_train : n_train + n_val]
        test = rolled[n_train + n_val :]
        folds.append(Fold(index=fold_idx, train=train, val=val, test=test))
    return folds


def coverage_report(folds: Sequence[Fold]) -> Dict[str, Dict[str, int]]:
    """Count how many folds each plot appears in as train/val/test (sanity check)."""
    report: Dict[str, Dict[str, int]] = {}
    for fold in folds:
        for role, plots in (("train", fold.train), ("val", fold.val), ("test", fold.test)):
            for name in plots:
                report.setdefault(name, {"train": 0, "val": 0, "test": 0})[role] += 1
    return report


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from plots_registry import discover_plots

    plots = [p.name for p in discover_plots()]
    folds = build_folds(plots)
    for fold in folds:
        print(f"Fold {fold.index}: train={fold.train}")
        print(f"         val={fold.val}")
        print(f"         test={fold.test}")
    print("\nCoverage (folds each plot appears in as test/val/train):")
    for name, counts in sorted(coverage_report(folds).items()):
        print(f"  {name}: {counts}")
