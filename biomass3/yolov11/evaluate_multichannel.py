#!/usr/bin/env python3
"""
Evaluate a trained YOLOv11 checkpoint on a dataset's held-out test split.

Returns precision / recall / F1 / mAP50 / mAP50-95, computed by Ultralytics'
own validator (box matching, greedy IoU-based TP/FP/FN) on `split="test"`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

from ultralytics import YOLO


def evaluate_test_split(
    weights_path: str | Path,
    data_yaml: str | Path,
    imgsz: int = 320,
    device: str = "0",
    project: str | None = None,
    name: str | None = None,
    plots: bool = False,
) -> Dict[str, float]:
    model = YOLO(str(weights_path))
    val_kwargs = dict(
        data=str(data_yaml),
        split="test",
        imgsz=imgsz,
        plots=plots,
        verbose=False,
    )
    if device != "":
        val_kwargs["device"] = device
    if project:
        val_kwargs["project"] = project
    if name:
        val_kwargs["name"] = name

    results = model.val(**val_kwargs)
    box = results.box
    precision = float(box.mp)
    recall = float(box.mr)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mAP50": float(box.map50),
        "mAP50_95": float(box.map),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a YOLOv11 checkpoint on a dataset's test split.")
    parser.add_argument("--weights", type=str, required=True)
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--device", type=str, default="0")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    metrics = evaluate_test_split(args.weights, args.data, imgsz=args.imgsz, device=args.device)
    for key, value in metrics.items():
        print(f"{key}: {value:.4f}")


if __name__ == "__main__":
    main()
