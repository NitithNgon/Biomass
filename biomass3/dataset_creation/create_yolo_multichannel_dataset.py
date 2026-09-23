#!/usr/bin/env python3
"""
Build a YOLO-format dataset for one (fold, channel-selection) combination
from the cached 9-channel PDD grids (see feature_cache.py).

Used both as a library (build_dataset(), called by run_experiments.py for all
40 fold x channel-set combinations) and as a CLI for building one dataset by
hand.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "scripts"))

from feature_cache import DEFAULT_CACHE_DIR, build_all_caches, load_plot_cache  # noqa: E402
from folds import (  # noqa: E402
    DEFAULT_K,
    DEFAULT_N_TEST,
    DEFAULT_N_TRAIN,
    DEFAULT_N_VAL,
    DEFAULT_SEED,
    Fold,
    build_folds,
)
from plots_registry import discover_plots  # noqa: E402
from pointcloud_multichannel import (  # noqa: E402
    ALL_CHANNELS,
    CODE_TO_CHANNEL,
    RubberTreeMultiChannelRasterizer,
)

DEFAULT_BOX_SIZE_METERS = 2.0
DEFAULT_OUTPUT_ROOT = SCRIPT_DIR / "yolov11" / "datasets"


def resolve_channels(channels: Sequence[str]) -> tuple[str, ...]:
    resolved = tuple(CODE_TO_CHANNEL.get(c, c) for c in channels)
    unknown = [c for c in resolved if c not in ALL_CHANNELS]
    if unknown:
        raise ValueError(f"Unknown channel(s) {unknown}. Available: {ALL_CHANNELS}")
    if len(resolved) not in (1, 3):
        raise ValueError(f"channels must have 1 or 3 entries, got {len(resolved)}")
    return resolved


def _yolo_labels_for_plot(meta: Dict, trees_df, box_size_meters: float) -> List[str]:
    width = float(meta["width"])
    height = float(meta["height"])
    pixel_size = float(meta["pixel_size"])
    box_size_px = box_size_meters / pixel_size

    labels: List[str] = []
    for _, tree in trees_df.iterrows():
        x_px = (float(tree["X"]) - meta["x_min"]) / pixel_size
        y_px = (float(tree["Y"]) - meta["y_min"]) / pixel_size
        if x_px < 0 or x_px >= width or y_px < 0 or y_px >= height:
            continue
        x_norm = np.clip(x_px / width, 0.0, 1.0)
        y_norm = np.clip(y_px / height, 0.0, 1.0)
        w_norm = np.clip(box_size_px / width, 0.0, 1.0)
        h_norm = np.clip(box_size_px / height, 0.0, 1.0)
        labels.append(f"0 {x_norm:.6f} {y_norm:.6f} {w_norm:.6f} {h_norm:.6f}")
    return labels


def build_dataset(
    fold: Fold,
    channels: Sequence[str],
    output_dir: Path,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    box_size_meters: float = DEFAULT_BOX_SIZE_METERS,
    overwrite: bool = True,
) -> Path:
    """Build a train/val/test YOLO dataset dir for one fold + channel selection."""
    channels = resolve_channels(channels)
    output_dir = Path(output_dir)
    if output_dir.exists():
        if not overwrite:
            raise SystemExit(f"Output exists: {output_dir}. Pass overwrite=True to replace it.")
        shutil.rmtree(output_dir)

    rasterizer = RubberTreeMultiChannelRasterizer()
    split_plots = {"train": fold.train, "val": fold.val, "test": fold.test}

    stats = []
    for split_name, plot_names in split_plots.items():
        image_dir = output_dir / "images" / split_name
        label_dir = output_dir / "labels" / split_name
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)

        for plot_name in plot_names:
            grid, meta, trees_df = load_plot_cache(cache_dir, plot_name)
            image_path = image_dir / f"{plot_name}.jpg"
            label_path = label_dir / f"{plot_name}.txt"

            rasterizer.save_image(grid, image_path, channel_order=channels)
            labels = _yolo_labels_for_plot(meta, trees_df, box_size_meters)
            label_path.write_text("\n".join(labels), encoding="utf-8")

            stats.append(
                {
                    "plot_name": plot_name,
                    "split": split_name,
                    "num_trees_csv": int(len(trees_df)),
                    "num_labels": len(labels),
                }
            )

    yaml_path = output_dir / "data.yaml"
    yaml_path.write_text(
        f"""# YOLO dataset for fold {fold.index}, channels={list(channels)}
path: {output_dir.absolute()}
train: images/train
val: images/val
test: images/test

names:
  0: tree

nc: 1

fold: {fold.index}
image_channel_order:
{chr(10).join(f"  - {c}" for c in channels)}
box_size_meters: {box_size_meters}
""",
        encoding="utf-8",
    )
    with open(output_dir / "dataset_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    return yaml_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one YOLO PDD dataset for a given fold index and 1-or-3 channel selection."
    )
    parser.add_argument("--fold", type=int, required=True, help="Fold index (0-based)")
    parser.add_argument("--channels", type=str, required=True, help="Comma-separated channel names/codes, 1 or 3")
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--cache_dir", type=str, default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--box_size", type=float, default=DEFAULT_BOX_SIZE_METERS)
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--n_train", type=int, default=DEFAULT_N_TRAIN)
    parser.add_argument("--n_val", type=int, default=DEFAULT_N_VAL)
    parser.add_argument("--n_test", type=int, default=DEFAULT_N_TEST)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--build_cache", action="store_true", help="(Re)build the feature cache first")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.build_cache:
        build_all_caches(Path(args.cache_dir))

    plot_names = [p.name for p in discover_plots()]
    folds = build_folds(
        plot_names, k=args.k, n_train=args.n_train, n_val=args.n_val, n_test=args.n_test, seed=args.seed
    )
    fold = folds[args.fold]
    channels = tuple(c.strip() for c in args.channels.split(","))

    yaml_path = build_dataset(
        fold,
        channels,
        Path(args.output_dir),
        cache_dir=Path(args.cache_dir),
        box_size_meters=args.box_size,
    )
    print(f"Built dataset for fold {fold.index}, channels={channels}")
    print(f"  train={fold.train}")
    print(f"  val={fold.val}")
    print(f"  test={fold.test}")
    print(f"  data.yaml: {yaml_path}")


if __name__ == "__main__":
    main()
