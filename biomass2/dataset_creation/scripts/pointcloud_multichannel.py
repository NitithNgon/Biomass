#!/usr/bin/env python3
"""
Rasterize rubber plantation LiDAR point clouds into a 3-channel top-view image.

Channels:
  R: density           - number of points in each top-view grid cell
  G: hag_p95           - 95th percentile height above local ground
  B: dbh_band_density  - number of points around breast height

The output is a normal RGB image so the existing YOLO/CNN workflow can train
without changing the model input layer. The colors are synthetic feature
channels, not natural image colors.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple

import cv2
import laspy
import numpy as np
from scipy import ndimage


DEFAULT_CHANNELS = ("density", "hag_p95", "dbh_band_density")


@dataclass(frozen=True)
class RasterConfig:
    image_size: int = 320
    pixel_size: float = 0.125
    area_size: float = 40.0
    dbh_band_low: float = 1.0
    dbh_band_high: float = 1.6
    ground_filter_size: int = 9
    normalize_low_percentile: float = 1.0
    normalize_high_percentile: float = 99.0


def _ensure_odd(value: int) -> int:
    value = max(1, int(value))
    return value if value % 2 == 1 else value + 1


def _nearest_fill_nan(grid: np.ndarray) -> np.ndarray:
    """Fill NaN cells with the nearest finite value."""
    mask = np.isfinite(grid)
    if mask.all():
        return grid.astype(np.float32, copy=True)
    if not mask.any():
        return np.zeros_like(grid, dtype=np.float32)

    _, indices = ndimage.distance_transform_edt(~mask, return_indices=True)
    filled = grid[tuple(indices)]
    return filled.astype(np.float32, copy=False)


def _robust_uint8(channel: np.ndarray, low_pct: float, high_pct: float) -> np.ndarray:
    """Convert a feature channel to uint8 with robust percentile scaling."""
    ch = np.nan_to_num(channel.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    values = ch[np.isfinite(ch) & (ch > 0)]
    if values.size == 0:
        return np.zeros_like(ch, dtype=np.uint8)

    lo = float(np.percentile(values, low_pct))
    hi = float(np.percentile(values, high_pct))
    if hi <= lo:
        hi = float(values.max())
        lo = float(values.min())
    if hi <= lo:
        return np.zeros_like(ch, dtype=np.uint8)

    scaled = np.clip((ch - lo) / (hi - lo), 0.0, 1.0)
    return (scaled * 255.0).astype(np.uint8)


def _percentile_per_pixel(
    values: np.ndarray,
    pixel_ids: np.ndarray,
    height: int,
    width: int,
    percentile: float,
) -> np.ndarray:
    """Compute one percentile for each occupied pixel."""
    out = np.zeros(height * width, dtype=np.float32)
    if values.size == 0:
        return out.reshape(height, width)

    order = np.argsort(pixel_ids, kind="mergesort")
    sorted_ids = pixel_ids[order]
    sorted_values = values[order]
    unique_ids, starts = np.unique(sorted_ids, return_index=True)
    ends = np.r_[starts[1:], sorted_ids.size]

    for pixel_id, start, end in zip(unique_ids, starts, ends):
        out[int(pixel_id)] = np.percentile(sorted_values[start:end], percentile)

    return out.reshape(height, width)


class RubberTreeMultiChannelRasterizer:
    """Create physically meaningful 2D feature images from LAS point clouds."""

    channel_names = DEFAULT_CHANNELS

    def __init__(self, config: RasterConfig | None = None):
        self.config = config or RasterConfig()

    def load_pointcloud(self, las_path: str | Path) -> Tuple[np.ndarray, Dict]:
        las_path = Path(las_path)
        print(f"Loading point cloud: {las_path}")
        las = laspy.read(str(las_path))
        points = np.vstack((las.x, las.y, las.z)).T.astype(np.float64)
        if points.size == 0:
            raise ValueError(f"No points found in {las_path}")

        metadata = {
            "source_file": str(las_path),
            "num_points": int(points.shape[0]),
            "x_min": float(points[:, 0].min()),
            "x_max": float(points[:, 0].max()),
            "y_min": float(points[:, 1].min()),
            "y_max": float(points[:, 1].max()),
            "z_min": float(points[:, 2].min()),
            "z_max": float(points[:, 2].max()),
        }
        print(f"  Points: {metadata['num_points']:,}")
        print(
            "  Extent: "
            f"X {metadata['x_min']:.2f}-{metadata['x_max']:.2f} m, "
            f"Y {metadata['y_min']:.2f}-{metadata['y_max']:.2f} m, "
            f"Z {metadata['z_min']:.2f}-{metadata['z_max']:.2f} m"
        )
        return points, metadata

    def _pixelize(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, int, int, Dict]:
        cfg = self.config
        x_min = float(points[:, 0].min())
        y_min = float(points[:, 1].min())
        x_max = float(points[:, 0].max())
        y_max = float(points[:, 1].max())

        width = max(1, int(np.ceil((x_max - x_min) / cfg.pixel_size)))
        height = max(1, int(np.ceil((y_max - y_min) / cfg.pixel_size)))

        x_idx = np.clip(((points[:, 0] - x_min) / cfg.pixel_size).astype(np.int64), 0, width - 1)
        y_idx = np.clip(((points[:, 1] - y_min) / cfg.pixel_size).astype(np.int64), 0, height - 1)
        pixel_ids = y_idx * width + x_idx

        meta = {
            "width": int(width),
            "height": int(height),
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "pixel_size": float(cfg.pixel_size),
            "area_size": float(cfg.area_size),
            "image_size": int(cfg.image_size),
        }
        return pixel_ids, points[:, 2].astype(np.float64), height, width, meta

    def _estimate_ground(self, z: np.ndarray, pixel_ids: np.ndarray, height: int, width: int) -> np.ndarray:
        """Estimate a simple local ground surface from per-cell minimum Z."""
        z_min_flat = np.full(height * width, np.inf, dtype=np.float64)
        np.minimum.at(z_min_flat, pixel_ids, z)
        z_min_grid = z_min_flat.reshape(height, width)
        z_min_grid[~np.isfinite(z_min_grid)] = np.nan

        filled = _nearest_fill_nan(z_min_grid)
        size = _ensure_odd(self.config.ground_filter_size)
        ground = ndimage.minimum_filter(filled, size=size, mode="nearest")
        return ground.astype(np.float32)

    def rasterize(self, points: np.ndarray) -> Tuple[np.ndarray, Dict]:
        cfg = self.config
        pixel_ids, z, height, width, meta = self._pixelize(points)
        total_cells = height * width

        print(f"Rasterizing to {width}x{height} grid ({total_cells:,} cells)")

        density = np.bincount(pixel_ids, minlength=total_cells).reshape(height, width).astype(np.float32)

        ground = self._estimate_ground(z, pixel_ids, height, width)
        ground_flat = ground.reshape(-1)
        hag = np.maximum(z - ground_flat[pixel_ids], 0.0)

        hag_p95 = _percentile_per_pixel(hag, pixel_ids, height, width, 95.0)

        dbh_mask = (hag >= cfg.dbh_band_low) & (hag <= cfg.dbh_band_high)
        dbh_count = np.bincount(pixel_ids[dbh_mask], minlength=total_cells)
        dbh_band_density = dbh_count.reshape(height, width).astype(np.float32)

        grid = np.dstack((density, hag_p95, dbh_band_density)).astype(np.float32)
        meta.update(
            {
                "num_channels": 3,
                "channel_names": list(self.channel_names),
                "channel_description": {
                    "density": "Point count per top-view grid cell",
                    "hag_p95": "95th percentile height above local ground per grid cell",
                    "dbh_band_density": (
                        "Point count with height above local ground inside "
                        f"{cfg.dbh_band_low:.2f}-{cfg.dbh_band_high:.2f} m"
                    ),
                },
                "dbh_band_low": float(cfg.dbh_band_low),
                "dbh_band_high": float(cfg.dbh_band_high),
                "ground_filter_size": int(_ensure_odd(cfg.ground_filter_size)),
            }
        )
        return grid, meta

    def resize_grid(self, grid: np.ndarray) -> np.ndarray:
        target = int(self.config.image_size)
        height, width, channels = grid.shape
        if (height, width) == (target, target):
            return np.nan_to_num(grid, nan=0.0, posinf=0.0, neginf=0.0)

        resized = np.zeros((target, target, channels), dtype=np.float32)
        shrinking = target < height or target < width
        for channel_idx in range(channels):
            interpolation = cv2.INTER_AREA if shrinking else cv2.INTER_LINEAR
            resized[:, :, channel_idx] = cv2.resize(
                grid[:, :, channel_idx],
                (target, target),
                interpolation=interpolation,
            )
        return np.nan_to_num(resized, nan=0.0, posinf=0.0, neginf=0.0)

    def to_rgb_image(
        self,
        grid: np.ndarray,
        channel_order: Sequence[str] = DEFAULT_CHANNELS,
    ) -> np.ndarray:
        names = list(self.channel_names)
        rgb = np.zeros((*grid.shape[:2], 3), dtype=np.uint8)
        for out_idx, channel_name in enumerate(channel_order):
            if channel_name not in names:
                raise ValueError(f"Unknown channel '{channel_name}'. Available: {names}")
            channel_idx = names.index(channel_name)
            rgb[:, :, out_idx] = _robust_uint8(
                grid[:, :, channel_idx],
                self.config.normalize_low_percentile,
                self.config.normalize_high_percentile,
            )
        return rgb

    def save_rgb(self, grid: np.ndarray, output_path: str | Path, channel_order: Sequence[str] = DEFAULT_CHANNELS) -> None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rgb = self.to_rgb_image(grid, channel_order=channel_order)
        cv2.imwrite(str(output_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

    def save_channel_previews(self, grid: np.ndarray, output_dir: str | Path, base_name: str) -> None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for idx, name in enumerate(self.channel_names):
            preview = _robust_uint8(
                grid[:, :, idx],
                self.config.normalize_low_percentile,
                self.config.normalize_high_percentile,
            )
            cv2.imwrite(str(output_dir / f"{base_name}_{name}.png"), preview)


def _parse_channels(value: str) -> Tuple[str, str, str]:
    channels = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(channels) != 3:
        raise argparse.ArgumentTypeError("Expected exactly 3 comma-separated channel names")
    return channels


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a 3-channel LiDAR feature image from one LAS file."
    )
    parser.add_argument("input_las", type=str, help="Input .las/.laz file")
    parser.add_argument("--output_dir", type=str, default="raster_output", help="Output directory")
    parser.add_argument("--image_size", type=int, default=320, help="Output square image size")
    parser.add_argument("--pixel_size", type=float, default=0.125, help="Grid pixel size in meters")
    parser.add_argument("--area_size", type=float, default=40.0, help="Nominal plot size in meters")
    parser.add_argument("--dbh_band_low", type=float, default=1.0, help="Lower HAG bound for DBH band")
    parser.add_argument("--dbh_band_high", type=float, default=1.6, help="Upper HAG bound for DBH band")
    parser.add_argument("--ground_filter_size", type=int, default=9, help="Local minimum filter size in pixels")
    parser.add_argument(
        "--channels",
        type=_parse_channels,
        default=DEFAULT_CHANNELS,
        help="RGB channel order, e.g. density,hag_p95,dbh_band_density",
    )
    parser.add_argument("--save_npy", action="store_true", help="Save resized feature grid as .npy")
    parser.add_argument("--save_previews", action="store_true", help="Save one grayscale preview per channel")
    return parser


def write_metadata(metadata: Dict, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def main() -> None:
    args = build_arg_parser().parse_args()
    cfg = RasterConfig(
        image_size=args.image_size,
        pixel_size=args.pixel_size,
        area_size=args.area_size,
        dbh_band_low=args.dbh_band_low,
        dbh_band_high=args.dbh_band_high,
        ground_filter_size=args.ground_filter_size,
    )
    rasterizer = RubberTreeMultiChannelRasterizer(cfg)

    points, source_meta = rasterizer.load_pointcloud(args.input_las)
    grid, meta = rasterizer.rasterize(points)
    resized_grid = rasterizer.resize_grid(grid)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = Path(args.input_las).stem
    image_path = output_dir / f"{base_name}_multichannel.jpg"

    rasterizer.save_rgb(resized_grid, image_path, channel_order=args.channels)
    meta.update(source_meta)
    meta["resized_to"] = int(args.image_size)
    meta["rgb_channel_order"] = list(args.channels)
    write_metadata(meta, output_dir / f"{base_name}_metadata.json")

    if args.save_npy:
        np.save(output_dir / f"{base_name}_features.npy", resized_grid)
    if args.save_previews:
        rasterizer.save_channel_previews(resized_grid, output_dir / "channel_previews", base_name)

    print("Done")
    print(f"  Image: {image_path}")
    print(f"  Metadata: {output_dir / f'{base_name}_metadata.json'}")


if __name__ == "__main__":
    main()
