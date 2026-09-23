#!/usr/bin/env python3
"""
Train YOLOv11 on a biomass3 PDD (Point Distribution Descriptor) dataset.

Hyperparameters below are copied verbatim from
`biomass2/yolov11/runs/detect/multichannel_from_v5_v6hyp/args.yaml`, biomass2's
best-scoring multichannel run (mAP50-95 ~0.59), not from density_v6_improved:
density_v6_improved's epochs=25/patience=5 turned out to cut every biomass3 run
off after only 6-13 gradient steps (it happened to never trigger early stopping
itself, but yolov11m from generic COCO weights on ~7 training images does), so
every model was essentially untrained. epochs=150/patience=100 gives training
enough room to actually converge. Only --model, --data, --project, --name,
--device and --seed vary across biomass3 runs so that experiment 1/2/3 configs
differ only by input channels and model size, not by training recipe.

Images are synthetic PDD feature encodings (grayscale for 1-channel configs,
RGB for 3-channel configs), not natural photos, so color augmentation
(hsv_h/s/v, bgr) stays at 0 - inherited from biomass2's hard rule.

Optimizer: REFERENCE_HYPERPARAMS defaults to SGD (matching multichannel_from_v5_v6hyp's own
fine-tuning stage), but run_experiments.py overrides this per experiment. On this dataset size
(~7 train images -> 1 gradient step/epoch), optimizer="auto" resolves to AdamW(lr=0.002,
momentum=0.9) - confirmed by probing this exact ultralytics install - which is what
density_v5_lightaug (the checkpoint multichannel_from_v5_v6hyp itself warm-started from) used to
train from scratch. run_experiments.py therefore uses optimizer="auto" for every from-COCO run
(experiment 1, experiment 3) and optimizer="SGD" only for the one warm-started fine-tuning run
(experiment 2), mirroring that same auto-then-SGD lineage.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "yolov11_model"

# Reference hyperparameters from biomass2/yolov11/runs/detect/multichannel_from_v5_v6hyp/args.yaml
REFERENCE_HYPERPARAMS = {
    "epochs": 150,
    "patience": 100,
    "batch": 16,
    "imgsz": 320,
    "optimizer": "SGD",
    "seed": 0,
    "deterministic": True,
    "close_mosaic": 10,
    "amp": True,
    "cos_lr": False,
    "rect": False,
    "single_cls": False,
    "overlap_mask": True,
    "mask_ratio": 4,
    "dropout": 0.0,
    "lr0": 0.0005,
    "lrf": 0.01,
    "momentum": 0.937,
    "weight_decay": 0.0005,
    "warmup_epochs": 5.0,
    "warmup_momentum": 0.8,
    "warmup_bias_lr": 0.1,
    "box": 7.5,
    "cls": 0.5,
    "dfl": 1.5,
    "hsv_h": 0.0,
    "hsv_s": 0.0,
    "hsv_v": 0.0,
    "bgr": 0.0,
    "degrees": 20.0,
    "translate": 0.2,
    "scale": 0.5,
    "shear": 0.0,
    "perspective": 0.0,
    "flipud": 0.5,
    "fliplr": 0.5,
    "mosaic": 0.5,
    "mixup": 0.05,
    "cutmix": 0.0,
    "copy_paste": 0.0,
    "copy_paste_mode": "flip",
    "auto_augment": "randaugment",
    "erasing": 0.0,
}


def default_model_path(size: str = "m") -> str:
    candidate = MODEL_DIR / f"yolo11{size}.pt"
    if candidate.exists():
        return str(candidate)
    return f"yolo11{size}.pt"  # fall back to ultralytics auto-download


def build_arg_parser() -> argparse.ArgumentParser:
    script_dir = Path(__file__).resolve().parent
    default_project = script_dir / "runs" / "detect"

    parser = argparse.ArgumentParser(description="Train YOLOv11 on a biomass3 PDD dataset.")
    parser.add_argument("--data", type=str, required=True, help="Path to data.yaml")
    parser.add_argument("--model_size", type=str, default="m", choices=["n", "s", "m", "l", "x"])
    parser.add_argument("--model", type=str, default=None, help="Explicit model/weights path (overrides --model_size)")
    parser.add_argument("--project", type=str, default=str(default_project))
    parser.add_argument("--name", type=str, required=True)
    parser.add_argument("--epochs", type=int, default=REFERENCE_HYPERPARAMS["epochs"])
    parser.add_argument("--patience", type=int, default=REFERENCE_HYPERPARAMS["patience"])
    parser.add_argument("--batch", type=int, default=REFERENCE_HYPERPARAMS["batch"])
    parser.add_argument("--imgsz", type=int, default=REFERENCE_HYPERPARAMS["imgsz"])
    parser.add_argument(
        "--optimizer",
        type=str,
        default=REFERENCE_HYPERPARAMS["optimizer"],
        help="'SGD' (fine-tuning from a warm-start checkpoint) or 'auto' (from-scratch COCO-init runs)",
    )
    parser.add_argument("--device", type=str, default="0", help="Device string, e.g. 0, cpu. Empty = auto")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=REFERENCE_HYPERPARAMS["seed"])
    parser.add_argument("--exist_ok", action="store_true")
    parser.add_argument("--plots", action="store_true", default=True)
    parser.add_argument("--verbose", action="store_true", default=True)
    return parser


def train(args: argparse.Namespace) -> "YOLO":
    model_path = args.model or default_model_path(args.model_size)
    model = YOLO(model_path)

    train_kwargs = dict(REFERENCE_HYPERPARAMS)
    train_kwargs.update(
        {
            "data": args.data,
            "epochs": args.epochs,
            "patience": args.patience,
            "batch": args.batch,
            "imgsz": args.imgsz,
            "optimizer": args.optimizer,
            "project": args.project,
            "name": args.name,
            "exist_ok": args.exist_ok,
            "seed": args.seed,
            "workers": args.workers,
            "save": True,
            "plots": args.plots,
            "verbose": args.verbose,
        }
    )
    if args.device != "":
        train_kwargs["device"] = args.device

    model.train(**train_kwargs)
    return model


def main() -> None:
    args = build_arg_parser().parse_args()
    train(args)
    print("\nTraining complete")
    print(f"Run name: {args.name}")
    print(f"Project: {args.project}")
    print(f"Data: {args.data}")


if __name__ == "__main__":
    main()
