#!/usr/bin/env python3
"""
Train YOLOv11 on the biomass2 synthetic multi-channel RGB dataset.

The RGB channels are physical LiDAR features, so color augmentations are
disabled to preserve channel meaning.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def default_model_path() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "biomass1" / "notebooks_density" / "training" / "yolo11n.pt"
    if candidate.exists():
        return str(candidate)
    return "yolo11n.pt"


def build_arg_parser() -> argparse.ArgumentParser:
    script_dir = Path(__file__).resolve().parent
    default_data = script_dir.parent / "dataset_creation" / "yolov11" / "dataset_multichannel" / "data.yaml"
    default_project = script_dir / "runs" / "detect"

    parser = argparse.ArgumentParser(description="Train YOLOv11 on biomass2 multi-channel LiDAR images.")
    parser.add_argument("--data", type=str, default=str(default_data), help="Path to data.yaml")
    parser.add_argument("--model", type=str, default=default_model_path(), help="YOLO model/weights path")
    parser.add_argument("--project", type=str, default=str(default_project), help="Output project directory")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", type=str, default="", help="Device string, e.g. 0, cpu, cuda, mps. Empty = auto")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--name", type=str, default="rubber_multichannel_density_hag_dbh")
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--exist_ok", action="store_true", help="Reuse the run folder if it already exists")
    parser.add_argument("--resume", action="store_true", help="Resume training from the checkpoint in --model")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    model = YOLO(args.model)

    train_kwargs = {
        "data": args.data,
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": args.project,
        "name": args.name,
        "exist_ok": args.exist_ok,
        "resume": args.resume,
        "patience": args.patience,
        "degrees": 15.0,
        "translate": 0.05,
        "scale": 0.10,
        "shear": 0.0,
        "perspective": 0.0,
        "flipud": 0.0,
        "fliplr": 0.0,
        "mosaic": 0.0,
        "mixup": 0.0,
        "cutmix": 0.0,
        "copy_paste": 0.0,
        "auto_augment": "",
        "erasing": 0.0,
        "hsv_h": 0.0,
        "hsv_s": 0.0,
        "hsv_v": 0.0,
        "bgr": 0.0,
        "workers": args.workers,
        "save": True,
        "plots": True,
        "verbose": True,
        "lr0": 0.01,
        "lrf": 0.01,
        "momentum": 0.937,
        "weight_decay": 0.0005,
        "warmup_epochs": 3.0,
        "close_mosaic": 10,
    }
    if args.device:
        train_kwargs["device"] = args.device

    model.train(**train_kwargs)

    print("\nTraining complete")
    print(f"Run name: {args.name}")
    print(f"Project: {args.project}")
    print(f"Data: {args.data}")


if __name__ == "__main__":
    main()
