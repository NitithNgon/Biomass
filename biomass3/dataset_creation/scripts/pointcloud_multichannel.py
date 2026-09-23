#!/usr/bin/env python3
"""
Rasterize rubber plantation LiDAR point clouds into top-view Point Distribution
Descriptor (PDD) grids.

biomass3 uses a 2-group, 9-descriptor PDD set (density group + distribution
group), replacing biomass2's fixed 3-channel recipe. All 9 are computed in one
pass per plot and cached; individual experiments then pick 1 or 3 of them as
the image channel(s).

Density group (point counts per top-view grid cell):
  D1 density              - all points, no height filter
  D2 band_density_0_1     - points with height-above-ground (HAG) in [0.0, 1.0) m
  D3 band_density_1_2     - points with HAG in [1.0, 2.0) m
  D4 band_density_2_3     - points with HAG in [2.0, 3.0) m

Distribution group (per-cell statistics of HAG, over all points in the cell):
  D5 hag_p05   - 5th percentile HAG
  D6 hag_p95   - 95th percentile HAG
  D7 hag_mean  - mean HAG
  D8 hag_std   - std. dev. of HAG
  D9 hag_skew  - skewness of HAG

Selected channels are rendered as a normal grayscale (1 channel) or RGB
(3 channel) image so the existing YOLO/CNN workflow can train without
changing the model input layer. The pixel values are synthetic feature
encodings, not natural image colors, so color augmentation must stay off.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Sequence, Tuple

import cv2
import laspy
import numpy as np
import pandas as pd
from scipy import ndimage

# Canonical PDD order: density group (D1-D4) then distribution group (D5-D9).
ALL_CHANNELS: Tuple[str, ...] = (
    "density",
    "band_density_0_1",
    "band_density_1_2",
    "band_density_2_3",
    "hag_p05",
    "hag_p95",
    "hag_mean",
    "hag_std",
    "hag_skew",
)

# D1..D9 labels used in experiment configs/reports.
CHANNEL_CODE = {name: f"D{i + 1}" for i, name in enumerate(ALL_CHANNELS)}
CODE_TO_CHANNEL = {code: name for name, code in CHANNEL_CODE.items()}

DEFAULT_CHANNELS: Tuple[str, ...] = ("density", "hag_p95", "hag_mean")

CHANNEL_DESCRIPTIONS: Dict[str, str] = {
    "density": "Point count per top-view grid cell (all heights)",
    "band_density_0_1": "Point count with height above local ground in 0.0-1.0 m",
    "band_density_1_2": "Point count with height above local ground in 1.0-2.0 m",
    "band_density_2_3": "Point count with height above local ground in 2.0-3.0 m",
    "hag_p05": "5th percentile height above local ground per grid cell",
    "hag_p95": "95th percentile height above local ground per grid cell",
    "hag_mean": "Mean height above local ground per grid cell",
    "hag_std": "Std. dev. of height above local ground per grid cell",
    "hag_skew": "Skewness of height above local ground per grid cell",
}

_DEFAULT_BAND_EDGES: Tuple[Tuple[float, float], ...] = ((0.0, 1.0), (1.0, 2.0), (2.0, 3.0))


@dataclass(frozen=True)
class RasterConfig:
    image_size: int = 320
    pixel_size: float = 0.125
    area_size: float = 40.0
    band_edges: Tuple[Tuple[float, float], ...] = field(default_factory=lambda: _DEFAULT_BAND_EDGES)
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


def _scatter_to_grid(series: pd.Series, height: int, width: int, fill: float = 0.0) -> np.ndarray:
    """Scatter a pixel-id-indexed pandas Series back into a dense (H, W) grid."""
    out = np.full(height * width, fill, dtype=np.float32)
    idx = series.index.to_numpy()
    out[idx] = series.to_numpy(dtype=np.float32, na_value=fill)
    return out.reshape(height, width)


class RubberTreeMultiChannelRasterizer:
    """Create physically meaningful 2D PDD grids from LAS point clouds."""

    channel_names = ALL_CHANNELS

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

        # --- density group: raw point counts, all-height and per HAG band ---
        density = np.bincount(pixel_ids, minlength=total_cells).reshape(height, width).astype(np.float32)

        ground = self._estimate_ground(z, pixel_ids, height, width)
        ground_flat = ground.reshape(-1)
        hag = np.maximum(z - ground_flat[pixel_ids], 0.0)

        band_grids = []
        for lo, hi in cfg.band_edges:
            mask = (hag >= lo) & (hag < hi)
            counts = np.bincount(pixel_ids[mask], minlength=total_cells)
            band_grids.append(counts.reshape(height, width).astype(np.float32))

        # --- distribution group: per-cell HAG stats via a single groupby ---
        df = pd.DataFrame({"pixel": pixel_ids, "hag": hag})
        grouped = df.groupby("pixel")["hag"]
        hag_p05 = _scatter_to_grid(grouped.quantile(0.05), height, width)
        hag_p95 = _scatter_to_grid(grouped.quantile(0.95), height, width)
        hag_mean = _scatter_to_grid(grouped.mean(), height, width)
        hag_std = _scatter_to_grid(grouped.std(), height, width)  # NaN->0 for single-point cells
        hag_skew = _scatter_to_grid(grouped.skew(), height, width)  # NaN->0 for cells with <3 points

        grid = np.dstack(
            (
                density,
                band_grids[0],
                band_grids[1],
                band_grids[2],
                hag_p05,
                hag_p95,
                hag_mean,
                hag_std,
                hag_skew,
            )
        ).astype(np.float32)

        meta.update(
            {
                "num_channels": len(ALL_CHANNELS),
                "channel_names": list(ALL_CHANNELS),
                "channel_codes": dict(CHANNEL_CODE),
                "channel_description": dict(CHANNEL_DESCRIPTIONS),
                "band_edges": [list(edge) for edge in cfg.band_edges],
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

    def select_channels(self, grid: np.ndarray, channel_order: Sequence[str]) -> np.ndarray:
        """Pick 1 or 3 named channels out of the full 9-channel grid, in order."""
        names = list(self.channel_names)
        idx = []
        for channel_name in channel_order:
            if channel_name not in names:
                raise ValueError(f"Unknown channel '{channel_name}'. Available: {names}")
            idx.append(names.index(channel_name))
        return grid[:, :, idx]

    def to_image(self, grid: np.ndarray, channel_order: Sequence[str] = DEFAULT_CHANNELS) -> np.ndarray:
        """Render 1 selected channel as grayscale or 3 selected channels as RGB."""
        channel_order = list(channel_order)
        if len(channel_order) not in (1, 3):
            raise ValueError(f"channel_order must have 1 or 3 entries, got {len(channel_order)}")

        selected = self.select_channels(grid, channel_order)
        planes = [
            _robust_uint8(
                selected[:, :, i],
                self.config.normalize_low_percentile,
                self.config.normalize_high_percentile,
            )
            for i in range(selected.shape[2])
        ]
        if len(planes) == 1:
            return planes[0]  # true single-channel grayscale image
        return np.dstack(planes)  # RGB, channel_order[0] -> R, [1] -> G, [2] -> B

    def save_image(
        self,
        grid: np.ndarray,
        output_path: str | Path,
        channel_order: Sequence[str] = DEFAULT_CHANNELS,
    ) -> None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = self.to_image(grid, channel_order=channel_order)
        if image.ndim == 2:
            cv2.imwrite(str(output_path), image)
        else:
            cv2.imwrite(str(output_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

    # Backward-compatible alias (biomass2 name).
    def save_rgb(
        self,
        grid: np.ndarray,
        output_path: str | Path,
        channel_order: Sequence[str] = DEFAULT_CHANNELS,
    ) -> None:
        self.save_image(grid, output_path, channel_order=channel_order)

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


def _parse_channels(value: str) -> Tuple[str, ...]:
    channels = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(channels) not in (1, 3):
        raise argparse.ArgumentTypeError("Expected 1 or 3 comma-separated channel names")
    resolved = tuple(CODE_TO_CHANNEL.get(c, c) for c in channels)
    unknown = [c for c in resolved if c not in ALL_CHANNELS]
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown channel(s) {unknown}. Available: {ALL_CHANNELS}")
    return resolved


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a 1- or 3-channel LiDAR PDD feature image from one LAS file."
    )
    parser.add_argument("input_las", type=str, help="Input .las/.laz file")
    parser.add_argument("--output_dir", type=str, default="raster_output", help="Output directory")
    parser.add_argument("--image_size", type=int, default=320, help="Output square image size")
    parser.add_argument("--pixel_size", type=float, default=0.125, help="Grid pixel size in meters")
    parser.add_argument("--area_size", type=float, default=40.0, help="Nominal plot size in meters")
    parser.add_argument("--ground_filter_size", type=int, default=9, help="Local minimum filter size in pixels")
    parser.add_argument(
        "--channels",
        type=_parse_channels,
        default=DEFAULT_CHANNELS,
        help=(
            "1 or 3 comma-separated channel names or codes, e.g. 'density,hag_p95,hag_mean' "
            "or 'D1,D6,D7'. Full list: " + ", ".join(f"{CHANNEL_CODE[c]}={c}" for c in ALL_CHANNELS)
        ),
    )
    parser.add_argument("--save_npy", action="store_true", help="Save resized 9-channel feature grid as .npy")
    parser.add_argument("--save_previews", action="store_true", help="Save one grayscale preview per PDD channel")
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

    rasterizer.save_image(resized_grid, image_path, channel_order=args.channels)
    meta.update(source_meta)
    meta["resized_to"] = int(args.image_size)
    meta["image_channel_order"] = list(args.channels)
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
