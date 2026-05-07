#!/usr/bin/env python3
"""
Plot z_mean, z_median, z_std from Excel file
Creates visualizations similar to the pretty plots from rasterization
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import argparse
from pathlib import Path


def create_pretty_colormap():
    """Create a vibrant colormap similar to the pretty plots"""
    colors = ['#000033', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF0000', '#800000']
    n_bins = 256
    cmap = LinearSegmentedColormap.from_list('pretty', colors, N=n_bins)
    return cmap


def plot_raster_pretty(data, title, output_path, vmin=None, vmax=None, cmap=None):
    """
    Create a pretty plot similar to the rasterization outputs
    
    Args:
        data: 2D numpy array
        title: Plot title
        output_path: Path to save the plot
        vmin: Minimum value for colormap
        vmax: Maximum value for colormap
        cmap: Colormap to use
    """
    if cmap is None:
        cmap = create_pretty_colormap()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Handle NaN values
    masked_data = np.ma.masked_invalid(data)
    
    # Auto-scale if not provided
    if vmin is None:
        vmin = np.nanpercentile(data, 2)
    if vmax is None:
        vmax = np.nanpercentile(data, 98)
    
    # Plot
    im = ax.imshow(masked_data, cmap=cmap, origin='lower', 
                   interpolation='nearest', vmin=vmin, vmax=vmax)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Height (m)', rotation=270, labelpad=20, fontsize=12)
    
    # Set title
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    # Labels
    ax.set_xlabel('X Pixel Index', fontsize=12)
    ax.set_ylabel('Y Pixel Index', fontsize=12)
    
    # Grid
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Add statistics text
    stats_text = f'Valid pixels: {np.sum(~np.isnan(data)):,}\n'
    stats_text += f'Min: {np.nanmin(data):.2f} m\n'
    stats_text += f'Max: {np.nanmax(data):.2f} m\n'
    stats_text += f'Mean: {np.nanmean(data):.2f} m\n'
    stats_text += f'Median: {np.nanmedian(data):.2f} m\n'
    stats_text += f'Std: {np.nanstd(data):.2f} m'
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Saved: {output_path}")


def plot_pixel_stats_from_excel(excel_path: str, output_dir: str = None, pixel_size: float = 0.125):
    """
    Read Excel file and create plots for z_mean, z_median, z_std
    
    Args:
        excel_path: Path to input Excel file
        output_dir: Output directory for plots (default: same as Excel file)
        pixel_size: Pixel size in meters (for reference)
    """
    print(f"\nReading Excel file: {excel_path}")
    excel_path = Path(excel_path)
    
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    
    # Set output directory
    if output_dir is None:
        output_dir = excel_path.parent
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read Summary sheet
    print("  Reading Summary sheet...")
    df = pd.read_excel(excel_path, sheet_name='Summary')
    print(f"  Total pixels: {len(df):,}")
    
    # Determine grid dimensions
    max_row = df['row'].max()
    max_col = df['col'].max()
    height = max_row + 1
    width = max_col + 1
    
    print(f"\nGrid dimensions:")
    print(f"  Width: {width} pixels")
    print(f"  Height: {height} pixels")
    print(f"  Total cells: {width * height:,}")
    print(f"  Coverage: {width * pixel_size:.2f} × {height * pixel_size:.2f} m")
    
    # Create empty rasters (filled with NaN)
    z_mean_raster = np.full((height, width), np.nan, dtype=np.float32)
    z_median_raster = np.full((height, width), np.nan, dtype=np.float32)
    z_std_raster = np.full((height, width), np.nan, dtype=np.float32)
    
    # Fill rasters with data
    print("\nFilling rasters...")
    for _, row in df.iterrows():
        r = int(row['row'])
        c = int(row['col'])
        z_mean_raster[r, c] = row['z_mean']
        z_median_raster[r, c] = row['z_median']
        z_std_raster[r, c] = row['z_std']
    
    # Print statistics
    print("\n📊 Raster Statistics:")
    print(f"\nZ Mean:")
    print(f"  Valid pixels: {np.sum(~np.isnan(z_mean_raster)):,}")
    print(f"  Range: {np.nanmin(z_mean_raster):.2f} – {np.nanmax(z_mean_raster):.2f} m")
    print(f"  Mean: {np.nanmean(z_mean_raster):.2f} m")
    print(f"  Std: {np.nanstd(z_mean_raster):.2f} m")
    
    print(f"\nZ Median:")
    print(f"  Valid pixels: {np.sum(~np.isnan(z_median_raster)):,}")
    print(f"  Range: {np.nanmin(z_median_raster):.2f} – {np.nanmax(z_median_raster):.2f} m")
    print(f"  Mean: {np.nanmean(z_median_raster):.2f} m")
    print(f"  Std: {np.nanstd(z_median_raster):.2f} m")
    
    print(f"\nZ Std:")
    print(f"  Valid pixels: {np.sum(~np.isnan(z_std_raster)):,}")
    print(f"  Range: {np.nanmin(z_std_raster):.2f} – {np.nanmax(z_std_raster):.2f} m")
    print(f"  Mean: {np.nanmean(z_std_raster):.2f} m")
    print(f"  Std: {np.nanstd(z_std_raster):.2f} m")
    
    # Create plots
    print("\n🎨 Creating plots...")
    base_name = excel_path.stem.replace('_pixel_z_values', '')
    
    # Plot z_mean
    output_path = output_dir / f"{base_name}_z_mean_pretty.png"
    plot_raster_pretty(
        z_mean_raster,
        title=f'Z Mean (m) - Pixel Size: {pixel_size}m',
        output_path=output_path
    )
    
    # Plot z_median
    output_path = output_dir / f"{base_name}_z_median_pretty.png"
    plot_raster_pretty(
        z_median_raster,
        title=f'Z Median (m) - Pixel Size: {pixel_size}m',
        output_path=output_path
    )
    
    # Plot z_std
    output_path = output_dir / f"{base_name}_z_std_pretty.png"
    # Use a different colormap for std (since it's always positive and different interpretation)
    plot_raster_pretty(
        z_std_raster,
        title=f'Z Standard Deviation (m) - Pixel Size: {pixel_size}m',
        output_path=output_path,
        vmin=0,  # std is always >= 0
        cmap='viridis'
    )
    
    print(f"\n✓ All plots created successfully!")
    print(f"  Output directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Plot z_mean, z_median, z_std from Excel file'
    )
    parser.add_argument('excel_file', help='Input Excel file path (.xlsx)')
    parser.add_argument('--output-dir', '-o', default=None,
                       help='Output directory for plots (default: same as Excel file)')
    parser.add_argument('--pixel-size', type=float, default=0.125,
                       help='Pixel size in meters (default: 0.125)')
    
    args = parser.parse_args()
    
    plot_pixel_stats_from_excel(
        args.excel_file,
        output_dir=args.output_dir,
        pixel_size=args.pixel_size
    )


if __name__ == "__main__":
    main()
