#!/usr/bin/env python3
"""
Optimized 2D Grid-Based Filtering with Direct Normalization Minkowski Expansion

This implementation combines:
1. 2D grid-based approach for fast point filtering
2. Direct Normalization method for efficient Minkowski expansion
3. Simple XY plane operations (no 3D normal transformation)

Key Improvements:
- Direct Normalization: Expands hull by moving edges along their normal vectors
  (more efficient than creating circles around each vertex)
- Grid-based filtering: Pre-computes which grid cells are inside hull
- Simple 2D approach: No expensive PCA/RANSAC for normal estimation
"""

import os
import sys
import time
import numpy as np
import scipy as sp
import argparse
from scipy.spatial import ConvexHull

# Add the scripts/python directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from core.pjfunc import readLas, readODM, writeLas
from core.convexhull import getInsidePoints2


def expand_hull_direct_normalization(hull_vertices, buffer_distance=0.5):
    """
    Expand convex hull using offset method (simple and reliable).
    
    For each edge of the convex hull, compute the outward normal and move
    the edge by buffer_distance. Then find intersections of adjacent offset edges.
    
    Args:
        hull_vertices: nx2 array of hull vertices (ordered counter-clockwise)
        buffer_distance: distance to expand the hull (in meters)
    
    Returns:
        expanded_vertices: expanded hull vertices
    """
    if buffer_distance <= 0:
        return hull_vertices.copy()
    
    n_vertices = len(hull_vertices)
    
    # Compute offset edges (lines parallel to original edges, moved outward)
    offset_edges = []
    for i in range(n_vertices):
        p1 = hull_vertices[i]
        p2 = hull_vertices[(i + 1) % n_vertices]
        
        # Edge vector
        edge = p2 - p1
        edge_length = np.linalg.norm(edge)
        
        if edge_length < 1e-10:
            continue
            
        # Outward normal (perpendicular to edge, pointing outward)
        # For counter-clockwise ordered vertices, left perpendicular is outward
        normal = np.array([edge[1], -edge[0]]) / edge_length
        
        # Offset both points by buffer_distance along the normal
        offset_p1 = p1 + normal * buffer_distance
        offset_p2 = p2 + normal * buffer_distance
        
        offset_edges.append((offset_p1, offset_p2))
    
    if len(offset_edges) < 3:
        return hull_vertices.copy()
    
    # Find intersections of adjacent offset edges to get new vertices
    expanded_vertices = []
    for i in range(len(offset_edges)):
        edge1 = offset_edges[i]
        edge2 = offset_edges[(i + 1) % len(offset_edges)]
        
        # Find intersection of edge1 and edge2
        intersection = line_intersection(edge1[0], edge1[1], edge2[0], edge2[1])
        
        if intersection is not None:
            expanded_vertices.append(intersection)
        else:
            # If lines are parallel (shouldn't happen with convex hull), use the endpoint
            expanded_vertices.append(edge1[1])
    
    if len(expanded_vertices) < 3:
        return hull_vertices.copy()
    
    return np.array(expanded_vertices)


def line_intersection(p1, p2, p3, p4):
    """
    Find intersection point of two line segments.
    Line 1: p1 -> p2
    Line 2: p3 -> p4
    
    Returns None if lines are parallel or don't intersect.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    
    if abs(denom) < 1e-10:
        # Lines are parallel
        return None
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    
    # Intersection point
    x = x1 + t * (x2 - x1)
    y = y1 + t * (y2 - y1)
    
    return np.array([x, y])


def create_grid_mask(bounds, grid_size, hull_vertices):
    """
    Create a binary grid mask indicating which cells are inside the convex hull.
    
    Args:
        bounds: dict with xmin, xmax, ymin, ymax
        grid_size: size of each grid cell (in meters)
        hull_vertices: vertices of the convex hull
    
    Returns:
        grid_mask: 2D binary array (1 = inside hull, 0 = outside)
        x_edges: grid cell edges in X direction
        y_edges: grid cell edges in Y direction
    """
    # Create grid edges
    x_edges = np.arange(bounds['xmin'], bounds['xmax'] + grid_size, grid_size)
    y_edges = np.arange(bounds['ymin'], bounds['ymax'] + grid_size, grid_size)
    
    # Create grid centers for checking
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    
    # Create meshgrid of all grid cell centers
    X, Y = np.meshgrid(x_centers, y_centers)
    grid_points = np.column_stack([X.ravel(), Y.ravel()])
    
    # Check which grid cells are inside the convex hull
    inside = getInsidePoints2(grid_points, hull_vertices)
    
    # Reshape to 2D grid mask
    grid_mask = inside.reshape(len(y_centers), len(x_centers))
    
    return grid_mask, x_edges, y_edges


def filter_points_by_grid(points, grid_mask, x_edges, y_edges):
    """
    Filter points based on grid mask using Direct Normalization.
    
    Args:
        points: nx3 array of points
        grid_mask: 2D binary array indicating which grid cells are valid
        x_edges: grid cell edges in X direction
        y_edges: grid cell edges in Y direction
    
    Returns:
        mask: boolean array indicating which points to keep
    """
    # Get X and Y coordinates
    x = points[:, 0]
    y = points[:, 1]
    
    # Get min values and grid size
    x_min = x_edges[0]
    y_min = y_edges[0]
    grid_size = x_edges[1] - x_edges[0]  # Assuming uniform grid
    
    # Direct Normalization: shift to grid origin, scale by grid_size, floor to get indices
    x_indices = np.floor((x - x_min) / grid_size).astype(int)
    y_indices = np.floor((y - y_min) / grid_size).astype(int)
    
    # Clip indices to valid range
    x_indices = np.clip(x_indices, 0, grid_mask.shape[1] - 1)
    y_indices = np.clip(y_indices, 0, grid_mask.shape[0] - 1)
    
    # Check if points are in valid grid cells
    mask = grid_mask[y_indices, x_indices]
    
    return mask


def filter_by_height_simple(points, min_height=None, max_height=None):
    """
    Filter points by Z height directly.
    
    Args:
        points: nx3 array of points
        min_height: minimum Z height to keep (optional)
        max_height: maximum Z height to keep (optional)
    Returns:
        mask: boolean array indicating which points to keep
    """
    mask = np.ones(len(points), dtype=bool)
    
    if min_height is not None:
        mask &= points[:, 2] >= min_height
    if max_height is not None:
        mask &= points[:, 2] <= max_height
        
    return mask


def process_optimized(data_path, odom_path, output_path=None, grid_size=0.5,
                     buffer_distance=0.5, min_height=None, max_height=None, 
                     show_progress=False):
    """
    Process point cloud using optimized 2D grid-based filtering with Direct Normalization.
    
    Pipeline:
    1. Read point cloud and odometry data
    2. Filter by Z height directly (if specified)
    3. Create convex hull from odometry
    4. Expand hull using Direct Normalization method
    5. Create grid covering the area
    6. Check which grid cells are inside expanded hull
    7. Filter points based on grid cell membership
    8. Save processed data
    
    Args:
        data_path (str): Path to input LAS file
        odom_path (str): Path to odometry text file
        output_path (str, optional): Path to save output LAS file
        grid_size (float): Size of grid cells in meters (default: 0.5m)
        buffer_distance (float): Distance to expand hull (default: 0.5m)
        min_height (float, optional): Minimum Z height to keep
        max_height (float, optional): Maximum Z height to keep
        show_progress (bool): Whether to show progress messages
    
    Returns:
        tuple: (processed_data, bounds, timing_info)
    """
    timing = {}
    t0 = time.time()
    
    # Check if files exist
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data path {data_path} doesn't exist")
        
    if not os.path.exists(odom_path):
        raise FileNotFoundError(f"Odometry path {odom_path} doesn't exist")
    
    # Set default output path if none provided
    if output_path is None:
        base, ext = os.path.splitext(data_path)
        output_path = f"{base}_optimized{ext}"
    
    # Read the data
    t_start = time.time()
    dat = readLas(data_path)
    x, y, z = readODM(odom_path)
    odm_points = np.column_stack((x, y))  # Only need X, Y for 2D
    timing['read_data'] = time.time() - t_start

    t1 = time.time()
    if show_progress:
        print(f"✓ Data reading: {t1-t0:.3f}s")
        print(f"  Point cloud: {len(dat):,} points")
        print(f"  Odometry: {len(odm_points)} positions")
        print(f"  Grid size: {grid_size}m")
        print(f"  Buffer distance: {buffer_distance}m")
        print(f"  Method: Direct Normalization + Grid-based")

    # Filter by height if specified
    t_start = time.time()
    if min_height is not None or max_height is not None:
        height_mask = filter_by_height_simple(dat, min_height, max_height)
        dat = dat[height_mask]
        if show_progress:
            print(f"✓ Height filtering: kept {np.sum(height_mask):,} points")
    timing['height_filter'] = time.time() - t_start
    
    # Create convex hull from odometry
    t_start = time.time()
    chull = ConvexHull(odm_points)
    hull_vertices = odm_points[chull.vertices]
    timing['create_hull'] = time.time() - t_start
    
    if show_progress:
        print(f"✓ Original hull: {len(hull_vertices)} vertices")
    
    # Expand hull using Direct Normalization
    t_start = time.time()
    expanded_hull = expand_hull_direct_normalization(hull_vertices, buffer_distance)
    timing['expand_hull'] = time.time() - t_start
    
    if show_progress:
        print(f"✓ Direct Normalization expansion: {timing['expand_hull']:.3f}s")
        print(f"  Expanded hull: {len(expanded_hull)} vertices")
    
    # Calculate bounds for grid (use expanded hull to cover expanded area)
    all_points = np.vstack([dat[:, :2], expanded_hull])
    bounds = {
        'xmin': np.floor(np.min(all_points[:, 0])),
        'xmax': np.ceil(np.max(all_points[:, 0])),
        'ymin': np.floor(np.min(all_points[:, 1])),
        'ymax': np.ceil(np.max(all_points[:, 1]))
    }
    
    # Create grid mask using expanded hull
    t_start = time.time()
    grid_mask, x_edges, y_edges = create_grid_mask(bounds, grid_size, expanded_hull)
    timing['create_grid'] = time.time() - t_start
    
    if show_progress:
        total_cells = grid_mask.size
        valid_cells = np.sum(grid_mask)
        print(f"✓ Grid creation: {timing['create_grid']:.3f}s")
        print(f"  Grid cells: {total_cells:,} total, {valid_cells:,} inside hull ({valid_cells/total_cells*100:.1f}%)")
    
    # Filter points using grid
    t_start = time.time()
    inside_mask = filter_points_by_grid(dat, grid_mask, x_edges, y_edges)
    filtered_data = dat[inside_mask]
    timing['filter_points'] = time.time() - t_start
    
    t2 = time.time()
    if show_progress:
        print(f"✓ Grid-based filtering: {t2-t1:.3f}s")
        print(f"  Points inside expanded hull: {len(filtered_data):,}")

    # Save processed data
    t_start = time.time()
    writeLas(output_path, filtered_data)
    timing['write_output'] = time.time() - t_start

    if show_progress:
        t3 = time.time()
        print(f"✓ File writing: {t3-t2:.3f}s")
        print(f"✓ Total time: {t3-t0:.3f}s")

    # Update bounds for final data
    final_bounds = {
        'xmin': np.floor(np.min(filtered_data[:,0])),
        'xmax': np.ceil(np.max(filtered_data[:,0])),
        'ymin': np.floor(np.min(filtered_data[:,1])),
        'ymax': np.ceil(np.max(filtered_data[:,1])),
        'zmin': np.floor(np.min(filtered_data[:,2])),
        'zmax': np.ceil(np.max(filtered_data[:,2]))
    }
    
    return filtered_data, final_bounds, timing


def main():
    parser = argparse.ArgumentParser(
        description='Optimized 2D grid-based filtering with Direct Normalization Minkowski expansion'
    )
    parser.add_argument('las_file', help='Input LAS file path')
    parser.add_argument('odom_file', help='Input odometry text file path')
    parser.add_argument('-o', '--output', help='Output LAS file path (optional)')
    parser.add_argument('--grid-size', type=float, default=0.5,
                       help='Grid cell size in meters (default: 0.5m)')
    parser.add_argument('--buffer', type=float, default=0.5,
                       help='Buffer distance for hull expansion in meters (default: 0.5m)')
    parser.add_argument('--min-height', type=float, help='Minimum Z height to keep')
    parser.add_argument('--max-height', type=float, help='Maximum Z height to keep')
    parser.add_argument('-p', '--progress', action='store_true', 
                       help='Show progress messages')
    
    args = parser.parse_args()
    
    try:
        data, bounds, timing = process_optimized(
            args.las_file,
            args.odom_file,
            args.output,
            args.grid_size,
            args.buffer,
            args.min_height,
            args.max_height,
            args.progress
        )
        
        print(f"\n✓ Successfully processed {args.las_file}")
        print(f"\nOptimization statistics:")
        print(f"  Grid size: {args.grid_size}m")
        print(f"  Buffer distance: {args.buffer}m")
        print(f"  Method: Direct Normalization + Grid-based")
        for step, step_time in timing.items():
            print(f"  {step}: {step_time:.3f}s")
        print("\nData bounds:")
        for key, value in bounds.items():
            print(f"  {key}: {value:.2f}")
        print(f"\nResult: {len(data):,} points")
        
    except Exception as e:
        print(f"✗ Error processing file: {str(e)}")
        raise


if __name__ == '__main__':
    main()
#  cd /Users/songkarn/locarb/biomass/handheld-lidar-slam-toolbox 
#  && /Users/songkarn/anaconda3/bin/python scripts/python/preprocessing/filter_pointcloud_by_odom_optimized.py 
#  output/scans.las output/odom_ska-ls-h201.txt -o output/scans_test_optimized.las --grid-size 0.5 --buffer 0.5 -p
