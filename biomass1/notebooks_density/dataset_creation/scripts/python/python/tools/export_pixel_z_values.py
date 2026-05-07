#!/usr/bin/env python3
"""
Export Z values per pixel to Excel file
Analyzes point cloud and exports sorted Z values for each pixel
"""

import numpy as np
import laspy
import argparse
from pathlib import Path
from tqdm import tqdm
import pandas as pd


def export_pixel_z_values(las_path: str, output_path: str, pixel_size: float = 0.125, 
                          max_detail_pixels: int = 100):
    """
    Export Z values per pixel to Excel file
    
    Args:
        las_path: Path to input LAS file
        output_path: Path to output Excel file
        pixel_size: Size of each pixel in meters
        max_detail_pixels: Maximum number of pixels to export detailed Z values
    """
    print(f"\nLoading point cloud: {las_path}")
    las = laspy.read(las_path)
    points = np.vstack((las.x, las.y, las.z)).T.astype(np.float64)
    
    print(f"  Total points: {len(points):,}")
    print(f"  X range: {points[:,0].min():.2f} – {points[:,0].max():.2f} m")
    print(f"  Y range: {points[:,1].min():.2f} – {points[:,1].max():.2f} m")
    print(f"  Z range: {points[:,2].min():.2f} – {points[:,2].max():.2f} m")
    
    # Calculate grid dimensions
    x_min, y_min = points[:,0].min(), points[:,1].min()
    x_max, y_max = points[:,0].max(), points[:,1].max()
    
    width = int(np.ceil((x_max - x_min) / pixel_size))
    height = int(np.ceil((y_max - y_min) / pixel_size))
    
    print(f"\nGrid configuration:")
    print(f"  Pixel size: {pixel_size} m")
    print(f"  Grid size: {width} × {height} = {width*height:,} pixels")
    print(f"  Coverage: {width*pixel_size:.2f} × {height*pixel_size:.2f} m")
    
    # Map points to pixels
    print("\nMapping points to pixels...")
    x_idx = np.clip(((points[:,0] - x_min) / pixel_size).astype(int), 0, width-1)
    y_idx = np.clip(((points[:,1] - y_min) / pixel_size).astype(int), 0, height-1)
    pid = y_idx * width + x_idx
    z = points[:,2]
    
    # Group points by pixel
    print("Grouping points by pixel...")
    unique_pids = np.unique(pid)
    print(f"  Non-empty pixels: {len(unique_pids):,}")
    
    # Collect pixel data
    print("\nAnalyzing pixel data...")
    pixel_data = []
    pixel_z_values = {}
    
    for p in tqdm(unique_pids, desc="Processing pixels"):
        mask = pid == p
        z_vals = z[mask]
        z_sorted = np.sort(z_vals)
        
        row = int(p) // width
        col = int(p) % width
        
        pixel_info = {
            'pixel_id': int(p),
            'row': row,
            'col': col,
            'x_center': x_min + (col + 0.5) * pixel_size,
            'y_center': y_min + (row + 0.5) * pixel_size,
            'point_count': len(z_vals),
            'z_min': float(z_vals.min()),
            'z_max': float(z_vals.max()),
            'z_range': float(z_vals.max() - z_vals.min()),
            'z_mean': float(z_vals.mean()),
            'z_median': float(np.median(z_vals)),
            'z_std': float(z_vals.std()),
            'z_p05': float(np.percentile(z_vals, 5)),
            'z_p10': float(np.percentile(z_vals, 10)),
            'z_p25': float(np.percentile(z_vals, 25)),
            'z_p75': float(np.percentile(z_vals, 75)),
            'z_p90': float(np.percentile(z_vals, 90)),
            'z_p95': float(np.percentile(z_vals, 95)),
        }
        pixel_data.append(pixel_info)
        pixel_z_values[int(p)] = z_sorted
    
    # Create summary DataFrame
    print("\nCreating summary DataFrame...")
    df_summary = pd.DataFrame(pixel_data)
    df_summary = df_summary.sort_values('point_count', ascending=False)
    
    # Export to Excel
    print(f"\nExporting to Excel: {output_path}")
    output_path = Path(output_path)
    
    with pd.ExcelWriter(str(output_path), engine='openpyxl') as writer:
        # Sheet 1: Summary of all pixels
        print("  Writing summary sheet...")
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        # Sheet 2: Top pixels by point count with detailed Z values
        print(f"  Writing detailed Z values for top {max_detail_pixels} pixels...")
        top_pixels = df_summary.head(max_detail_pixels)['pixel_id'].values
        
        # Prepare data for detailed sheet
        max_points = max(len(pixel_z_values[pid]) for pid in top_pixels)
        detail_data = {'Z_Index': list(range(max_points))}
        
        for idx, pid in enumerate(top_pixels[:50]):  # Limit to 50 pixels per sheet due to Excel column limit
            z_vals = pixel_z_values[pid]
            col_name = f'Pixel_{pid}_R{df_summary[df_summary["pixel_id"]==pid]["row"].values[0]}_C{df_summary[df_summary["pixel_id"]==pid]["col"].values[0]}'
            # Pad with NaN if needed
            padded_vals = np.pad(z_vals.astype(float), (0, max_points - len(z_vals)), 
                                constant_values=np.nan)
            detail_data[col_name] = padded_vals
        
        df_detail = pd.DataFrame(detail_data)
        df_detail.to_excel(writer, sheet_name='Top50_Z_Values', index=False)
        
        # Sheet 3: Additional top 50 pixels if more than 50
        if len(top_pixels) > 50:
            print("  Writing additional detailed Z values...")
            detail_data2 = {'Z_Index': list(range(max_points))}
            for idx, pid in enumerate(top_pixels[50:min(100, len(top_pixels))]):
                z_vals = pixel_z_values[pid]
                col_name = f'Pixel_{pid}_R{df_summary[df_summary["pixel_id"]==pid]["row"].values[0]}_C{df_summary[df_summary["pixel_id"]==pid]["col"].values[0]}'
                padded_vals = np.pad(z_vals.astype(float), (0, max_points - len(z_vals)), 
                                    constant_values=np.nan)
                detail_data2[col_name] = padded_vals
            
            df_detail2 = pd.DataFrame(detail_data2)
            df_detail2.to_excel(writer, sheet_name='Top51-100_Z_Values', index=False)
        
        # Sheet 4: Statistics summary
        print("  Writing statistics sheet...")
        stats_data = {
            'Metric': [
                'Total Points', 'Total Pixels', 'Non-empty Pixels', 'Empty Pixels',
                'Min Point Count', 'Max Point Count', 'Mean Point Count', 'Median Point Count',
                'Min Z (all)', 'Max Z (all)', 'Mean Z (all)', 'Median Z (all)'
            ],
            'Value': [
                len(points), width * height, len(unique_pids), width * height - len(unique_pids),
                df_summary['point_count'].min(), df_summary['point_count'].max(),
                df_summary['point_count'].mean(), df_summary['point_count'].median(),
                z.min(), z.max(), z.mean(), np.median(z)
            ]
        }
        df_stats = pd.DataFrame(stats_data)
        df_stats.to_excel(writer, sheet_name='Statistics', index=False)
    
    print(f"\n✓ Export complete!")
    print(f"  Excel file: {output_path}")
    print(f"  Sheets created:")
    print(f"    - Summary: All {len(unique_pids):,} non-empty pixels with statistics")
    print(f"    - Top50_Z_Values: Detailed sorted Z values for top 50 pixels")
    if len(top_pixels) > 50:
        print(f"    - Top51-100_Z_Values: Detailed sorted Z values for pixels 51-100")
    print(f"    - Statistics: Overall statistics")
    
    # Print some interesting statistics
    print(f"\n📊 Key Statistics:")
    print(f"  Pixels with most points:")
    for i, row in df_summary.head(10).iterrows():
        print(f"    Pixel {int(row['pixel_id']):5d} (R{int(row['row']):3d}, C{int(row['col']):3d}): {int(row['point_count']):4d} points, Z: [{row['z_min']:6.2f}, {row['z_max']:6.2f}] m")


def main():
    parser = argparse.ArgumentParser(
        description='Export sorted Z values per pixel to Excel file'
    )
    parser.add_argument('input_las', help='Input .las file path')
    parser.add_argument('--output', '-o', default=None,
                       help='Output .xlsx file path (default: <input>_pixel_z_values.xlsx)')
    parser.add_argument('--pixel-size', type=float, default=0.125,
                       help='Pixel size in meters (default: 0.125)')
    parser.add_argument('--max-detail-pixels', type=int, default=100,
                       help='Maximum number of pixels to export detailed Z values (default: 100)')
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output is None:
        input_path = Path(args.input_las)
        output_path = input_path.parent / f"{input_path.stem}_pixel_z_values.xlsx"
    else:
        output_path = Path(args.output)
    
    export_pixel_z_values(
        args.input_las,
        str(output_path),
        pixel_size=args.pixel_size,
        max_detail_pixels=args.max_detail_pixels
    )


if __name__ == "__main__":
    main()


# cd /Users/songkarn/locarb/biomass/hand
# held-lidar-slam-toolbox && python scripts/python/tools/export_pixel_z_values.py output/scans_t
# est_optimized_1m.las --output output/test_histogram/pixel_z_values.xlsx
