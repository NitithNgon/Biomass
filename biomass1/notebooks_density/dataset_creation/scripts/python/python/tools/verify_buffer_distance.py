#!/usr/bin/env python3
"""
Verify buffer distance between 0m and 1m versions of LAS files.
This script compares the bounds of both files to check if the expansion matches expectations.
"""

import sys
import os
import numpy as np
import laspy

# Add the scripts/python directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from core.pjfunc import readLas


def get_las_bounds(las_path):
    """Get the bounds of a LAS file."""
    data = readLas(las_path)
    
    bounds = {
        'xmin': np.min(data[:, 0]),
        'xmax': np.max(data[:, 0]),
        'ymin': np.min(data[:, 1]),
        'ymax': np.max(data[:, 1]),
        'zmin': np.min(data[:, 2]),
        'zmax': np.max(data[:, 2])
    }
    
    return bounds, len(data)


def compare_files(file_0m, file_1m):
    """Compare two LAS files to determine buffer distance."""
    print("=" * 80)
    print("BUFFER DISTANCE VERIFICATION")
    print("=" * 80)
    
    # Check if files exist
    if not os.path.exists(file_0m):
        print(f"❌ Error: File not found: {file_0m}")
        return
    if not os.path.exists(file_1m):
        print(f"❌ Error: File not found: {file_1m}")
        return
    
    print(f"\n📄 0m file: {os.path.basename(file_0m)}")
    print(f"📄 1m file: {os.path.basename(file_1m)}")
    print()
    
    # Get bounds
    print("Loading files...")
    bounds_0m, points_0m = get_las_bounds(file_0m)
    bounds_1m, points_1m = get_las_bounds(file_1m)
    
    print(f"✓ 0m file: {points_0m:,} points")
    print(f"✓ 1m file: {points_1m:,} points")
    print()
    
    # Display bounds
    print("-" * 80)
    print("BOUNDS COMPARISON")
    print("-" * 80)
    print(f"{'Coordinate':<12} {'0m File':<20} {'1m File':<20} {'Difference':>15}")
    print("-" * 80)
    
    for coord in ['xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax']:
        diff = bounds_1m[coord] - bounds_0m[coord]
        sign = "+" if diff > 0 else ""
        print(f"{coord:<12} {bounds_0m[coord]:>19.3f} {bounds_1m[coord]:>19.3f} {sign}{diff:>14.3f}")
    
    print("-" * 80)
    
    # Calculate expansion distances
    print("\nEXPANSION ANALYSIS")
    print("-" * 80)
    
    # X expansion (should be negative on min, positive on max)
    x_expansion_min = bounds_0m['xmin'] - bounds_1m['xmin']  # How much xmin moved outward (left)
    x_expansion_max = bounds_1m['xmax'] - bounds_0m['xmax']  # How much xmax moved outward (right)
    
    # Y expansion (should be negative on min, positive on max)
    y_expansion_min = bounds_0m['ymin'] - bounds_1m['ymin']  # How much ymin moved outward (down)
    y_expansion_max = bounds_1m['ymax'] - bounds_0m['ymax']  # How much ymax moved outward (up)
    
    # Z should remain the same or minimal change
    z_change_min = abs(bounds_1m['zmin'] - bounds_0m['zmin'])
    z_change_max = abs(bounds_1m['zmax'] - bounds_0m['zmax'])
    
    print(f"X-axis expansion:")
    print(f"  Min boundary (left):  {x_expansion_min:>7.3f} m")
    print(f"  Max boundary (right): {x_expansion_max:>7.3f} m")
    print(f"  Average X expansion:  {(x_expansion_min + x_expansion_max) / 2:>7.3f} m")
    print()
    print(f"Y-axis expansion:")
    print(f"  Min boundary (down):  {y_expansion_min:>7.3f} m")
    print(f"  Max boundary (up):    {y_expansion_max:>7.3f} m")
    print(f"  Average Y expansion:  {(y_expansion_min + y_expansion_max) / 2:>7.3f} m")
    print()
    print(f"Z-axis changes (should be minimal):")
    print(f"  Min boundary change:  {z_change_min:>7.3f} m")
    print(f"  Max boundary change:  {z_change_max:>7.3f} m")
    
    # Overall assessment
    avg_expansion = (x_expansion_min + x_expansion_max + y_expansion_min + y_expansion_max) / 4
    
    print()
    print("=" * 80)
    print("ASSESSMENT")
    print("=" * 80)
    print(f"Average buffer expansion: {avg_expansion:.3f} m")
    
    if abs(avg_expansion - 1.0) < 0.1:
        print("✓ Buffer distance appears correct (~1 meter)")
    elif abs(avg_expansion - 0.5) < 0.1:
        print("⚠️  Buffer distance appears to be ~0.5 meters, not 1 meter!")
    elif avg_expansion < 0.1:
        print("❌ No significant expansion detected!")
    else:
        print(f"⚠️  Unexpected buffer distance: {avg_expansion:.3f} m")
    
    # Point count change
    point_increase = points_1m - points_0m
    point_increase_pct = (point_increase / points_0m) * 100 if points_0m > 0 else 0
    
    print(f"\nPoint count change: {point_increase:+,} points ({point_increase_pct:+.1f}%)")
    
    if point_increase > 0:
        print("✓ Point count increased as expected")
    else:
        print("❌ Point count did not increase (unexpected)")
    
    print("=" * 80)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Verify buffer distance between 0m and 1m versions of LAS files'
    )
    parser.add_argument('file_0m', help='Path to 0m buffer LAS file')
    parser.add_argument('file_1m', help='Path to 1m buffer LAS file')
    
    args = parser.parse_args()
    
    try:
        compare_files(args.file_0m, args.file_1m)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
