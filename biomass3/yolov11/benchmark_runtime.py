#!/usr/bin/env python3
"""
Efficiency benchmark for a trained biomass3 model: per-plot preprocessing
time (LAS -> selected-channel image) and inference time, measured separately,
warm-up excluded, mean +/- sd; plus peak RAM, peak VRAM, and model size.
Used by experiment 2 (yolov11m) and experiment 3 (n/s/m/l/x).
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import psutil
import torch
from ultralytics import YOLO

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_CREATION_DIR = SCRIPT_DIR.parent / "dataset_creation"
sys.path.insert(0, str(DATASET_CREATION_DIR))
sys.path.insert(0, str(DATASET_CREATION_DIR / "scripts"))

from plots_registry import PlotEntry, discover_plots  # noqa: E402
from pointcloud_multichannel import RasterConfig, RubberTreeMultiChannelRasterizer  # noqa: E402


def _now() -> float:
    return time.perf_counter()


def model_size_stats(weights_path: str | Path, model: YOLO) -> Dict[str, float]:
    size_bytes = Path(weights_path).stat().st_size
    num_params = sum(p.numel() for p in model.model.parameters())
    return {"model_size_mb": size_bytes / (1024 * 1024), "num_params": int(num_params)}


def benchmark_preprocessing(
    entries: Sequence[PlotEntry],
    channels: Sequence[str],
    config: RasterConfig,
    n_warmup: int = 1,
    n_repeats: int = 3,
) -> List[float]:
    """Time the full LAS -> selected-channel-image pipeline, per plot."""
    rasterizer = RubberTreeMultiChannelRasterizer(config)
    times: List[float] = []

    for entry in entries:
        for rep in range(n_warmup + n_repeats):
            t0 = _now()
            points, _ = rasterizer.load_pointcloud(entry.las_path)
            grid, _meta = rasterizer.rasterize(points)
            resized = rasterizer.resize_grid(grid)
            _image = rasterizer.to_image(resized, channel_order=channels)
            elapsed = _now() - t0
            if rep >= n_warmup:
                times.append(elapsed)
    return times


def benchmark_inference(
    model: YOLO,
    image_paths: Sequence[Path],
    imgsz: int,
    device: str,
    n_warmup: int = 2,
    n_repeats: int = 10,
) -> List[float]:
    """Time model inference on a fixed set of images, warm-up excluded."""
    times: List[float] = []
    if not image_paths:
        return times

    # Warm-up: CUDA kernel compilation / cudnn autotune, not counted.
    for _ in range(n_warmup):
        model.predict(source=str(image_paths[0]), imgsz=imgsz, device=device, verbose=False)

    for _ in range(n_repeats):
        for image_path in image_paths:
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t0 = _now()
            model.predict(source=str(image_path), imgsz=imgsz, device=device, verbose=False)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            times.append(_now() - t0)
    return times


def _summarize(times: Sequence[float]) -> Dict[str, float]:
    if not times:
        return {"mean_s": float("nan"), "sd_s": float("nan"), "n": 0}
    arr = np.asarray(times, dtype=np.float64)
    return {"mean_s": float(arr.mean()), "sd_s": float(arr.std(ddof=0)), "n": int(arr.size)}


def run_benchmark(
    weights_path: str | Path,
    channels: Sequence[str],
    test_plot_names: Sequence[str],
    imgsz: int = 320,
    device: str = "0",
    image_paths_for_inference: Sequence[Path] | None = None,
    config: RasterConfig | None = None,
) -> Dict:
    """Full efficiency benchmark: preprocessing + inference + memory + model size."""
    config = config or RasterConfig(image_size=imgsz)
    all_entries = {e.name: e for e in discover_plots()}
    entries = [all_entries[name] for name in test_plot_names if name in all_entries]

    process = psutil.Process(os.getpid())
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    ram_before = process.memory_info().rss

    preprocess_times = benchmark_preprocessing(entries, channels, config)

    model = YOLO(str(weights_path))
    if image_paths_for_inference is None:
        raise ValueError("image_paths_for_inference is required (rendered test-split images)")
    inference_times = benchmark_inference(model, list(image_paths_for_inference), imgsz=imgsz, device=device)

    ram_peak = process.memory_info().rss
    vram_peak_mb = (
        torch.cuda.max_memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else None
    )

    result = {
        "preprocessing": _summarize(preprocess_times),
        "inference": _summarize(inference_times),
        "peak_ram_mb": (ram_peak - ram_before) / (1024 * 1024) + ram_before / (1024 * 1024),
        "peak_ram_delta_mb": (ram_peak - ram_before) / (1024 * 1024),
        "peak_vram_mb": vram_peak_mb,
        **model_size_stats(weights_path, model),
    }
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark preprocessing + inference runtime for a trained model.")
    parser.add_argument("--weights", type=str, required=True)
    parser.add_argument("--channels", type=str, required=True, help="Comma-separated channel names")
    parser.add_argument("--test_plots", type=str, required=True, help="Comma-separated plot names")
    parser.add_argument("--test_images_dir", type=str, required=True, help="Dir with rendered test-split images")
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--output_json", type=str, default=None)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    channels = tuple(c.strip() for c in args.channels.split(","))
    test_plots = tuple(p.strip() for p in args.test_plots.split(","))
    image_paths = sorted(Path(args.test_images_dir).glob("*.jpg"))

    result = run_benchmark(
        args.weights,
        channels,
        test_plots,
        imgsz=args.imgsz,
        device=args.device,
        image_paths_for_inference=image_paths,
    )
    print(json.dumps(result, indent=2))
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
