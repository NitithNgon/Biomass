#!/usr/bin/env python3
"""
True Minkowski Sum-Based Filtering for Point Cloud

This implementation uses TRUE Minkowski sum which creates smooth, rounded boundaries
by placing circles at each vertex and connecting them with arc segments.

Key Difference from Direct Normalization:
- Direct Normalization: Offsets edges → sharp corners (polygon remains angular)
- True Minkowski Sum: Circles at vertices + arcs → smooth, rounded shape
"""

import os
import sys
import time
import numpy as np
import scipy as sp
import argparse
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

# Add the scripts/python directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from core.pjfunc import readLas, readODM, writeLas
from core.convexhull import getInsidePoints2


def expand_hull_minkowski_sum(hull_vertices, buffer_distance=0.5, num_arc_points=8):
    """
    Expand convex hull using TRUE Minkowski sum with circular structuring element.
    
    This creates a smooth, rounded boundary by:
    1. Creating a circle (disk) at each vertex of the hull
    2. Creating arc segments between adjacent vertices
    3. Taking the union of all these shapes
    
    Args:
        hull_vertices: nx2 array of hull vertices (ordered counter-clockwise)
        buffer_distance: radius of the circular structuring element (in meters)
        num_arc_points: number of points per arc segment (higher = smoother)
    
    Returns:
        expanded_vertices: vertices of the expanded hull (smooth boundary)
    """
    if buffer_distance <= 0:
        return hull_vertices.copy()
    
    # Use Shapely's buffer method which implements true Minkowski sum
    # Create polygon from hull vertices
    poly = Polygon(hull_vertices)
    
    # Buffer creates Minkowski sum with a disk of given radius
    # cap_style=1 (round) ensures circular caps at vertices
    # join_style=1 (round) ensures rounded corners
    buffered_poly = poly.buffer(
        buffer_distance,
        resolution=num_arc_points,  # points per quarter circle
        cap_style=1,   # round caps
        join_style=1,  # round joins
        mitre_limit=5.0
    )
    
    # Extract coordinates from buffered polygon
    if buffered_poly.is_empty:
        return hull_vertices.copy()
    
    # Get exterior coordinates (boundary of expanded polygon)
    expanded_coords = np.array(buffered_poly.exterior.coords[:-1])  # Remove duplicate last point
    
    return expanded_coords


def expand_hull_minkowski_manual(hull_vertices, buffer_distance=0.5, num_arc_points=8):
    """
    Manual implementation of Minkowski sum for educational purposes.
    
    Creates smooth expansion by:
    1. Offsetting each edge by buffer_distance
    2. Adding circular arcs at each vertex
    
    Args:
        hull_vertices: nx2 array of hull vertices
        buffer_distance: expansion distance
        num_arc_points: points per arc
    
    Returns:
        expanded_vertices: smooth expanded boundary
    """
    if buffer_distance <= 0:
        return hull_vertices.copy()
    
    n_vertices = len(hull_vertices)
    expanded_points = []
    
    for i in range(n_vertices):
        # Current vertex and its neighbors
        prev_vertex = hull_vertices[(i - 1) % n_vertices]
        curr_vertex = hull_vertices[i]
        next_vertex = hull_vertices[(i + 1) % n_vertices]
        
        # Vectors to neighbors
        to_prev = prev_vertex - curr_vertex
        to_next = next_vertex - curr_vertex
        
        # Normalize
        to_prev_norm = to_prev / np.linalg.norm(to_prev)
        to_next_norm = to_next / np.linalg.norm(to_next)
        
        # Perpendicular vectors (outward normals)
        perp_prev = np.array([to_prev_norm[1], -to_prev_norm[0]])
        perp_next = np.array([to_next_norm[1], -to_next_norm[0]])
        
        # Offset points on adjacent edges
        offset_on_prev_edge = curr_vertex + perp_prev * buffer_distance
        offset_on_next_edge = curr_vertex + perp_next * buffer_distance
        
        # Calculate angle for arc at this vertex
        # Angle from prev edge normal to next edge normal
        angle_prev = np.arctan2(perp_prev[1], perp_prev[0])
        angle_next = np.arctan2(perp_next[1], perp_next[0])
        
        # Ensure we go counter-clockwise
        if angle_next < angle_prev:
            angle_next += 2 * np.pi
        
        # Create arc points
        arc_angles = np.linspace(angle_prev, angle_next, num_arc_points, endpoint=False)
        for angle in arc_angles:
            arc_point = curr_vertex + buffer_distance * np.array([np.cos(angle), np.sin(angle)])
            expanded_points.append(arc_point)
    
    if len(expanded_points) < 3:
        return hull_vertices.copy()
    
    expanded_vertices = np.array(expanded_points)
    
    # Create convex hull of all expanded points to ensure valid polygon
    if len(expanded_vertices) > 2:
        try:
            hull = ConvexHull(expanded_vertices)
            expanded_vertices = expanded_vertices[hull.vertices]
        except:
            pass
    
    return expanded_vertices


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
    Filter points based on grid mask.
    
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
    grid_size = x_edges[1] - x_edges[0]
    
    # Calculate grid indices
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


def process_minkowski(data_path, odom_path, output_path=None, grid_size=0.5,
                     buffer_distance=0.5, min_height=None, max_height=None, 
                     num_arc_points=16, show_progress=False, use_shapely=True):
    """
    Process point cloud using TRUE Minkowski sum expansion.
    
    Pipeline:
    1. Read point cloud and odometry data
    2. Filter by Z height directly (if specified)
    3. Create convex hull from odometry
    4. Expand hull using TRUE Minkowski sum (smooth, rounded boundary)
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
        num_arc_points (int): Points per arc segment for smoothness (default: 16)
        show_progress (bool): Whether to show progress messages
        use_shapely (bool): Use Shapely library (True) or manual implementation (False)
    
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
    
    # Auto-convert PCD to LAS if needed
    original_data_path = data_path
    if data_path.lower().endswith('.pcd'):
        las_path = data_path[:-4] + '.las'
        if show_progress:
            print(f"⚙ Auto-converting PCD to LAS format...")
        
        # Import convert_pcd_to_las function
        tools_dir = os.path.join(parent_dir, 'tools')
        sys.path.insert(0, tools_dir)
        try:
            from convert_pcd_to_las import convert_pcd_to_las
            convert_pcd_to_las(data_path, las_path)
            data_path = las_path
            if show_progress:
                print(f"✓ Converted to: {las_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to convert PCD to LAS: {str(e)}")
    
    # Set default output path if none provided
    if output_path is None:
        base, ext = os.path.splitext(data_path)
        output_path = f"{base}_minkowski{ext}"
    
    # Read the data
    t_start = time.time()
    dat = readLas(data_path)
    x, y, z = readODM(odom_path)
    odm_points = np.column_stack((x, y))
    timing['read_data'] = time.time() - t_start

    t1 = time.time()
    if show_progress:
        print(f"✓ Data reading: {t1-t0:.3f}s")
        print(f"  Point cloud: {len(dat):,} points")
        print(f"  Odometry: {len(odm_points)} positions")
        print(f"  Grid size: {grid_size}m")
        print(f"  Buffer distance: {buffer_distance}m")
        print(f"  Arc points: {num_arc_points} (higher = smoother)")
        method = "Shapely (True Minkowski)" if use_shapely else "Manual Minkowski"
        print(f"  Method: {method}")

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
    
    # Expand hull using TRUE Minkowski sum
    t_start = time.time()
    if use_shapely:
        expanded_hull = expand_hull_minkowski_sum(hull_vertices, buffer_distance, num_arc_points)
    else:
        expanded_hull = expand_hull_minkowski_manual(hull_vertices, buffer_distance, num_arc_points)
    timing['expand_hull'] = time.time() - t_start
    
    if show_progress:
        print(f"✓ Minkowski sum expansion: {timing['expand_hull']:.3f}s")
        print(f"  Expanded hull: {len(expanded_hull)} vertices (SMOOTH & ROUNDED)")
    
    # Calculate bounds for grid
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

    # Check if we have any points left
    if len(filtered_data) == 0:
        # Provide diagnostic information
        pc_bounds = {
            'x': (np.min(dat[:, 0]), np.max(dat[:, 0])),
            'y': (np.min(dat[:, 1]), np.max(dat[:, 1])),
            'z': (np.min(dat[:, 2]), np.max(dat[:, 2]))
        }
        odom_bounds = {
            'x': (np.min(odm_points[:, 0]), np.max(odm_points[:, 0])),
            'y': (np.min(odm_points[:, 1]), np.max(odm_points[:, 1]))
        }
        
        error_msg = (
            "\n❌ FILTERING RESULTED IN 0 POINTS\n\n"
            "This usually means the odometry path and point cloud don't overlap.\n\n"
            "Diagnostic Information:\n"
            f"  Point Cloud Bounds:\n"
            f"    X: [{pc_bounds['x'][0]:.2f}, {pc_bounds['x'][1]:.2f}]\n"
            f"    Y: [{pc_bounds['y'][0]:.2f}, {pc_bounds['y'][1]:.2f}]\n"
            f"    Z: [{pc_bounds['z'][0]:.2f}, {pc_bounds['z'][1]:.2f}]\n"
            f"  Odometry Bounds:\n"
            f"    X: [{odom_bounds['x'][0]:.2f}, {odom_bounds['x'][1]:.2f}]\n"
            f"    Y: [{odom_bounds['y'][0]:.2f}, {odom_bounds['y'][1]:.2f}]\n\n"
            "Possible solutions:\n"
            "  1. Check if the point cloud and odometry are in the same coordinate system\n"
            "  2. Verify the odometry file corresponds to this point cloud scan\n"
            "  3. Try increasing the buffer distance (currently {:.2f}m)\n"
            "  4. Check if coordinate transformations are needed\n"
        ).format(buffer_distance)
        
        raise ValueError(error_msg)

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
        description='True Minkowski Sum-based filtering with smooth, rounded boundaries'
    )
    parser.add_argument('las_file', help='Input LAS file path')
    parser.add_argument('odom_file', help='Input odometry text file path')
    parser.add_argument('-o', '--output', help='Output LAS file path (optional)')
    parser.add_argument('--grid-size', type=float, default=0.5,
                       help='Grid cell size in meters (default: 0.5m)')
    parser.add_argument('--buffer', type=float, default=0.5,
                       help='Buffer distance for hull expansion in meters (default: 0.5m)')
    parser.add_argument('--arc-points', type=int, default=16,
                       help='Number of points per arc segment (default: 16, higher = smoother)')
    parser.add_argument('--min-height', type=float, help='Minimum Z height to keep')
    parser.add_argument('--max-height', type=float, help='Maximum Z height to keep')
    parser.add_argument('--manual', action='store_true',
                       help='Use manual Minkowski implementation instead of Shapely')
    parser.add_argument('-p', '--progress', action='store_true', 
                       help='Show progress messages')
    
    args = parser.parse_args()
    
    try:
        data, bounds, timing = process_minkowski(
            args.las_file,
            args.odom_file,
            args.output,
            args.grid_size,
            args.buffer,
            args.min_height,
            args.max_height,
            args.arc_points,
            args.progress,
            use_shapely=not args.manual
        )
        
        print(f"\n✓ Successfully processed {args.las_file}")
        print(f"\nMethod: TRUE Minkowski Sum (smooth & rounded)")
        print(f"  Buffer distance: {args.buffer}m")
        print(f"  Arc smoothness: {args.arc_points} points/arc")
        print(f"\nTiming breakdown:")
        for step, step_time in timing.items():
            print(f"  {step}: {step_time:.3f}s")
        print("\nData bounds:")
        for key, value in bounds.items():
            print(f"  {key}: {value:.2f}")
        print(f"\nResult: {len(data):,} points")
        
    except Exception as e:
        print(f"✗ Error processing file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
