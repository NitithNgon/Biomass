#!/usr/bin/env python3
"""
Master orchestrator for biomass3's 3 experiments (see biomass3/README.md).

  Experiment 1: yolov11m, one PDD channel at a time (D1..D9), 4-fold CV,
                optimizer="auto" (from COCO weights). Ranks the 9 PDDs by
                mean test mAP50-95, picks the best 3. Stays at ONE size (m)
                so every candidate channel gets the same treatment - a fair
                head-to-head. (Not warm-started, on purpose - see below.)

  Warm-start prep: the "warm-start channel" (default: density) trained the
                same way, at the 4 OTHER sizes (n, s, l, x) - so every size
                has its own from-scratch checkpoint to seed experiment 2/3's
                fine-tuning from. This is infrastructure for the next step,
                not a ranking - it reuses experiment 1's own dataset/channel.

  Experiments 2+3 (unified): best-3-channel image, EVERY size {n,s,m,l,x},
                4-fold CV, each (size, fold) warm-started from that SAME
                fold+size's warm-start-channel checkpoint, optimizer="SGD".
                All 5 sizes get identical treatment (matching-size,
                matching-fold warm-start), so this stays an uncofounded
                size-vs-accuracy comparison. The `m` row IS experiment 2
                (best-3-channel headline accuracy + runtime benchmark);
                the full 5-size sweep IS experiment 3. One training run
                each, not two.

This mirrors biomass2's own successful lineage: an optimizer="auto" (->
AdamW) run trained from scratch (density_v5_lightaug), then an
optimizer="SGD" fine-tune warm-started from it (multichannel_from_v5_v6hyp)
- applied per model size here, not just at the size biomass2 happened to use.

All runs share biomass3/dataset_creation/create_yolo_multichannel_dataset.py
for dataset construction and biomass3/yolov11/train_multichannel.py's
REFERENCE_HYPERPARAMS (copied from biomass2's multichannel_from_v5_v6hyp) for
every non-optimizer, non-init hyperparameter, so configs differ only by
input channels, model size, starting weights, and optimizer.

Every run's row records both the true held-out TEST split metrics
(evaluate_multichannel.evaluate_test_split - the honest generalization
number) and the internal VAL-split training-curve metrics at best/final
epoch (val_best_*/val_final_* - comparable to how biomass1/biomass2's own
results were reported). Report both; don't conflate them.

Progress is written incrementally to CSV after every run, and completed runs
(weights + metrics already on disk) are skipped on re-run, so this script is
safe to resume after an interruption. Per biomass3/CLAUDE.md's working rule,
this script never deletes an existing run/results file itself - clear stale
data by hand, after confirming with the user, before relaunching.

Usage:
    python biomass3/run_experiments.py --device 0
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence

import pandas as pd
import torch

BIOMASS3_DIR = Path(__file__).resolve().parent
DATASET_CREATION_DIR = BIOMASS3_DIR / "dataset_creation"
YOLOV11_DIR = BIOMASS3_DIR / "yolov11"
sys.path.insert(0, str(DATASET_CREATION_DIR))
sys.path.insert(0, str(DATASET_CREATION_DIR / "scripts"))
sys.path.insert(0, str(YOLOV11_DIR))

from benchmark_runtime import run_benchmark  # noqa: E402
from create_yolo_multichannel_dataset import build_dataset  # noqa: E402
from evaluate_multichannel import evaluate_test_split  # noqa: E402
from feature_cache import DEFAULT_CACHE_DIR, build_all_caches  # noqa: E402
from folds import Fold, build_folds  # noqa: E402
from plots_registry import discover_plots  # noqa: E402
from pointcloud_multichannel import ALL_CHANNELS, CHANNEL_CODE, CODE_TO_CHANNEL  # noqa: E402
from train_multichannel import REFERENCE_HYPERPARAMS, default_model_path  # noqa: E402
from ultralytics import YOLO  # noqa: E402

RESULTS_DIR = BIOMASS3_DIR / "results"
DATASETS_DIR = DATASET_CREATION_DIR / "yolov11" / "datasets"
RUNS_DETECT_DIR = YOLOV11_DIR / "runs" / "detect"

EXP1_CSV = RESULTS_DIR / "experiment1_single_channel.csv"
EXP1_RANKING_CSV = RESULTS_DIR / "experiment1_ranking.csv"
WARMSTART_PREP_CSV = RESULTS_DIR / "warmstart_checkpoints.csv"
WARMSTART_SELECTION_CSV = RESULTS_DIR / "warmstart_channel_selection.csv"
EXP2_CSV = RESULTS_DIR / "experiment2_best3_warmstart.csv"  # == the model_size=="m" rows of EXP3_CSV
EXP3_CSV = RESULTS_DIR / "experiment3_model_sizes.csv"
BEST3_JSON = RESULTS_DIR / "best3_channels.json"

MODEL_SIZES = ("n", "s", "m", "l", "x")
MODEL_SIZE_EXP1 = "m"  # the size the 9-channel ranking runs at
WARMSTART_SIZES = tuple(s for s in MODEL_SIZES if s != MODEL_SIZE_EXP1)  # n, s, l, x
IMGSZ = REFERENCE_HYPERPARAMS["imgsz"]
BOX_SIZE_METERS = 2.0

# From-scratch (COCO-init) runs use optimizer="auto", which resolves to
# AdamW(lr=0.002, momentum=0.9) on a dataset this size (confirmed by probing
# this exact ultralytics install) - matching density_v5_lightaug, the
# checkpoint biomass2's best multichannel run warm-started from. Every
# warm-started fine-tune (experiments 2+3) keeps "SGD", matching that same
# run's own recipe.
FROM_SCRATCH_OPTIMIZER = "auto"
WARMSTART_OPTIMIZER = "SGD"

# Default behavior: train ALL 3 best-3 channels at every size (not just one hardcoded channel),
# then let each size warm-start from whichever of the 3 actually transfers best for it -
# select_warmstart_channel_per_size() picks per size by mean test mAP50-95. --warmstart_channel
# overrides this to force one specific channel for every size instead (cheaper: skips training
# the other 2 candidates).


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def free_gpu() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def append_csv_row(path: Path, row: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def read_completed_run_names(csv_path: Path) -> set:
    if not csv_path.exists():
        return set()
    with open(csv_path, encoding="utf-8") as f:
        return {r["run_name"] for r in csv.DictReader(f)}


def read_val_curve_metrics(run_dir: Path) -> Dict:
    """Read Ultralytics' own training-curve results.csv: best- and final-epoch VAL-split
    metrics (comparable to how biomass1/biomass2's own headline numbers were reported)."""
    empty = {
        "val_best_epoch": None,
        "val_best_mAP50_95": None,
        "val_best_mAP50": None,
        "val_best_precision": None,
        "val_best_recall": None,
        "val_final_epoch": None,
        "val_final_mAP50_95": None,
        "val_final_mAP50": None,
        "val_final_precision": None,
        "val_final_recall": None,
        "epochs_completed": 0,
    }
    results_csv = run_dir / "results.csv"
    if not results_csv.exists():
        return empty

    df = pd.read_csv(results_csv)
    df.columns = [c.strip() for c in df.columns]
    if df.empty or "metrics/mAP50-95(B)" not in df.columns:
        return empty

    best = df.loc[df["metrics/mAP50-95(B)"].idxmax()]
    final = df.iloc[-1]
    return {
        "val_best_epoch": int(best["epoch"]),
        "val_best_mAP50_95": float(best["metrics/mAP50-95(B)"]),
        "val_best_mAP50": float(best["metrics/mAP50(B)"]),
        "val_best_precision": float(best["metrics/precision(B)"]),
        "val_best_recall": float(best["metrics/recall(B)"]),
        "val_final_epoch": int(final["epoch"]),
        "val_final_mAP50_95": float(final["metrics/mAP50-95(B)"]),
        "val_final_mAP50": float(final["metrics/mAP50(B)"]),
        "val_final_precision": float(final["metrics/precision(B)"]),
        "val_final_recall": float(final["metrics/recall(B)"]),
        "epochs_completed": int(len(df)),
    }


def exp1_run_name(channel: str, fold_index: int, size: str) -> str:
    """Name of the experiment-1-style checkpoint for one channel/fold/size.

    size==MODEL_SIZE_EXP1 reuses the plain name the 9-channel ranking sweep
    already trains under (no suffix); other sizes are the warm-start-prep
    extension, suffixed so they don't collide with the ranking run."""
    if size == MODEL_SIZE_EXP1:
        return f"exp1_{channel}_fold{fold_index}"
    return f"exp1_{channel}_yolo11{size}_fold{fold_index}"


def train_one(
    model_size: str,
    data_yaml: Path,
    run_name: str,
    device: str,
    optimizer: str,
    model_path_override: str | Path | None = None,
    epochs: int | None = None,
) -> Dict:
    """Train one YOLOv11 config; return the weights path + wall time.

    model_path_override, when given, is the starting checkpoint (a warm-start
    weights path) instead of the plain COCO yolo11{size}.pt."""
    weights_path = RUNS_DETECT_DIR / run_name / "weights" / "best.pt"
    t0 = time.time()
    if weights_path.exists():
        log(f"  [skip-train] {run_name} already has weights")
    else:
        model_path = str(model_path_override) if model_path_override else default_model_path(model_size)
        model = YOLO(model_path)
        kwargs = dict(REFERENCE_HYPERPARAMS)
        kwargs.update(
            {
                "data": str(data_yaml),
                "optimizer": optimizer,
                "project": str(RUNS_DETECT_DIR),
                "name": run_name,
                "exist_ok": True,
                "device": device,
                "workers": 8,
                "plots": True,
                "verbose": False,
            }
        )
        if epochs is not None:
            kwargs["epochs"] = epochs
        model.train(**kwargs)
        del model
        free_gpu()
    train_seconds = time.time() - t0
    return {"weights_path": weights_path, "train_seconds": train_seconds}


def evaluate_one(weights_path: Path, data_yaml: Path, device: str) -> Dict:
    metrics = evaluate_test_split(weights_path, data_yaml, imgsz=IMGSZ, device=device)
    free_gpu()
    return metrics


def benchmark_one(weights_path: Path, channels: Sequence[str], fold: Fold, dataset_dir: Path, device: str) -> Dict:
    image_paths = sorted((dataset_dir / "images" / "test").glob("*.jpg"))
    result = run_benchmark(
        weights_path,
        channels,
        fold.test,
        imgsz=IMGSZ,
        device=device,
        image_paths_for_inference=image_paths,
    )
    free_gpu()
    return {
        "preprocess_mean_s": result["preprocessing"]["mean_s"],
        "preprocess_sd_s": result["preprocessing"]["sd_s"],
        "inference_mean_s": result["inference"]["mean_s"],
        "inference_sd_s": result["inference"]["sd_s"],
        "peak_ram_delta_mb": result["peak_ram_delta_mb"],
        "peak_vram_mb": result["peak_vram_mb"],
        "model_size_mb": result["model_size_mb"],
        "num_params": result["num_params"],
    }


def ensure_best3_dataset(fold: Fold, best3: Sequence[str]) -> tuple[Path, Path]:
    """Build (once) or reuse the best-3-channel dataset for one fold; shared by experiments 2+3."""
    dataset_dir = DATASETS_DIR / "best3" / f"fold{fold.index}"
    data_yaml = dataset_dir / "data.yaml"
    if not data_yaml.exists():
        log(f"  building best-3-channel dataset for fold {fold.index}")
        build_dataset(fold, tuple(best3), dataset_dir, box_size_meters=BOX_SIZE_METERS, overwrite=True)
    return dataset_dir, data_yaml


def run_experiment1(folds: List[Fold], device: str) -> List[str]:
    """One PDD channel at a time, yolov11m, optimizer=auto, 4-fold CV. Returns the best-3 channels."""
    log("=== Experiment 1: single-channel PDD sweep (yolov11m, 9 channels x 4 folds) ===")
    completed = read_completed_run_names(EXP1_CSV)

    for channel in ALL_CHANNELS:
        for fold in folds:
            run_name = exp1_run_name(channel, fold.index, MODEL_SIZE_EXP1)
            if run_name in completed:
                log(f"[skip] {run_name} already recorded")
                continue

            dataset_dir = DATASETS_DIR / "exp1" / channel / f"fold{fold.index}"
            data_yaml = dataset_dir / "data.yaml"
            if not data_yaml.exists():
                log(f"  building dataset {run_name}")
                build_dataset(fold, (channel,), dataset_dir, box_size_meters=BOX_SIZE_METERS, overwrite=True)

            log(f"[train] {run_name}")
            train_info = train_one(MODEL_SIZE_EXP1, data_yaml, run_name, device, optimizer=FROM_SCRATCH_OPTIMIZER)
            log(f"[eval]  {run_name}")
            metrics = evaluate_one(train_info["weights_path"], data_yaml, device)
            val_curve = read_val_curve_metrics(RUNS_DETECT_DIR / run_name)

            row = {
                "run_name": run_name,
                "channel": channel,
                "channel_code": CHANNEL_CODE[channel],
                "fold": fold.index,
                "model_size": MODEL_SIZE_EXP1,
                "optimizer": FROM_SCRATCH_OPTIMIZER,
                **metrics,
                **val_curve,
                "train_seconds": round(train_info["train_seconds"], 2),
                "weights_path": str(train_info["weights_path"]),
                "data_yaml": str(data_yaml),
            }
            append_csv_row(EXP1_CSV, row)
            log(
                f"[done]  {run_name}: test mAP50-95={metrics['mAP50_95']:.4f} "
                f"(val best={val_curve['val_best_mAP50_95']}) P={metrics['precision']:.3f} R={metrics['recall']:.3f}"
            )

    return rank_experiment1()


def rank_experiment1() -> List[str]:
    """Aggregate exp1 CSV by channel (mean TEST mAP50-95 across folds) and pick the top 3."""
    df = pd.read_csv(EXP1_CSV)
    summary = (
        df.groupby("channel")[["mAP50_95", "mAP50", "precision", "recall", "f1"]]
        .agg(["mean", "std"])
        .reset_index()
    )
    summary.columns = ["_".join(c).strip("_") for c in summary.columns.to_flat_index()]
    summary = summary.sort_values("mAP50_95_mean", ascending=False).reset_index(drop=True)
    summary.insert(0, "rank", summary.index + 1)
    summary.to_csv(EXP1_RANKING_CSV, index=False)

    best3 = summary["channel"].head(3).tolist()
    with open(BEST3_JSON, "w", encoding="utf-8") as f:
        json.dump({"best3_channels": best3, "ranking_csv": str(EXP1_RANKING_CSV)}, f, indent=2)

    log(f"Experiment 1 ranking (by mean TEST mAP50-95 across {df['fold'].nunique()} folds):")
    for _, r in summary.iterrows():
        marker = "  <-- selected" if r["channel"] in best3 else ""
        log(
            f"  #{int(r['rank'])} {r['channel']:20s} "
            f"mAP50-95={r['mAP50_95_mean']:.4f}+/-{r['mAP50_95_std']:.4f}{marker}"
        )
    log(f"Best 3 channels: {best3}")
    return best3


def load_best3_channels() -> List[str]:
    if BEST3_JSON.exists():
        with open(BEST3_JSON, encoding="utf-8") as f:
            return json.load(f)["best3_channels"]
    return rank_experiment1()


def prepare_warmstart_checkpoints(folds: List[Fold], device: str, channels: Sequence[str]) -> None:
    """Train each of `channels` (single-channel, from-scratch, optimizer=auto) at every size
    other than MODEL_SIZE_EXP1 - that size's checkpoint already exists from experiment 1. Gives
    experiments 2+3 a matching-size, matching-fold checkpoint to warm-start every size from, for
    each candidate channel (so select_warmstart_channel_per_size() has something to compare)."""
    log(f"=== Warm-start prep: channels {list(channels)} at sizes {WARMSTART_SIZES} x 4 folds ===")
    completed = read_completed_run_names(WARMSTART_PREP_CSV)

    for channel in channels:
        dataset_dir = DATASETS_DIR / "exp1" / channel
        for size in WARMSTART_SIZES:
            for fold in folds:
                run_name = exp1_run_name(channel, fold.index, size)
                if run_name in completed:
                    log(f"[skip] {run_name} already recorded")
                    continue

                data_yaml = dataset_dir / f"fold{fold.index}" / "data.yaml"
                if not data_yaml.exists():
                    log(f"  building dataset {run_name}")
                    build_dataset(
                        fold, (channel,), dataset_dir / f"fold{fold.index}",
                        box_size_meters=BOX_SIZE_METERS, overwrite=True,
                    )

                log(f"[train] {run_name}")
                train_info = train_one(size, data_yaml, run_name, device, optimizer=FROM_SCRATCH_OPTIMIZER)
                log(f"[eval]  {run_name}")
                metrics = evaluate_one(train_info["weights_path"], data_yaml, device)
                val_curve = read_val_curve_metrics(RUNS_DETECT_DIR / run_name)

                row = {
                    "run_name": run_name,
                    "channel": channel,
                    "fold": fold.index,
                    "model_size": size,
                    "optimizer": FROM_SCRATCH_OPTIMIZER,
                    **metrics,
                    **val_curve,
                    "train_seconds": round(train_info["train_seconds"], 2),
                    "weights_path": str(train_info["weights_path"]),
                    "data_yaml": str(data_yaml),
                }
                append_csv_row(WARMSTART_PREP_CSV, row)
                log(f"[done]  {run_name}: test mAP50-95={metrics['mAP50_95']:.4f}")


def select_warmstart_channel_per_size(best3: Sequence[str]) -> Dict[str, str]:
    """For each model size, pick whichever of `best3` has the highest mean TEST mAP50-95 at that
    size - size==MODEL_SIZE_EXP1 uses experiment 1's own numbers (already covers all 9 channels
    there), other sizes use the warm-start-prep CSV. Lets each size warm-start from whichever
    single-channel checkpoint actually transfers best for it, instead of hardcoding one channel
    everywhere."""
    frames = []
    if EXP1_CSV.exists():
        df1 = pd.read_csv(EXP1_CSV)
        frames.append(df1[df1["channel"].isin(best3) & (df1["model_size"] == MODEL_SIZE_EXP1)])
    if WARMSTART_PREP_CSV.exists():
        df2 = pd.read_csv(WARMSTART_PREP_CSV)
        frames.append(df2[df2["channel"].isin(best3)])
    if not frames or all(f.empty for f in frames):
        raise RuntimeError(
            "No warm-start candidate data found - run experiment 1 and prepare_warmstart_checkpoints() first."
        )

    combined = pd.concat(frames, ignore_index=True)
    summary = combined.groupby(["model_size", "channel"])["mAP50_95"].mean().reset_index()
    summary = summary.sort_values(["model_size", "mAP50_95"], ascending=[True, False])
    summary.to_csv(WARMSTART_SELECTION_CSV, index=False)

    selection: Dict[str, str] = {}
    log("Warm-start channel selected per size (highest mean test mAP50-95 among best-3 candidates):")
    for size in MODEL_SIZES:
        size_rows = summary[summary["model_size"] == size]
        if size_rows.empty:
            raise RuntimeError(f"No warm-start candidate data for size '{size}' among channels {list(best3)}.")
        selection[size] = size_rows.iloc[0]["channel"]
        log(f"  {size}: {selection[size]} (mAP50-95={size_rows.iloc[0]['mAP50_95']:.4f})")
    return selection


def run_experiments_2_and_3(
    folds: List[Fold], best3: Sequence[str], device: str, warmstart_channel_by_size: Dict[str, str]
) -> None:
    """Best-3-channel image, EVERY size {n,s,m,l,x}, 4-fold CV, each warm-started from that same
    fold+size's warm-start checkpoint (channel chosen per size via warmstart_channel_by_size,
    typically from select_warmstart_channel_per_size()), optimizer=SGD, + runtime benchmark.
    Writes every row to EXP3_CSV; the model_size=='m' rows ARE experiment 2 (also copied to
    EXP2_CSV)."""
    log(f"=== Experiments 2+3: best-3 channels {best3}, warm-started sizes {MODEL_SIZES} x 4 folds ===")
    log(f"  warm-start channel per size: {warmstart_channel_by_size}")
    completed = read_completed_run_names(EXP3_CSV)

    for fold in folds:
        dataset_dir, data_yaml = ensure_best3_dataset(fold, best3)

        for size in MODEL_SIZES:
            run_name = f"exp23_warmstart_yolo11{size}_fold{fold.index}"
            if run_name in completed:
                log(f"[skip] {run_name} already recorded")
                continue

            warmstart_channel = warmstart_channel_by_size[size]
            warmstart_run = exp1_run_name(warmstart_channel, fold.index, size)
            warmstart_weights = RUNS_DETECT_DIR / warmstart_run / "weights" / "best.pt"
            if not warmstart_weights.exists():
                raise FileNotFoundError(
                    f"{run_name} needs {warmstart_weights} (the '{warmstart_channel}' checkpoint "
                    f"for fold {fold.index}, size {size}) as its warm-start source. Run experiment "
                    "1 and prepare_warmstart_checkpoints() first."
                )

            log(f"[train] {run_name} (warm-start: {warmstart_weights})")
            train_info = train_one(
                size, data_yaml, run_name, device,
                optimizer=WARMSTART_OPTIMIZER, model_path_override=warmstart_weights,
            )
            log(f"[eval]  {run_name}")
            metrics = evaluate_one(train_info["weights_path"], data_yaml, device)
            val_curve = read_val_curve_metrics(RUNS_DETECT_DIR / run_name)
            log(f"[bench] {run_name}")
            bench = benchmark_one(train_info["weights_path"], best3, fold, dataset_dir, device)

            row = {
                "run_name": run_name,
                "channels": ";".join(best3),
                "channel_codes": ";".join(CHANNEL_CODE[c] for c in best3),
                "fold": fold.index,
                "model_size": f"yolo11{size}",
                "optimizer": WARMSTART_OPTIMIZER,
                "warmstart_channel": warmstart_channel,
                "warmstart_weights": str(warmstart_weights),
                **metrics,
                **val_curve,
                "train_seconds": round(train_info["train_seconds"], 2),
                **bench,
                "weights_path": str(train_info["weights_path"]),
                "data_yaml": str(data_yaml),
            }
            append_csv_row(EXP3_CSV, row)
            log(
                f"[done]  {run_name}: test mAP50-95={metrics['mAP50_95']:.4f} test mAP50={metrics['mAP50']:.4f} "
                f"infer={bench['inference_mean_s'] * 1000:.1f}ms size={bench['model_size_mb']:.1f}MB"
            )

    write_experiment2_csv()


def write_experiment2_csv() -> None:
    """Experiment 2 == the model_size=='yolo11m' rows of experiment 3's warm-started sweep."""
    if not EXP3_CSV.exists():
        return
    df = pd.read_csv(EXP3_CSV)
    exp2 = df[df["model_size"] == f"yolo11{MODEL_SIZE_EXP1}"].copy()
    exp2.to_csv(EXP2_CSV, index=False)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run biomass3 experiments 1, 2, and 3 end-to-end.")
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--cache_dir", type=str, default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--skip_exp1", action="store_true", help="Reuse an existing best3_channels.json")
    parser.add_argument(
        "--force_best3",
        type=str,
        default=None,
        help="Comma-separated channel names/codes to use instead of experiment 1's ranking",
    )
    parser.add_argument(
        "--warmstart_channel",
        type=str,
        default=None,
        help=(
            "Force one single-channel checkpoint as the warm-start source for every size "
            "(skips training/comparing the other 2 best-3 candidates). Default: train all 3 "
            "best-3 channels at every size and auto-select whichever transfers best, per size."
        ),
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    log("Building PDD feature cache (12 plots, 9 channels each) if not already cached...")
    build_all_caches(Path(args.cache_dir))

    plot_names = [p.name for p in discover_plots()]
    folds = build_folds(plot_names)
    log(f"{len(folds)} folds built from {len(plot_names)} plots (train=7/val=2/test=3 each)")

    if args.force_best3:
        best3 = [CODE_TO_CHANNEL.get(c.strip(), c.strip()) for c in args.force_best3.split(",")]
        log(f"Using forced best-3 channels: {best3}")
    elif args.skip_exp1:
        best3 = load_best3_channels()
    else:
        best3 = run_experiment1(folds, args.device)

    if args.warmstart_channel:
        forced_channel = CODE_TO_CHANNEL.get(args.warmstart_channel, args.warmstart_channel)
        log(f"Forcing warm-start channel '{forced_channel}' for every size")
        prepare_warmstart_checkpoints(folds, args.device, [forced_channel])
        warmstart_channel_by_size = {size: forced_channel for size in MODEL_SIZES}
    else:
        prepare_warmstart_checkpoints(folds, args.device, best3)
        warmstart_channel_by_size = select_warmstart_channel_per_size(best3)

    run_experiments_2_and_3(folds, best3, args.device, warmstart_channel_by_size)

    log("All experiments complete.")
    log(f"  Experiment 1: {EXP1_CSV}")
    log(f"  Experiment 1 ranking: {EXP1_RANKING_CSV}")
    log(f"  Warm-start checkpoints: {WARMSTART_PREP_CSV}")
    if WARMSTART_SELECTION_CSV.exists():
        log(f"  Warm-start channel selection: {WARMSTART_SELECTION_CSV}")
    log(f"  Experiment 2: {EXP2_CSV}")
    log(f"  Experiment 3: {EXP3_CSV}")


if __name__ == "__main__":
    main()
