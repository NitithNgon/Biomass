#!/usr/bin/env python3
"""
Create RGB composite images from rasterization outputs for experimental results.

This script creates 4 RGB combinations:
1. Mean, Median, Std (z_mean, z_p50, z_std)
2. Z_p50, Z_p25, z_range (percentile values with range)
3. P5, Median, P95 (z_p05, z_p50, z_p95)
4. P25, Median, P75 (z_p25, z_p50, z_p75)
"""

import numpy as np
import cv2
import json
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


def normalize_channel(channel, min_val=None, max_val=None):
    """Normalize a channel to 0-255 range for RGB output."""
    channel = np.nan_to_num(channel, nan=0.0, posinf=0.0, neginf=0.0)
    
    if min_val is None:
        min_val = channel.min()
    if max_val is None:
        max_val = channel.max()
    
    if max_val > min_val:
        normalized = ((channel - min_val) / (max_val - min_val) * 255).astype(np.uint8)
    else:
        normalized = np.zeros_like(channel, dtype=np.uint8)
    
    return normalized


def calculate_std_from_percentiles(grid, meta):
    """
    Calculate approximate standard deviation using percentiles.
    Uses the interquartile range (IQR) method: std ≈ IQR / 1.349
    """
    channel_names = meta['channel_names']
    p25_idx = channel_names.index('z_p25')
    p75_idx = channel_names.index('z_p75')
    
    p25 = grid[:, :, p25_idx]
    p75 = grid[:, :, p75_idx]
    
    # IQR method to estimate std
    iqr = p75 - p25
    std_approx = iqr / 1.349
    
    return np.nan_to_num(std_approx, nan=0.0, posinf=0.0, neginf=0.0)


def world_to_pixel(x, y, meta):
    """
    Convert world coordinates (X, Y in meters) to pixel coordinates in the raster.
    """
    x_min = meta.get('x_min', 0)
    y_min = meta.get('y_min', 0)
    pixel_size = meta.get('pixel_size', 0.125)
    
    orig_width = meta.get('width', 320)
    orig_height = meta.get('height', 320)
    
    resized_to = meta.get('resized_to', None)
    if resized_to and resized_to != orig_height:
        scale = resized_to / orig_height
        current_width = int(orig_width * scale)
        current_height = resized_to
    else:
        current_width = orig_width
        current_height = orig_height
    
    x_max = meta.get('x_max', x_min + orig_width * pixel_size)
    y_max = meta.get('y_max', y_min + orig_height * pixel_size)
    world_width = x_max - x_min
    world_height = y_max - y_min
    
    effective_pixel_size_x = world_width / current_width
    effective_pixel_size_y = world_height / current_height
    
    pixel_x = int((x - x_min) / effective_pixel_size_x)
    pixel_y = int((y - y_min) / effective_pixel_size_y)
    
    # Y axis is inverted in image coordinates
    pixel_y = current_height - pixel_y - 1
    
    return pixel_x, pixel_y


def draw_tree_rectangles(rgb_image, csv_path, meta, rect_size=1.0):
    """
    Draw rectangles for tree positions on RGB image and return positions data.
    
    Returns:
        annotated_image: Image with rectangles drawn
        tree_positions: List of dicts with tree information
    """
    try:
        df_trees = pd.read_csv(csv_path)
        df_trees = df_trees.dropna(subset=['X', 'Y'])
    except Exception as e:
        print(f"⚠ Warning: Could not load tree CSV: {e}")
        return rgb_image, []
    
    # Convert RGB to BGR for OpenCV
    annotated = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    annotated_flipped = cv2.flip(annotated, 0)  # Flip vertically for correct orientation
    
    # Calculate effective pixel size
    orig_width = meta.get('width', 320)
    orig_height = meta.get('height', 320)
    resized_to = meta.get('resized_to', None)
    
    if resized_to and resized_to != orig_height:
        scale = resized_to / orig_height
        current_width = int(orig_width * scale)
    else:
        current_width = orig_width
    
    x_min = meta.get('x_min', 0)
    x_max = meta.get('x_max', 0)
    world_width = x_max - x_min
    effective_pixel_size = world_width / current_width
    
    rect_half_size_pixels = int(rect_size / effective_pixel_size / 2)
    
    tree_positions = []
    RECT_COLOR = (0, 255, 0)  # Green in BGR
    RECT_THICKNESS = 2
    
    for idx, row in df_trees.iterrows():
        x_world = row['X']
        y_world = row['Y']
        
        px, py = world_to_pixel(x_world, y_world, meta)
        px = int(px * 1.08)  # Apply 1.08x extension
        
        if 0 <= px < meta['width'] and 0 <= py < meta['height']:
            x1 = max(0, px - rect_half_size_pixels)
            y1 = max(0, py - rect_half_size_pixels)
            x2 = min(meta['width'] - 1, px + rect_half_size_pixels)
            y2 = min(meta['height'] - 1, py + rect_half_size_pixels)
            
            cv2.rectangle(annotated_flipped, (x1, y1), (x2, y2), RECT_COLOR, RECT_THICKNESS)
            cv2.circle(annotated_flipped, (px, py), 2, (255, 0, 0), -1)  # Blue dot at center
            
            tree_positions.append({
                'tree_id': row.get('ID', idx),
                'x_world': float(x_world),
                'y_world': float(y_world),
                'pixel_x': int(px),
                'pixel_y': int(py),
                'rect_x1': int(x1),
                'rect_y1': int(y1),
                'rect_x2': int(x2),
                'rect_y2': int(y2)
            })
    
    # Convert back to RGB
    annotated_rgb = cv2.cvtColor(annotated_flipped, cv2.COLOR_BGR2RGB)
    
    return annotated_rgb, tree_positions


def create_rgb_composite(r_channel, g_channel, b_channel, output_path, title=None, 
                        csv_path=None, meta=None, draw_trees=False):
    """Create and save an RGB composite image."""
    # Normalize each channel
    r_norm = normalize_channel(r_channel)
    g_norm = normalize_channel(g_channel)
    b_norm = normalize_channel(b_channel)
    
    # Stack into RGB
    rgb = np.stack([r_norm, g_norm, b_norm], axis=2)
    
    # Save using matplotlib for better quality
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(rgb)
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close()
    
    # Also save raw RGB file
    raw_path = str(output_path).replace('.png', '_raw.png')
    cv2.imwrite(raw_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    
    print(f"✓ Saved RGB composite: {output_path}")
    print(f"  Raw RGB: {raw_path}")
    
    # Draw tree positions if requested
    tree_positions = []
    if draw_trees and csv_path and meta:
        annotated_rgb, tree_positions = draw_tree_rectangles(rgb, csv_path, meta)
        
        # Save annotated version
        annotated_path = str(output_path).replace('.png', '_with_trees.png')
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.imshow(annotated_rgb)
        if title:
            ax.set_title(f"{title} | Trees: {len(tree_positions)}", fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(annotated_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # Save raw annotated
        annotated_raw_path = str(output_path).replace('.png', '_with_trees_raw.png')
        cv2.imwrite(annotated_raw_path, cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR))
        
        print(f"✓ Saved RGB with trees: {annotated_path}")
        print(f"  Trees drawn: {len(tree_positions)}")
        print(f"  Raw RGB with trees: {annotated_raw_path}")
    
    return tree_positions


def draw_tree_rectangles_yolo(rgb_image, csv_path, meta, rect_size=1.0, size_multiplier=1.5):
    """
    Draw rectangles for YOLO training (larger boxes, no center dots).
    
    Returns:
        annotated_image: Image with rectangles drawn
        yolo_labels: List of YOLO format labels (class x_center y_center width height)
    """
    try:
        df_trees = pd.read_csv(csv_path)
        df_trees = df_trees.dropna(subset=['X', 'Y'])
    except Exception as e:
        print(f"⚠ Warning: Could not load tree CSV: {e}")
        return rgb_image, []
    
    # Convert RGB to BGR for OpenCV
    annotated = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    annotated_flipped = cv2.flip(annotated, 0)  # Flip vertically
    
    # Calculate effective pixel size
    orig_width = meta.get('width', 320)
    orig_height = meta.get('height', 320)
    resized_to = meta.get('resized_to', None)
    
    if resized_to and resized_to != orig_height:
        scale = resized_to / orig_height
        current_width = int(orig_width * scale)
        current_height = resized_to
    else:
        current_width = orig_width
        current_height = orig_height
    
    x_min = meta.get('x_min', 0)
    x_max = meta.get('x_max', 0)
    world_width = x_max - x_min
    effective_pixel_size = world_width / current_width
    
    # Larger rectangle for YOLO
    rect_half_size_pixels = int((rect_size * size_multiplier) / effective_pixel_size / 2)
    
    yolo_labels = []
    RECT_COLOR = (0, 255, 0)  # Green in BGR
    RECT_THICKNESS = 2
    
    for idx, row in df_trees.iterrows():
        x_world = row['X']
        y_world = row['Y']
        
        px, py = world_to_pixel(x_world, y_world, meta)
        px = int(px * 1.08)  # Apply 1.08x extension
        
        if 0 <= px < current_width and 0 <= py < current_height:
            x1 = max(0, px - rect_half_size_pixels)
            y1 = max(0, py - rect_half_size_pixels)
            x2 = min(current_width - 1, px + rect_half_size_pixels)
            y2 = min(current_height - 1, py + rect_half_size_pixels)
            
            # Draw rectangle (no center dot for YOLO)
            cv2.rectangle(annotated_flipped, (x1, y1), (x2, y2), RECT_COLOR, RECT_THICKNESS)
            
            # YOLO format: class x_center y_center width height (all normalized 0-1)
            box_width = (x2 - x1) / current_width
            box_height = (y2 - y1) / current_height
            x_center = ((x1 + x2) / 2) / current_width
            y_center = ((y1 + y2) / 2) / current_height
            
            # Class 0 for trees
            yolo_labels.append({
                'class': 0,
                'x_center': float(x_center),
                'y_center': float(y_center),
                'width': float(box_width),
                'height': float(box_height),
                'tree_id': row.get('ID', idx)
            })
    
    # Convert back to RGB
    annotated_rgb = cv2.cvtColor(annotated_flipped, cv2.COLOR_BGR2RGB)
    
    return annotated_rgb, yolo_labels


def save_yolo_labels(yolo_labels, output_path):
    """Save YOLO format labels to text file."""
    with open(output_path, 'w') as f:
        for label in yolo_labels:
            # YOLO format: class x_center y_center width height
            f.write(f"{label['class']} {label['x_center']:.6f} {label['y_center']:.6f} "
                   f"{label['width']:.6f} {label['height']:.6f}\n")


def main():
    # Configuration
    INPUT_NPY = '../../../output/rasterization_result_notebook/scans_test_optimized_1m_raster.npy'
    INPUT_META = '../../../output/rasterization_result_notebook/scans_test_optimized_1m_raster_metadata.json'
    OUTPUT_DIR = '../../../output/rasterization_result_notebook'
    CSV_FILE = '../../../input/DBHaverage.csv'
    DRAW_TREES = True
    RECT_SIZE = 1.0
    YOLO_SIZE_MULTIPLIER = 1.5  # Larger boxes for YOLO
    
    print("="*70)
    print("RGB COMPOSITE GENERATOR FOR EXPERIMENTAL RESULTS")
    print("="*70)
    
    # Load data
    print(f"\nLoading data from: {INPUT_NPY}")
    grid = np.load(INPUT_NPY)
    
    with open(INPUT_META, 'r') as f:
        meta = json.load(f)
    
    channel_names = meta['channel_names']
    print(f"✓ Loaded grid with shape: {grid.shape}")
    print(f"✓ Available channels: {len(channel_names)}")
    
    # Get channel indices
    density_idx = channel_names.index('density')
    z_mean_idx = channel_names.index('z_mean')
    z_p50_idx = channel_names.index('z_p50')  # median
    z_p05_idx = channel_names.index('z_p05')
    z_p25_idx = channel_names.index('z_p25')
    z_p75_idx = channel_names.index('z_p75')
    z_p95_idx = channel_names.index('z_p95')
    z_range_idx = channel_names.index('z_range')
    
    # Apply density mask
    MIN_DENSITY = 10
    density = grid[:, :, density_idx]
    mask = density >= MIN_DENSITY
    
    print(f"\nApplying density mask (min density = {MIN_DENSITY})...")
    
    # Extract and mask channels
    z_mean = np.copy(grid[:, :, z_mean_idx])
    z_p50 = np.copy(grid[:, :, z_p50_idx])
    z_p05 = np.copy(grid[:, :, z_p05_idx])
    z_p25 = np.copy(grid[:, :, z_p25_idx])
    z_p75 = np.copy(grid[:, :, z_p75_idx])
    z_p95 = np.copy(grid[:, :, z_p95_idx])
    z_range = np.copy(grid[:, :, z_range_idx])
    
    # Calculate std
    print("Calculating standard deviation from percentiles...")
    z_std = calculate_std_from_percentiles(grid, meta)
    
    # Apply mask to all channels
    for ch in [z_mean, z_p50, z_p05, z_p25, z_p75, z_p95, z_range, z_std]:
        ch[~mask] = 0.0
    
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*70)
    print("CREATING RGB COMPOSITES")
    print("="*70)
    
    # Store all tree positions
    all_tree_positions = {}
    
    # 1. Mean, Median, Std
    print("\n1. RGB Composite: Mean (R), Median (G), Std (B)")
    trees_1 = create_rgb_composite(
        z_mean, z_p50, z_std,
        output_dir / 'rgb_mean_median_std.png',
        title='RGB: Mean (R) | Median (G) | Std (B)',
        csv_path=CSV_FILE, meta=meta, draw_trees=DRAW_TREES
    )
    all_tree_positions['mean_median_std'] = trees_1
    
    # YOLO version
    if DRAW_TREES and CSV_FILE and meta:
        rgb_1 = np.stack([normalize_channel(z_mean), normalize_channel(z_p50), normalize_channel(z_std)], axis=2)
        yolo_img_1, yolo_labels_1 = draw_tree_rectangles_yolo(rgb_1, CSV_FILE, meta, RECT_SIZE, YOLO_SIZE_MULTIPLIER)
        
        # Save YOLO image
        yolo_path_1 = output_dir / 'rgb_mean_median_std_yolo.png'
        cv2.imwrite(str(yolo_path_1), cv2.cvtColor(yolo_img_1, cv2.COLOR_RGB2BGR))
        
        # Save YOLO labels
        label_path_1 = output_dir / 'rgb_mean_median_std_yolo.txt'
        save_yolo_labels(yolo_labels_1, label_path_1)
        
        print(f"✓ Saved YOLO version: {yolo_path_1}")
        print(f"✓ Saved YOLO labels: {label_path_1} ({len(yolo_labels_1)} trees)")
    
    # 2. Z_p50, Z_p25, Range
    print("\n2. RGB Composite: P50 (R), P25 (G), Range (B)")
    trees_2 = create_rgb_composite(
        z_p50, z_p25, z_range,
        output_dir / 'rgb_p50_p25_range.png',
        title='RGB: P50 (R) | P25 (G) | Range (B)',
        csv_path=CSV_FILE, meta=meta, draw_trees=DRAW_TREES
    )
    all_tree_positions['p50_p25_range'] = trees_2
    
    # 3. P5, Median, P95
    print("\n3. RGB Composite: P5 (R), Median (G), P95 (B)")
    trees_3 = create_rgb_composite(
        z_p05, z_p50, z_p95,
        output_dir / 'rgb_p05_median_p95.png',
        title='RGB: P5 (R) | Median (G) | P95 (B)',
        csv_path=CSV_FILE, meta=meta, draw_trees=DRAW_TREES
    )
    all_tree_positions['p05_median_p95'] = trees_3
    
    # 4. P25, Median, P75
    print("\n4. RGB Composite: P25 (R), Median (G), P75 (B)")
    trees_4 = create_rgb_composite(
        z_p25, z_p50, z_p75,
        output_dir / 'rgb_p25_median_p75.png',
        title='RGB: P25 (R) | Median (G) | P75 (B)',
        csv_path=CSV_FILE, meta=meta, draw_trees=DRAW_TREES
    )
    all_tree_positions['p25_median_p75'] = trees_4
    
    # YOLO version
    if DRAW_TREES and CSV_FILE and meta:
        rgb_4 = np.stack([normalize_channel(z_p25), normalize_channel(z_p50), normalize_channel(z_p75)], axis=2)
        yolo_img_4, yolo_labels_4 = draw_tree_rectangles_yolo(rgb_4, CSV_FILE, meta, RECT_SIZE, YOLO_SIZE_MULTIPLIER)
        
        # Save YOLO image
        yolo_path_4 = output_dir / 'rgb_p25_median_p75_yolo.png'
        cv2.imwrite(str(yolo_path_4), cv2.cvtColor(yolo_img_4, cv2.COLOR_RGB2BGR))
        
        # Save YOLO labels
        label_path_4 = output_dir / 'rgb_p25_median_p75_yolo.txt'
        save_yolo_labels(yolo_labels_4, label_path_4)
        
        print(f"✓ Saved YOLO version: {yolo_path_4}")
        print(f"✓ Saved YOLO labels: {label_path_4} ({len(yolo_labels_4)} trees)")
    
    # Save tree positions to JSON
    if DRAW_TREES and any(all_tree_positions.values()):
        positions_path = output_dir / 'rgb_tree_positions.json'
        with open(positions_path, 'w') as f:
            json.dump(all_tree_positions, f, indent=2)
        print(f"\n✓ Saved tree positions: {positions_path}")
    
    print("\n" + "="*70)
    print("✓ ALL RGB COMPOSITES CREATED SUCCESSFULLY!")
    print("="*70)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    print("  1. rgb_mean_median_std.png (+ _raw.png + _with_trees + _yolo versions)")
    print("  2. rgb_p50_p25_range.png (+ _raw.png + _with_trees versions)")
    print("  3. rgb_p05_median_p95.png (+ _raw.png + _with_trees versions)")
    print("  4. rgb_p25_median_p75.png (+ _raw.png + _with_trees + _yolo versions)")
    print("  5. rgb_tree_positions.json (tree position data)")
    print("\nNote: Each composite has:")
    print("  - Titled version (.png)")
    print("  - Raw version (_raw.png)")
    print("  - Version with trees drawn (_with_trees.png)")
    print("  - Raw version with trees (_with_trees_raw.png)")
    print("\nYOLO Training versions (for composites #1 and #4):")
    print("  - YOLO image (_yolo.png) - larger boxes, no center dots")
    print("  - YOLO labels (.txt) - normalized bbox coordinates")


if __name__ == '__main__':
    main()
