# CLAUDE.md (biomass3)

## What this is

`biomass3` detects individual rubber trees in handheld-LiDAR top-view plot images with a
multi-channel YOLOv11. Each grid cell of a plot gets 1 or 3 selected Point Distribution Descriptors
(PDDs) as image channel(s); the model is trained to draw one fixed-size box per tree centre.
Detection only - no DBH estimation, no SFS/Mahalanobis-based descriptor selection (that's done by
training a single-channel detector per descriptor and ranking by test mAP - see experiment 1
below). Full pipeline documentation (PDD definitions, dataset/fold construction, all 3
experiments): `biomass3/README.md`.

## Required input data (not included in this folder)

`biomass3/dataset_creation/plots_registry.py` expects, at fixed relative paths from this folder:

- `../biomass1/notebooks_density/processed/*_rotated.las` - 12 rubber-plantation LiDAR plots
- `../biomass1/dataset/ข้อมูลแปลง/<plot>/DBHaverage.csv` - tree X/Y labels per plot (only the X/Y
  columns are used; any DBH column is ignored)
- `../yolov11_model/yolo11{n,s,m,l,x}.pt` - pretrained COCO checkpoints, the training starting
  point for every run. If a file is missing here, `train_multichannel.py` falls back to plain
  `yolo11{size}.pt` and lets Ultralytics auto-download it (needs internet access).

`plots_registry.py` derives these as `Path(__file__).resolve().parents[2] / ...`, i.e. two levels
above `biomass3/` - so this folder must sit at `<root>/biomass3/` with the LAS/CSV data at
`<root>/biomass1/...` and the checkpoints at `<root>/yolov11_model/...`. If that data lives
somewhere else on this machine, symlink/copy it into that layout, or pass `--plots_dir`/`--csv_dir`
explicitly to `dataset_creation/create_yolo_multichannel_dataset.py` (the higher-level
`run_experiments.py` orchestrator doesn't currently expose those overrides).

## Environment

- Needs: `laspy`, `opencv-python`, `numpy`, `pandas`, `scipy`, `ultralytics`, `torch` (+ CUDA for
  GPU training), `psutil`. Exact pinned versions: `requirements_clean.txt` at the repo root.
- The conda env name is not hardcoded anywhere in the code - activate whatever env on this machine
  already has those packages.
- `psutil` is only used by `yolov11/benchmark_runtime.py` (experiments 2/3's RAM tracking) - the
  package most likely to need installing on an otherwise-complete env.
- Training hyperparameters (`train_multichannel.py`'s `REFERENCE_HYPERPARAMS`) were validated
  against ultralytics 8.4.x's `model.train()` kwargs (e.g. `cutmix`, `copy_paste_mode`). Smoke-test
  one short run before trusting a full batch if this machine has a very different version.
- GPU: everything defaults to `--device 0` (first CUDA GPU). Pass `--device cpu` if there's no GPU
  - works, but 150-epoch x 104-run batches will be far slower.

## First run on a new machine

```bash
conda activate <this-machine's-env-name>
python biomass3/dataset_creation/feature_cache.py    # rasterizes the 12 plots once, ~1-2 min
python biomass3/dataset_creation/folds.py             # sanity check: prints the 4 folds + coverage
python biomass3/run_experiments.py --device 0         # full 104-run batch; likely several hours
```

`run_experiments.py` is resumable: if interrupted, rerunning it skips any run whose weights *and*
CSV row already exist, and picks up where it left off.

## Hard rule: no color augmentation

Image channels are physical LiDAR features (point density, height-above-ground statistics), not
real colors, so color jitter corrupts what they mean. `hsv_h`, `hsv_s`, `hsv_v`, `bgr` must stay at
0 in any training config. Geometric/mosaic/mixup augmentation is fine.

## Working rule for this project

**Never delete an existing trained run or results file (`yolov11/runs/detect/*`,
`results/*.csv`) to make way for a re-run - even when a code/config fix makes the old run
technically invalid. Ask first and say exactly what would be lost.** Learned the hard way: a
complete 56-run, ~5-hour training batch was deleted via `rm -rf` without asking, to make way for a
k-fold split fix, and turned out not to be locally recoverable (`rm -rf` bypasses the Recycle Bin).
If a fix invalidates prior results, say what's now stale and let the user decide whether to keep it
aside or clear it - don't treat it as obvious cleanup.

## Current design (summary - see README.md for full detail)

- **PDD set**: 9 descriptors in 2 groups. D1-D4 = density (D1 all-height point count; D2/D3/D4 =
  point count in height-above-ground bands 0-1/1-2/2-3 m). D5-D9 = per-cell height-above-ground
  distribution stats (p05, p95, mean, std, skew). All 9 computed and cached per plot in one pass
  (`dataset_creation/feature_cache.py`); each experiment picks 1 or 3 as image channel(s).
- **Cross-validation**: k=4, plot-level, each fold = 7 train / 2 val (early-stopping only, never
  used for the reported accuracy) / 3 test. Same 4 folds serve every model in every experiment. A
  plot is never split across tiles - each plot rasterizes to exactly one image, assigned wholly to
  one split.
- **Training recipe**: epochs=150, patience=100, batch=16, imgsz=320, lr0=0.0005, aggressive
  geometric augmentation (degrees=20, translate=0.2, scale=0.5, flipud/fliplr=0.5, mosaic=0.5,
  mixup=0.05, randaugment) - same for every run; input channels, model size, starting weights and
  optimizer vary by experiment.
- **Optimizer**: `auto` (-> `AdamW(lr=0.002, momentum=0.9)` on this dataset size, confirmed by
  probing) for every from-scratch, COCO-init run (experiment 1 + warm-start prep); `SGD` for every
  warm-started fine-tune (experiments 2+3). Mirrors biomass2's own successful lineage:
  `density_v5_lightaug` (auto/AdamW, from scratch) -> `multichannel_from_v5_v6hyp` (SGD, fine-tuned
  from it) - applied at every model size here, not just the one size biomass2 happened to use.
- **Pipeline** (`run_experiments.py`, 104 runs total by default):
  1. **Experiment 1** - yolov11m x 9 single channels x 4 folds, COCO-init, `auto` -> rank by mean
     test mAP50-95, pick best 3 (uniform init across all 9 candidates, so it stays a fair
     comparison - deliberately not warm-started). 36 runs.
  2. **Warm-start prep** - by default, **all 3 best-3 channels** x the 4 *other* sizes (n,s,l,x) x
     4 folds, COCO-init, `auto` (experiment 1 already covers `m` for all 3). 48 runs. (Not a
     re-ranking of all 9 channels at every size - 5x the cost for no change in which 3 win; just
     the 3 already-selected candidates, everywhere.) `select_warmstart_channel_per_size()` then
     picks, per size, whichever of the 3 transfers best there (different sizes can favor different
     channels) - written to `results/warmstart_channel_selection.csv`. `--warmstart_channel
     <name>` skips this and forces one channel everywhere instead (16 runs, not empirically
     chosen).
  3. **Experiments 2+3 (unified)** - best-3-channel image x model size {n,s,m,l,x} x 4 folds, each
     (size, fold) warm-started from that *same size and same fold's* selected (or forced)
     checkpoint - never a different fold's, which would leak that fold's test plots into the
     warm-start weights; never a different size's, which would give one size an unfair head start
     - `SGD`, + runtime benchmark. The `m` rows are experiment 2 (best-3-channel headline
     accuracy); the full 5-size sweep is experiment 3. 20 runs.
- **Val vs. test**: every row records both the true held-out test-split metrics (the honest
  number) and the internal training-time val-split metrics at best/final epoch (comparable to how
  biomass1/biomass2's own results were reported - biomass2's headline numbers are val-split, and
  its split gives only 1 validation image, which saturates mAP easily). Don't conflate the two.
