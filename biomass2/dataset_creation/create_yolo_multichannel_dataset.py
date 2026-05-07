#!/usr/bin/env python3
"""
Generate a YOLO-format dataset using 3-channel LiDAR feature images.

Default RGB mapping:
  R = density
  G = hag_p95
  B = dbh_band_density
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR / "scripts"))

from pointcloud_multichannel import (  # noqa: E402
    DEFAULT_CHANNELS,
    RasterConfig,
    RubberTreeMultiChannelRasterizer,
)


class YOLOMultiChannelDatasetGenerator:
    def __init__(
        self,
        image_size: int = 320,
        pixel_size: float = 0.125,
        area_size: float = 40.0,
        box_size_meters: float = 2.0,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        dbh_band_low: float = 1.0,
        dbh_band_high: float = 1.6,
        ground_filter_size: int = 9,
        channel_order: Sequence[str] = DEFAULT_CHANNELS,
    ):
        total_ratio = train_ratio + val_ratio + test_ratio
        if not np.isclose(total_ratio, 1.0):
            raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")

        self.image_size = image_size
        self.pixel_size = pixel_size
        self.area_size = area_size
        self.box_size_meters = box_size_meters
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.channel_order = tuple(channel_order)
        self.tree_class = 0

        config = RasterConfig(
            image_size=image_size,
            pixel_size=pixel_size,
            area_size=area_size,
            dbh_band_low=dbh_band_low,
            dbh_band_high=dbh_band_high,
            ground_filter_size=ground_filter_size,
        )
        self.rasterizer = RubberTreeMultiChannelRasterizer(config)

    @staticmethod
    def _find_coordinate_columns(df: pd.DataFrame) -> Tuple[str, str]:
        normalized = {col.strip().lower(): col for col in df.columns}
        x_col = normalized.get("x") or normalized.get("x_m") or normalized.get("utm_x")
        y_col = normalized.get("y") or normalized.get("y_m") or normalized.get("utm_y")
        if x_col is None or y_col is None:
            raise ValueError(f"CSV must contain X/Y coordinate columns. Found: {list(df.columns)}")
        return x_col, y_col

    def load_tree_labels(self, csv_path: Path) -> pd.DataFrame:
        print(f"Loading labels: {csv_path}")
        df = pd.read_csv(csv_path)
        x_col, y_col = self._find_coordinate_columns(df)
        df = df.rename(columns={x_col: "X", y_col: "Y"})
        df = df.dropna(subset=["X", "Y"])
        print(f"  Valid trees: {len(df)}")
        return df

    def meters_to_pixels(self, x_meters: float, y_meters: float, meta: Dict) -> Tuple[float, float]:
        px = (x_meters - meta["x_min"]) / self.pixel_size
        py = (y_meters - meta["y_min"]) / self.pixel_size
        return px, py

    def create_yolo_labels(self, trees_df: pd.DataFrame, meta: Dict, output_path: Path) -> int:
        width = float(meta["width"])
        height = float(meta["height"])
        box_size_px = self.box_size_meters / self.pixel_size

        labels: List[str] = []
        for _, tree in trees_df.iterrows():
            x_px, y_px = self.meters_to_pixels(float(tree["X"]), float(tree["Y"]), meta)
            if x_px < 0 or x_px >= width or y_px < 0 or y_px >= height:
                continue

            x_norm = np.clip(x_px / width, 0.0, 1.0)
            y_norm = np.clip(y_px / height, 0.0, 1.0)
            w_norm = np.clip(box_size_px / width, 0.0, 1.0)
            h_norm = np.clip(box_size_px / height, 0.0, 1.0)
            labels.append(
                f"{self.tree_class} {x_norm:.6f} {y_norm:.6f} {w_norm:.6f} {h_norm:.6f}"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(labels), encoding="utf-8")
        return len(labels)

    def process_plot(self, las_path: Path, csv_path: Path, output_dir: Path, split: str) -> Dict:
        plot_name = las_path.stem
        print(f"\n{'=' * 72}")
        print(f"Processing {plot_name} ({split})")
        print(f"{'=' * 72}")

        points, _ = self.rasterizer.load_pointcloud(las_path)
        grid, meta = self.rasterizer.rasterize(points)
        resized_grid = self.rasterizer.resize_grid(grid)
        meta["resized_to"] = int(self.image_size)
        meta["rgb_channel_order"] = list(self.channel_order)

        trees_df = self.load_tree_labels(csv_path)

        image_dir = output_dir / "images" / split
        label_dir = output_dir / "labels" / split
        metadata_dir = output_dir / "metadata" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        image_path = image_dir / f"{plot_name}.jpg"
        label_path = label_dir / f"{plot_name}.txt"
        metadata_path = metadata_dir / f"{plot_name}.json"

        self.rasterizer.save_rgb(resized_grid, image_path, channel_order=self.channel_order)
        num_labels = self.create_yolo_labels(trees_df, meta, label_path)

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        print(f"  Image: {image_path}")
        print(f"  Labels in bounds: {num_labels}/{len(trees_df)}")
        return {
            "plot_name": plot_name,
            "split": split,
            "las_path": str(las_path),
            "csv_path": str(csv_path),
            "image_path": str(image_path),
            "label_path": str(label_path),
            "num_trees_csv": int(len(trees_df)),
            "num_labels": int(num_labels),
        }

    def split_dataset(self, plot_pairs: Sequence[Tuple[Path, Path]], seed: int) -> Dict[str, List[Tuple[Path, Path]]]:
        rng = np.random.default_rng(seed)
        pairs = list(plot_pairs)
        rng.shuffle(pairs)

        n = len(pairs)
        n_train = int(n * self.train_ratio)
        n_val = int(n * self.val_ratio)
        return {
            "train": pairs[:n_train],
            "val": pairs[n_train : n_train + n_val],
            "test": pairs[n_train + n_val :],
        }

    def create_data_yaml(self, output_dir: Path) -> Path:
        yaml_path = output_dir / "data.yaml"
        yaml_content = f"""# YOLO Dataset Configuration
# Rubber tree LiDAR multi-channel dataset

path: {output_dir.absolute()}
train: images/train
val: images/val
test: images/test

names:
  0: tree

nc: 1

image_size: {self.image_size}
pixel_size: {self.pixel_size}
area_coverage: {self.area_size}x{self.area_size}m
default_box_size: {self.box_size_meters}m
rgb_channel_order:
  - {self.channel_order[0]}
  - {self.channel_order[1]}
  - {self.channel_order[2]}
"""
        yaml_path.write_text(yaml_content, encoding="utf-8")
        print(f"\nCreated {yaml_path}")
        return yaml_path


def _parse_channels(value: str) -> Tuple[str, str, str]:
    channels = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(channels) != 3:
        raise argparse.ArgumentTypeError("Expected exactly 3 comma-separated channel names")
    return channels


def _plot_name_from_las(las_file: Path) -> str:
    stem = las_file.stem
    if "_scans" in stem:
        return stem.split("_scans", 1)[0]
    if "_optimized" in stem:
        return stem.split("_optimized", 1)[0]
    if "_rotated" in stem:
        return stem.split("_rotated", 1)[0]
    return stem


def find_plot_pairs(plots_dir: Path, csv_dir: Path, las_pattern: str, csv_name: str) -> List[Tuple[Path, Path]]:
    las_files = sorted(plots_dir.glob(las_pattern))
    print(f"Found {len(las_files)} LAS files with pattern '{las_pattern}'")

    pairs: List[Tuple[Path, Path]] = []
    for las_file in las_files:
        plot_name = _plot_name_from_las(las_file)
        csv_path = csv_dir / plot_name / csv_name
        if not csv_path.exists():
            print(f"  Skip {las_file.name}: missing {csv_path}")
            continue
        pairs.append((las_file, csv_path))

    return pairs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate YOLO dataset from LAS files using density + HAG + DBH-band channels."
    )
    parser.add_argument("--plots_dir", type=str, required=True, help="Directory containing LAS files")
    parser.add_argument("--csv_dir", type=str, required=True, help="Directory containing plot label folders")
    parser.add_argument(
        "--output_dir",
        type=str,
        default=str(SCRIPT_DIR / "yolov11" / "dataset_multichannel"),
        help="Output YOLO dataset directory",
    )
    parser.add_argument("--las_pattern", type=str, default="*_optimized_*.las", help="Glob pattern for LAS files")
    parser.add_argument("--use_rotated", action="store_true", help="Use '*_rotated.las' as LAS pattern")
    parser.add_argument("--csv_name", type=str, default="DBHaverage.csv", help="CSV filename inside each plot folder")

    parser.add_argument("--image_size", type=int, default=320)
    parser.add_argument("--pixel_size", type=float, default=0.125)
    parser.add_argument("--area_size", type=float, default=40.0)
    parser.add_argument("--box_size", type=float, default=2.0, help="YOLO box size in meters")

    parser.add_argument("--dbh_band_low", type=float, default=1.0, help="Lower HAG bound for DBH-band channel")
    parser.add_argument("--dbh_band_high", type=float, default=1.6, help="Upper HAG bound for DBH-band channel")
    parser.add_argument("--ground_filter_size", type=int, default=9, help="Local ground filter size in pixels")
    parser.add_argument("--channels", type=_parse_channels, default=DEFAULT_CHANNELS)

    parser.add_argument("--train_ratio", type=float, default=0.7)
    parser.add_argument("--val_ratio", type=float, default=0.15)
    parser.add_argument("--test_ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing dataset")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    plots_dir = Path(args.plots_dir)
    csv_dir = Path(args.csv_dir)
    output_dir = Path(args.output_dir)

    if args.use_rotated:
        args.las_pattern = "*_rotated.las"

    if output_dir.exists():
        if not args.overwrite:
            raise SystemExit(f"Output exists: {output_dir}. Use --overwrite to replace it.")
        shutil.rmtree(output_dir)

    plot_pairs = find_plot_pairs(plots_dir, csv_dir, args.las_pattern, args.csv_name)
    if not plot_pairs:
        raise SystemExit("No matching LAS/CSV pairs found")

    generator = YOLOMultiChannelDatasetGenerator(
        image_size=args.image_size,
        pixel_size=args.pixel_size,
        area_size=args.area_size,
        box_size_meters=args.box_size,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        dbh_band_low=args.dbh_band_low,
        dbh_band_high=args.dbh_band_high,
        ground_filter_size=args.ground_filter_size,
        channel_order=args.channels,
    )

    splits = generator.split_dataset(plot_pairs, seed=args.seed)
    for split_name, pairs in splits.items():
        print(f"{split_name}: {len(pairs)} plots")

    stats: List[Dict] = []
    for split_name, pairs in splits.items():
        for las_path, csv_path in pairs:
            stats.append(generator.process_plot(las_path, csv_path, output_dir, split_name))

    yaml_path = generator.create_data_yaml(output_dir)
    stats_path = output_dir / "dataset_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print("\nDataset generation complete")
    print(f"  Dataset: {output_dir}")
    print(f"  Data YAML: {yaml_path}")
    print(f"  Stats: {stats_path}")


if __name__ == "__main__":
    main()
