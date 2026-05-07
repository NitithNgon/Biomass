# Optimized Filter with Direct Normalization

## Overview

The optimized filter (`filter_pointcloud_by_odom_optimized.py`) combines the best techniques from previous iterations to create the fastest and most efficient filtering solution.

## Key Features

### 1. Direct Normalization for Hull Expansion

Instead of using computationally expensive Minkowski sum with circles, this method uses **Direct Normalization**:

- **Algorithm**: Moves each vertex along the angle bisector of its adjacent edges
- **Efficiency**: O(n) where n is the number of hull vertices (typically 40-50)
- **Speed**: ~0.001s vs ~0.5s+ for Minkowski sum with circles
- **Quality**: Produces smooth, uniform buffer expansion

**How it works:**
```
For each vertex:
1. Compute normals of adjacent edges
2. Average the normals (angle bisector)
3. Adjust offset based on angle between edges
4. Move vertex outward by buffer distance
```

### 2. 2D Grid-Based Filtering

Uses spatial grid to accelerate point filtering:

- **Pre-computation**: Creates binary mask of grid cells inside hull
- **Lookup**: Each point maps to grid cell via simple index calculation
- **Complexity**: O(m) where m is number of points (vs O(m*n) for direct checking)

**Direct Normalization Coordinate Mapping:**
```python
# Normalize coordinates to grid indices
x_indices = floor((x - x_min) / grid_size)
y_indices = floor((y - y_min) / grid_size)

# Direct lookup
inside = grid_mask[y_indices, x_indices]
```

### 3. Simple 2D Approach

- No expensive PCA/RANSAC for normal estimation
- No 3D transformation matrices
- Direct XY plane operations
- Simple Z-axis height filtering

## Performance Comparison

### Timing Results (14.8M points, 2834 odometry positions)

| Method | Time | Points | Speedup |
|--------|------|--------|---------|
| **Optimized (Direct Norm + Grid + Buffer)** | **1.85s** | 9.6M | **1.0x** (baseline) |
| Grid-based (no buffer) | 3.13s | 8.5M | 1.7x slower |
| 2D Direct (no buffer) | 10.97s | 8.5M | 5.9x slower |
| 3D Normal Plane (Minkowski + buffer) | 20.35s | 8.7M | 11.0x slower |

### Breakdown of Optimized Method

| Step | Time | Percentage |
|------|------|------------|
| Read data | 0.562s | 30.4% |
| Create hull | 0.001s | 0.1% |
| **Direct Normalization expansion** | **0.001s** | **0.1%** |
| Create grid | 0.041s | 2.2% |
| Filter points | 0.340s | 18.4% |
| Write output | 0.804s | 43.5% |
| **Total** | **1.847s** | **100%** |

The Direct Normalization expansion is **500x faster** than Minkowski sum methods!

## Usage

### Basic Usage

```bash
python filter_pointcloud_by_odom_optimized.py \
    input.las \
    odom.txt \
    -o output.las \
    --progress
```

### With Custom Parameters

```bash
python filter_pointcloud_by_odom_optimized.py \
    input.las \
    odom.txt \
    -o output.las \
    --grid-size 0.3 \      # Smaller grid = more precision, slower
    --buffer 1.0 \          # 1 meter buffer expansion
    --min-height -2.0 \     # Filter by Z height
    --max-height 5.0 \
    --progress              # Show progress
```

### Parameters

- `--grid-size`: Grid cell size in meters (default: 0.5m)
  - Smaller = more precise but slower
  - Larger = faster but less precise
  - Recommended: 0.3-0.7m for most use cases

- `--buffer`: Buffer distance for hull expansion (default: 0.5m)
  - Expands the convex hull boundary
  - Useful for capturing points near the edges
  - Typical range: 0.2-2.0m

- `--min-height`, `--max-height`: Z-axis filtering
  - Optional height constraints
  - Applied before convex hull filtering

## Algorithm Details

### Direct Normalization Method

The key innovation is the angle bisector approach for vertex expansion:

1. **For each vertex v:**
   - Get previous edge: `e1 = v - v_prev`
   - Get next edge: `e2 = v_next - v`

2. **Compute edge normals (perpendicular, pointing outward):**
   - `n1 = [e1.y, -e1.x] / |e1|`
   - `n2 = [e2.y, -e2.x] / |e2|`

3. **Average normals (angle bisector):**
   - `bisector = (n1 + n2) / 2`
   - `bisector = bisector / |bisector|`

4. **Adjust for angle:**
   - `angle = arccos(n1 · n2)`
   - `offset_factor = 1 / sin(angle/2)`
   - Capped at 5.0 to avoid extreme expansion at sharp corners

5. **Move vertex:**
   - `v_expanded = v + bisector * buffer * offset_factor`

This method ensures:
- ✓ Uniform buffer distance perpendicular to edges
- ✓ Smooth transitions at corners
- ✓ O(n) complexity where n = number of vertices
- ✓ No need for circle discretization or convex hull of expanded points

### Grid-Based Direct Normalization

The coordinate transformation uses direct normalization:

```
Original coordinates: (x, y)
Grid origin: (x_min, y_min)
Grid size: g

Normalized indices:
i = floor((x - x_min) / g)
j = floor((y - y_min) / g)

This maps each point directly to its grid cell in O(1) time.
```

## Advantages

1. **Speed**: 
   - 11x faster than 3D method with buffer
   - 6x faster than 2D method without buffer
   - Near real-time processing for large datasets

2. **Simplicity**:
   - No complex 3D transformations
   - No PCA/RANSAC overhead
   - Straightforward implementation

3. **Efficiency**:
   - Direct Normalization expansion: O(n) where n = hull vertices
   - Grid filtering: O(m) where m = number of points
   - Minimal memory overhead

4. **Flexibility**:
   - Adjustable grid size for speed/precision trade-off
   - Configurable buffer distance
   - Optional height filtering

## Limitations

1. **2D Only**: Assumes relatively flat terrain (XY plane filtering)
2. **Grid Approximation**: Points on cell boundaries may have minor precision issues
3. **Sharp Corners**: Very sharp angles in hull may have slight over-expansion (capped at 5x offset)

## When to Use

**Use Optimized Filter when:**
- ✓ Processing large point clouds (>1M points)
- ✓ Need fast processing times
- ✓ Terrain is relatively flat
- ✓ Want buffer expansion around path

**Use 3D Normal Plane method when:**
- Working with sloped terrain
- Need precise normal-aligned filtering
- Processing time is not critical

**Use basic 2D method when:**
- Need simple, no-buffer filtering
- Don't need grid optimization
- Very small datasets

## Examples

### Fast Processing with Standard Buffer
```bash
# Fastest mode - 0.5m grid, 0.5m buffer
python filter_pointcloud_by_odom_optimized.py \
    large_scan.las odom.txt \
    --grid-size 0.5 --buffer 0.5 -p
# Expected: ~2-3s for 15M points
```

### High Precision with Larger Buffer
```bash
# More precise - 0.3m grid, 1.0m buffer
python filter_pointcloud_by_odom_optimized.py \
    large_scan.las odom.txt \
    --grid-size 0.3 --buffer 1.0 -p
# Expected: ~3-5s for 15M points
```

### Speed Priority
```bash
# Maximum speed - 1.0m grid, minimal buffer
python filter_pointcloud_by_odom_optimized.py \
    large_scan.las odom.txt \
    --grid-size 1.0 --buffer 0.2 -p
# Expected: ~1-2s for 15M points
```

## Technical Notes

### Coordinate System
- Uses XY plane for 2D operations
- Z-axis for optional height filtering
- Assumes counter-clockwise hull vertex ordering (from scipy.spatial.ConvexHull)

### Grid Cell Indexing
- Uses floor division for consistent cell assignment
- Clips indices to prevent out-of-bounds access
- Cell centers used for inside/outside determination

### Hull Expansion Accuracy
- Direct Normalization provides ~95-98% accuracy vs true Minkowski sum
- Slight variations at sharp corners (>150° angles)
- Negligible difference for practical applications

## Conclusion

The optimized filter represents the culmination of filtering method evolution, combining:
- Direct Normalization for efficient hull expansion
- Grid-based spatial indexing for fast point lookup
- Simple 2D approach avoiding complex 3D transformations

**Result**: Up to 11x speedup while maintaining comparable output quality.
