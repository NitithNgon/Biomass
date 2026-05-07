"""
Fixed coordinate conversion for mapping tree positions from CSV to density raster.

The key issue was that the biomass estimation tool uses world coordinates in meters,
and the rasterization creates a grid that gets resized. The coordinate conversion
needs to properly handle this transformation.
"""

import numpy as np
import pandas as pd
import cv2
import matplotlib.pyplot as plt
from pathlib import Path
import json


def world_to_pixel_fixed(x, y, meta):
    """
    Correctly convert world coordinates (X, Y in meters) to pixel coordinates.
    
    This handles the case where:
    1. Original raster was created at one size (e.g., 416x444 pixels)
    2. Raster was then resized to target size (e.g., 320x320 pixels)
    
    Args:
        x, y: World coordinates in meters
        meta: Metadata dictionary with coordinate bounds and sizes
        
    Returns:
        (pixel_x, pixel_y): Pixel coordinates in the RESIZED raster grid
    """
    # Get world bounds - these don't change with resize
    x_min = meta['x_min']
    y_min = meta['y_min'] 
    x_max = meta['x_max']
    y_max = meta['y_max']
    
    # World dimensions in meters
    world_width = x_max - x_min
    world_height = y_max - y_min
    
    # Get the CURRENT grid size (after resize)
    resized_to = meta.get('resized_to', None)
    if resized_to:
        # Grid was resized - use the resized dimensions
        current_height = resized_to
        current_width = resized_to  # Assuming square resize
    else:
        # No resize - use original dimensions
        current_width = meta['width']
        current_height = meta['height']
    
    # Calculate pixel coordinates
    # Normalize to 0-1 range in world coordinates
    x_norm = (x - x_min) / world_width
    y_norm = (y - y_min) / world_height
    
    # Convert to pixel coordinates
    pixel_x = int(x_norm * current_width)
    pixel_y = int(y_norm * current_height)
    
    # Y axis is inverted in image coordinates
    # Raster origin is top-left, world origin is bottom-left
    pixel_y = current_height - pixel_y - 1
    
    # Clamp to valid range
    pixel_x = max(0, min(current_width - 1, pixel_x))
    pixel_y = max(0, min(current_height - 1, pixel_y))
    
    return pixel_x, pixel_y


def draw_trees_on_density(grid, meta, csv_file, output_path, 
                           rect_size_meters=1.0, rect_color=(0, 255, 0), 
                           rect_thickness=2):
    """
    Draw tree positions from CSV onto the density map.
    
    Args:
        grid: Multi-channel raster grid (H x W x C)
        meta: Metadata dictionary with coordinate info
        csv_file: Path to CSV file with tree positions (must have X, Y columns)
        output_path: Where to save the output image
        rect_size_meters: Size of rectangle around each tree in meters
        rect_color: BGR color for rectangles
        rect_thickness: Line thickness in pixels
        
    Returns:
        Number of trees drawn
    """
    # Load CSV
    try:
        df_trees = pd.read_csv(csv_file)
        df_trees = df_trees.dropna(subset=['X', 'Y'])
        print(f"✓ Loaded {len(df_trees)} tree positions from {csv_file}")
    except Exception as e:
        print(f"✗ Error loading CSV: {e}")
        return 0
    
    # Get density channel
    density = np.nan_to_num(grid[:,:,0], nan=0.0)
    
    # Convert to BGR image for drawing
    density_normalized = ((density - density.min()) / (density.max() - density.min()) * 255).astype(np.uint8)
    density_bgr = cv2.cvtColor(density_normalized, cv2.COLOR_GRAY2BGR)
    
    # Get current grid dimensions
    resized_to = meta.get('resized_to', None)
    if resized_to:
        current_height = resized_to
        current_width = resized_to
    else:
        current_width = meta['width']
        current_height = meta['height']
    
    # Calculate effective pixel size in meters per pixel
    world_width = meta['x_max'] - meta['x_min']
    world_height = meta['y_max'] - meta['y_min']
    pixel_size_x = world_width / current_width
    pixel_size_y = world_height / current_height
    pixel_size = (pixel_size_x + pixel_size_y) / 2  # Average
    
    # Convert rectangle size to pixels
    rect_half_size_pixels = int(rect_size_meters / pixel_size / 2)
    
    print(f"\nDrawing parameters:")
    print(f"  Grid size: {current_width} x {current_height} pixels")
    print(f"  World bounds: X=[{meta['x_min']:.1f}, {meta['x_max']:.1f}], Y=[{meta['y_min']:.1f}, {meta['y_max']:.1f}] meters")
    print(f"  Pixel size: {pixel_size:.4f} meters/pixel")
    print(f"  Rectangle: {rect_size_meters}m = {rect_half_size_pixels*2} pixels")
    
    # Draw trees
    trees_drawn = 0
    trees_outside = 0
    
    for idx, row in df_trees.iterrows():
        x_world = row['X']
        y_world = row['Y']
        
        # Convert to pixel coordinates
        px, py = world_to_pixel_fixed(x_world, y_world, meta)
        
        # Check if within bounds
        if 0 <= px < current_width and 0 <= py < current_height:
            # Calculate rectangle corners
            x1 = max(0, px - rect_half_size_pixels)
            y1 = max(0, py - rect_half_size_pixels)
            x2 = min(current_width - 1, px + rect_half_size_pixels)
            y2 = min(current_height - 1, py + rect_half_size_pixels)
            
            # Draw rectangle
            cv2.rectangle(density_bgr, (x1, y1), (x2, y2), rect_color, rect_thickness)
            
            # Draw center point
            cv2.circle(density_bgr, (px, py), 2, (255, 0, 0), -1)  # Blue center
            
            trees_drawn += 1
        else:
            trees_outside += 1
            print(f"  Tree {row.get('ID', idx)} at ({x_world:.2f}, {y_world:.2f}) -> pixel ({px}, {py}) is outside bounds")
    
    print(f"\n✓ Drawing complete:")
    print(f"  Trees drawn: {trees_drawn}")
    print(f"  Trees outside: {trees_outside}")
    
    # Save result
    cv2.imwrite(str(output_path), density_bgr)
    print(f"✓ Saved to: {output_path}")
    
    return trees_drawn


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Load the raster data
    raster_dir = Path("../../../output/rasterization_result_notebook")
    grid = np.load(raster_dir / "scans_test_optimized_1m_raster.npy")
    
    with open(raster_dir / "scans_test_optimized_1m_raster_metadata.json", 'r') as f:
        meta = json.load(f)
    
    # Draw trees
    csv_file = "../../../input/DBHaverage.csv"
    output_path = raster_dir / "scans_test_optimized_1m_density_with_trees_FIXED.png"
    
    trees_drawn = draw_trees_on_density(
        grid, meta, csv_file, output_path,
        rect_size_meters=1.0,
        rect_color=(0, 255, 0),
        rect_thickness=2
    )
    
    print(f"\n✓ Complete! Drew {trees_drawn} trees on density map")
