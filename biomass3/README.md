# biomass3: PDD-group experiments (density vs. distribution), no DBH/SFS

`biomass3` is a scoped-down fork of `biomass2` for a different set of experiments. Two things
`biomass2`/the thesis proposal describe are **out of scope here**:

- **No DBH estimation.** Detection only (tree centres). There is no DBH stage, no patch builder,
  no `run_dbh_pipeline.py`.
- **No Sequential Forward Selection (SFS).** PDD selection here is done by training a
  single-channel detector per candidate descriptor and ranking by test-set accuracy (experiment 1
  below), not by the 27-round SFS loop. (Mahalanobis-distance-based class separability was
  mentioned as a possible alternative PDD-selection method to explore later; it is **not**
  implemented in this repo.)

## PDD set: 2 groups, 9 descriptors

Replaces biomass2's fixed 3-channel recipe (`density`, `hag_p95`, `dbh_band_density`). Computed in
`dataset_creation/scripts/pointcloud_multichannel.py`, one pass per plot, all 9 at once:

| Code | Name | Group | Definition |
|------|------|-------|------------|
| D1 | `density` | density | point count per cell, all heights |
| D2 | `band_density_0_1` | density | point count, height-above-ground (HAG) in [0.0, 1.0) m |
| D3 | `band_density_1_2` | density | point count, HAG in [1.0, 2.0) m |
| D4 | `band_density_2_3` | density | point count, HAG in [2.0, 3.0) m |
| D5 | `hag_p05` | distribution | 5th percentile HAG per cell |
| D6 | `hag_p95` | distribution | 95th percentile HAG per cell |
| D7 | `hag_mean` | distribution | mean HAG per cell |
| D8 | `hag_std` | distribution | std. dev. of HAG per cell |
| D9 | `hag_skew` | distribution | skewness of HAG per cell |

Each experiment picks 1 or 3 of these as the image channel(s): 1 -> a true single-channel
grayscale image (matches biomass1's density approach - Ultralytics still loads it as 3 identical
channels via `cv2.imread`, so the pretrained YOLO input layer is unchanged); 3 -> RGB, channel
order = R,G,B. Color augmentation (`hsv_h/s/v`, `bgr`) stays at 0 either way, same hard rule as
biomass2, since pixel values are physical features, not natural colors.

Ground estimate, percentile-clip normalization (1st-99th percentile per channel, per image), image
size (320 px), pixel size (0.125 m/px, ~40x40 m plots) and YOLO box size (2.0 m) are unchanged from
biomass2.

## Dataset: 12 plots, k=4 plot-level cross-validation, train=7/val=2/test=3

`dataset_creation/plots_registry.py` discovers the same 12 LAS/CSV plot pairs biomass1/biomass2
use (`biomass1/notebooks_density/processed/*_rotated.las` + `biomass1/dataset/ข้อมูลแปลง/<plot>/DBHaverage.csv`).

`dataset_creation/folds.py` builds 4 folds, each partitioning **all 12 plots** into train=7 /
val=2 / test=3, never splitting a plot across tiles since trees within a plot are spatially
correlated (val is Ultralytics' internal validation split, used for early stopping only; test is
the held-out set accuracy is reported on; the same folds serve every model). The 12 plots are
shuffled once with a fixed seed and rotated by 3 positions per fold. Every plot lands in `test`
in exactly one fold (4x3=12, full coverage on the split that matters for reporting); `val` only
gets 4x2=8<12, so 8 of the 12 plots get a val turn and 4 never do. Train/val/test are always
disjoint within a fold (no leakage).

`dataset_creation/feature_cache.py` rasterizes each plot's LAS file **once** into the full
9-channel grid (~2s/plot) and caches it (`dataset_creation/cache/`, gitignored) so all 40
fold x channel-set combinations across the 3 experiments just slice cached channels instead of
re-parsing multi-million-point LAS files 40 times.

`dataset_creation/create_yolo_multichannel_dataset.py`'s `build_dataset(fold, channels, out_dir)`
builds one YOLO dataset dir (images/labels/data.yaml) from the cache for a given fold + channel
selection. CLI:

```bash
python biomass3/dataset_creation/create_yolo_multichannel_dataset.py \
  --fold 0 --channels density,hag_p95,hag_mean \
  --output_dir biomass3/dataset_creation/yolov11/datasets/manual/fold0_dhm
```

`--channels` also accepts PDD codes (`D1,D6,D7`).

## Training hyperparameters

Fixed in `yolov11/train_multichannel.py`'s `REFERENCE_HYPERPARAMS`, copied verbatim from
`biomass2/yolov11/runs/detect/multichannel_from_v5_v6hyp/args.yaml` - biomass2's best-scoring
multichannel run (mAP50-95 ~0.59), **not** `density_v6_improved`: an earlier version of this
pipeline used `density_v6_improved`'s epochs=25/patience=5, and every run early-stopped after only
6-13 gradient steps (yolov11m from generic COCO weights on ~7 training images just doesn't improve
fast enough epoch-to-epoch to keep resetting a patience-5 counter, unlike `density_v6_improved`
itself, which happened to keep improving throughout its full 25-epoch budget and never triggered
patience at all) - so every model came out essentially untrained (mAP50-95 ~0.0001-0.0007). Current
recipe: epochs=150, patience=100, batch=16, imgsz=320, lr0=0.0005, geometric aug (degrees=20,
translate=0.2, scale=0.5, flipud/fliplr=0.5, mosaic=0.5, mixup=0.05, randaugment, erasing=0.0),
color aug off. Every biomass3 run uses these same hyperparameters; only input channels, model size,
starting weights and optimizer vary between configs, per experiment (below).

**Optimizer differs by stage, not by accident.** `multichannel_from_v5_v6hyp` (biomass2's best run)
warm-started from `density_v5_lightaug`, which itself was trained from scratch with `optimizer=
auto`. On a dataset this size (~7 train images -> 1 gradient step/epoch), `auto` resolves to
`AdamW(lr=0.002, momentum=0.9)` (confirmed by probing this exact ultralytics install) - not SGD. So
the real successful lineage is: **auto/AdamW to train a domain checkpoint from scratch, then SGD to
fine-tune from it**. biomass3 mirrors that at every model size (biomass2 only did it at the one size
it happened to use): every from-scratch, COCO-init run (experiment 1, and warm-start prep) uses
`optimizer="auto"`; every warm-started fine-tune (experiments 2+3) uses `optimizer="SGD"`.

Starting weights: from-scratch runs start from plain pretrained COCO checkpoints in
`yolov11_model/yolo11{n,s,m,l,x}.pt` (repo root) - not the biomass1 transfer-learning weights
biomass2 used, since biomass3's channel set differs from biomass2's and there's no matching biomass1
checkpoint for most of it. Warm-started runs (experiments 2+3) instead start from a biomass3-grown
checkpoint - see below.

## The pipeline (`run_experiments.py`)

**Experiment 1 - PDD ranking.** yolov11m, one channel at a time (D1..D9), COCO-init,
`optimizer="auto"`, 4-fold CV = 36 runs. Same starting point for every candidate channel, so it
stays a fair head-to-head (only the descriptor varies) - deliberately *not* warm-started, even
though warm-starting clearly helps overall, because giving different channels different starting
points would confound "which descriptor is best" with "which checkpoint happened to transfer
better." Each (channel, fold) is trained then evaluated on that fold's held-out test split
(precision, recall, F1, mAP50, mAP50-95 via Ultralytics' own validator), plus the internal
training-time val-split metrics at best/final epoch (`val_best_*`/`val_final_*` - the same kind of
number biomass1/biomass2's own headline results report; see the note on val vs. test below).
Results: `results/experiment1_single_channel.csv` (one row per run). Ranked by mean **test**
mAP50-95 across the 4 folds: `results/experiment1_ranking.csv`. Top 3 channels ->
`results/best3_channels.json`.

**Warm-start prep.** Experiments 2+3 need a same-size, same-fold, from-scratch checkpoint to
warm-start every model size from - experiment 1 only provides that at `m`. By default, **all 3
best-3 channels** are trained (COCO-init, `optimizer="auto"`) at the 4 *other* sizes (n, s, l, x) x
4 folds = 3 x 4 x 4 = 48 runs (not a re-ranking of all 9 channels at every size - that would be 5x
the cost for no change in which 3 win; just the 3 already-selected candidates, at every size).
Results: `results/warmstart_checkpoints.csv`. `select_warmstart_channel_per_size()` then picks,
**per size**, whichever of the 3 has the highest mean test mAP50-95 at that size (`m` uses
experiment 1's own numbers, which already cover all 3) - different sizes can transfer best from
different channels, so this doesn't hardcode one channel everywhere. Selection written to
`results/warmstart_channel_selection.csv`. Pass `--warmstart_channel <name>` to skip all of this
and force one specific channel (e.g. `density`, mirroring `density_v5_lightaug` exactly) for every
size instead - cheaper (16 runs instead of 48: only that one channel gets trained at the 4 other
sizes) but not empirically chosen.

**Experiments 2+3 (unified) - best-3-channel accuracy + efficiency, every size, warm-started.**
Best-3-channel image, sweep model size {n, s, m, l, x}, 4-fold CV = 20 runs. Each (size, fold) is
warm-started from that **same size and same fold's** warm-start checkpoint (per the selection
above, or the forced `--warmstart_channel`) with `optimizer="SGD"`. Fold-matching matters for
correctness: using a *different* fold's checkpoint would mean that fold's held-out test plots had
already been training data for the warm-start weights, silently leaking test data. Size-matching
matters for fairness: every size gets the *same kind* of head start (its own matching-size
checkpoint), so this stays an uncofounded size-vs-accuracy comparison - unlike giving only one size
a warm start and leaving the rest on COCO-init. Accuracy + val-curve metrics, plus a runtime
benchmark: preprocessing time (LAS -> selected-channel image, warm-up excluded) and inference time
(warm-up excluded), both mean +/- sd; peak RAM (psutil) and peak VRAM
(`torch.cuda.max_memory_allocated`); model size (MB + parameter count). All 20 rows ->
`results/experiment3_model_sizes.csv`; the `model_size=="yolo11m"` rows are also copied to
`results/experiment2_best3_warmstart.csv` (the best-3-channel headline accuracy number) - one
training run each, not two.

**Val vs. test - report both, don't conflate them.** Every row has both `mAP50`/`mAP50_95`/etc.
(the true held-out **test**-split numbers - the honest generalization measure) and
`val_best_mAP50`/`val_final_mAP50`/etc. (the **training-time val-split** numbers, comparable to
what biomass1/biomass2's own results report). These are not interchangeable: biomass2's headline
`multichannel_from_v5_v6hyp` mAP50=0.993 is a *val*-split number, and biomass2's 70/15/15 split
gives it only 1 validation image - a single-image val mAP saturates easily and isn't a rigorous
generalization measure. biomass3's `test`-split numbers are measured on 3 plots per fold the model
never saw during training or checkpoint selection - stricter and more meaningful, but not the same
kind of number. For a comparison table against biomass1/biomass2, use `val_best_mAP50` for an
apples-to-apples column and `mAP50` (test) as the honest one, both clearly labeled.

Run everything end-to-end:

```bash
conda activate open3d_env
python biomass3/run_experiments.py --device 0
```

This builds the feature cache, runs experiment 1, ranks it and picks the best 3 channels, prepares
warm-start checkpoints for all 3 best channels at every size and picks the best-transferring one
per size, then runs experiments 2+3 together (104 runs total: 36 + 48 + 20). Progress is appended
to the result CSVs after every single run, and a run already recorded (weights + CSV row present)
is skipped - safe to re-run after an interruption. **This script never deletes an existing run or
result file itself** - see `CLAUDE.md`'s working rule. To skip re-running experiment 1 and reuse a
previous ranking: `--skip_exp1`. To force a specific 3-channel set instead of experiment 1's
ranking (e.g. to try a literature-motivated set): `--force_best3 D1,D6,D7`. To skip the per-size
warm-start comparison and force one channel everywhere instead (cheaper: 72 runs total, 36 + 16 +
20): `--warmstart_channel density` (or a `D`-code) - only affects warm-start prep and experiments
2+3, not experiment 1's ranking.

## What's deliberately not here (vs. biomass2 / the thesis proposal)

- DBH stage (module 5), DBH patch builder, `DBHaverage.csv`'s DBH column - unused, only X/Y.
- SFS loop / Mahalanobis-distance PDD selection - PDD selection here is trained-accuracy ranking
  (experiment 1) instead.
- Biomass stage (module 6).
- The full thesis eval protocol (greedy NN centre matching, TDR, localization error, paired
  significance tests, exhaustive-vs-SFS comparison) - experiment metrics here are Ultralytics'
  own P/R/F1/mAP, not that full protocol.
