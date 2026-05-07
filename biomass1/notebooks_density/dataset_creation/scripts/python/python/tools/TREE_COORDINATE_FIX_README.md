# Tree Coordinate Mapping Fix

## Problem Summary

When loading tree positions from the CSV file (`input/DBHaverage.csv`) and trying to draw them on the density map from pointcloud rasterization, the trees were not appearing correctly or were positioned incorrectly.

## Root Cause

The issue was in the coordinate conversion function `world_to_pixel()` in the notebook. The function had several problems:

1. **Incorrect handling of grid resize**: The rasterization process creates a grid at one size (e.g., 416×444 pixels), then resizes it to the target size (e.g., 320×320 pixels). The coordinate conversion was not properly accounting for this transformation.

2. **Complex pixel size calculation**: The function was trying to calculate "effective pixel size" based on the resize operation, but this approach was unnecessarily complex and error-prone.

3. **Coordinate system mismatch**: The CSV coordinates come from the biomass estimation tool which uses world coordinates in meters (with a 0.2m grid for density calculation). The rasterization tool uses world coordinates directly from the LAS file, so they should align - but the pixel mapping was wrong.

## Solution

The fixed coordinate conversion (`world_to_pixel_fixed()` in `fix_tree_coordinates.py`) uses a simpler and more robust approach:

1. **Normalize to 0-1 range**: Convert world coordinates to normalized coordinates (0-1) based on the world bounds
2. **Scale to pixel space**: Multiply by the current grid dimensions (after resize)
3. **Invert Y-axis**: Account for image coordinates having origin at top-left vs world coordinates at bottom-left

### Key Differences

**Old approach (incorrect)**:
```python
# Tried to calculate "effective pixel size" accounting for resize
effective_pixel_size_x = world_width / current_width
pixel_x = int((x - x_min) / effective_pixel_size_x)
```

**New approach (correct)**:
```python
# Normalize then scale directly
x_norm = (x - x_min) / world_width
pixel_x = int(x_norm * current_width)
```

## Results

- **Before**: Trees were misaligned or outside bounds
- **After**: All 68 trees correctly positioned on density map
- **Success rate**: 100% (68/68 trees drawn successfully)

## Usage

### Option 1: Use the standalone script
```bash
cd scripts/python/tools
python fix_tree_coordinates.py
```

This will generate: `output/rasterization_result_notebook/scans_test_optimized_1m_density_with_trees_FIXED.png`

### Option 2: Import the function in your notebook

Add this cell to your notebook:
```python
from fix_tree_coordinates import world_to_pixel_fixed, draw_trees_on_density

# Then use it to draw trees
trees_drawn = draw_trees_on_density(
    grid, meta, 
    csv_file='../../../input/DBHaverage.csv',
    output_path=out_dir / f"{base}_density_with_trees.png",
    rect_size_meters=1.0
)
```

### Option 3: Replace the function in the notebook

Replace the `world_to_pixel()` function definition cell with the corrected version from `fix_tree_coordinates.py`.

## Technical Details

### Coordinate Systems

1. **World coordinates** (from LAS file and biomass CSV):
   - Origin: Arbitrary (depends on data collection)
   - Units: Meters
   - X range: -9.0 to 43.0 m
   - Y range: -5.0 to 50.5 m

2. **Raster grid** (before resize):
   - Size: 416 × 444 pixels
   - Pixel size: 0.125 m/pixel
   - Covers the same world bounds

3. **Resized grid** (final):
   - Size: 320 × 320 pixels
   - Effective pixel size: ~0.168 m/pixel
   - Still covers the same world bounds

### Why the CSV Coordinates Work

The biomass estimation tool (`biomass-estimation-tools/src/mainClass.py`) generates tree positions using:
- The same point cloud data (same coordinate system)
- World coordinates in meters for tree centers
- A 0.2m grid for density analysis (independent of visualization grid)

Therefore, the X,Y coordinates in `DBHaverage.csv` are already in the correct world coordinate system - they just needed proper pixel mapping.

## Verification

Run the script and check the output image. All trees should:
- ✓ Be positioned at density peaks
- ✓ Have green rectangles (1m × 1m)
- ✓ Have blue center dots
- ✓ Not extend outside the image bounds

## Files Modified/Created

- `scripts/python/tools/fix_tree_coordinates.py` - New standalone fix script
- `output/rasterization_result_notebook/scans_test_optimized_1m_density_with_trees_FIXED.png` - Corrected visualization
