# Point Cloud Preprocessing Scripts

This directory contains optimized point cloud filtering scripts for processing LiDAR data with odometry.

## Active Production Scripts

### Main Filter (Recommended)
- **`filter_pointcloud_by_odom_optimized.py`** - Production-ready optimized filter
  - Uses Direct Normalization for hull expansion (500x faster than Minkowski sum)
  - Grid-based spatial indexing for fast point filtering
  - Processes 14.8M points in ~1.85 seconds
  - See [README_OPTIMIZED_FILTER.md](README_OPTIMIZED_FILTER.md) for details

### Utility Scripts
- **`organize_experiment_outputs.py`** - Organizes experimental output files into categorized folders

## Archive Directories

### `deprecated/`
Contains older filter implementations kept for reference:
- `filter_pointcloud_by_odom.py` - 3D normal plane approach (slow but handles sloped terrain)
- `filter_pointcloud_by_odom_2d.py` - Simple 2D approach (no buffer expansion)
- `filter_pointcloud_by_odom_grid.py` - Grid-based without buffer

### `experiments_scripts/`
Contains visualization and testing scripts used for development:
- Visualization scripts (`visualize_*.py`)
- Testing/comparison scripts (`test_*.py`)
- Documentation for experiments (README_*.md)

## Usage

### Basic Usage (Recommended)

```bash
python filter_pointcloud_by_odom_optimized.py \
    input.las \
    odom.txt \
    -o output.las \
    --grid-size 0.5 \
    --buffer 0.5 \
    --progress
```

### With Height Filtering

```bash
python filter_pointcloud_by_odom_optimized.py \
    input.las \
    odom.txt \
    -o output.las \
    --grid-size 0.5 \
    --buffer 0.5 \
    --min-height -2.0 \
    --max-height 5.0 \
    --progress
```

## Parameters

- `--grid-size`: Grid cell size in meters (default: 0.5m)
  - Smaller = more precise but slower
  - Recommended: 0.3-0.7m

- `--buffer`: Buffer distance for hull expansion (default: 0.5m)
  - Expands the convex hull boundary
  - Typical range: 0.2-2.0m

- `--min-height`, `--max-height`: Z-axis filtering (optional)

- `--progress` or `-p`: Show progress messages

## Performance

| Method | Time | Points (with 0.5m buffer) |
|--------|------|---------------------------|
| **Optimized (Recommended)** | **1.85s** | **9.6M** |
| Grid-based (no buffer) | 3.13s | 8.5M |
| 2D Direct (no buffer) | 10.97s | 8.5M |
| 3D Normal (Minkowski) | 20.35s | 8.7M |

The optimized filter is:
- **11x faster** than 3D method
- **6x faster** than 2D method
- Uses Direct Normalization (500x faster than Minkowski sum)

## Documentation

- [README_OPTIMIZED_FILTER.md](README_OPTIMIZED_FILTER.md) - Detailed documentation for the optimized filter
- [deprecated/](deprecated/) - Archive of older implementations
- [experiments_scripts/](experiments_scripts/) - Development and testing scripts

## Dependencies

- numpy
- scipy
- laspy (for LAS file I/O)
- Custom modules: `core.pjfunc`, `core.convexhull`

## Output Organization

Use `organize_experiment_outputs.py` to organize experimental files:

```bash
python organize_experiment_outputs.py --output-dir output
```

This creates:
```
output/
├── experiments/
│   ├── visualizations/
│   ├── point_clouds/
│   ├── reports/
│   └── timing/
├── scans.las          (main output)
├── scans.pcd
└── odom_*.txt
```

## For Development

If you need to run experiments or visualizations, use scripts from `experiments_scripts/`:

```bash
# Run comparison test
python experiments_scripts/test_all_methods.py input.las odom.txt

# Create visualizations
python experiments_scripts/visualize_grid_steps.py input.las odom.txt
```

## Migration Notes

If you were using older scripts:
- **Old 3D method** → Use optimized filter (11x faster, similar results with buffer)
- **Old 2D method** → Use optimized filter (6x faster, adds buffer expansion)
- **Old grid method** → Use optimized filter (1.7x faster, adds buffer expansion)

All old implementations are preserved in `deprecated/` for reference.
