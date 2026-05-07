#!/usr/bin/env python3
"""
Batch process all plots in yolov11/dataset/ข้อมูลแปลง/
Convert .pcd files to optimized .las files with filtering
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add scripts/python to path for imports
script_dir = Path(__file__).parent / "scripts" / "python" / "python"
sys.path.insert(0, str(script_dir))

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Batch process all plots with filtering and rotation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process with 1m buffer (default)
  python batch_process_plots.py
  
  # Process with 0m buffer (no expansion)
  python batch_process_plots.py --buffer 0
  
  # Process with custom buffer
  python batch_process_plots.py --buffer 0.5
        """
    )
    parser.add_argument(
        '--buffer', '-b',
        type=float,
        default=1.0,
        help='Buffer distance in meters for Minkowski expansion (default: 1.0). Use 0 for no expansion.'
    )
    parser.add_argument(
        '--grid-size', '-g',
        type=float,
        default=0.5,
        help='Grid size in meters for filtering (default: 0.5)'
    )
    
    args = parser.parse_args()
    buffer_distance = args.buffer
    grid_size = args.grid_size
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir /"dataset_creation"/ "dataset" / "ข้อมูลแปลง"
    output_dir = base_dir / "processed"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Format buffer string for filenames
    buffer_str = f"{int(buffer_distance)}m" if buffer_distance == int(buffer_distance) else f"{buffer_distance}m"
    
    print(f"{'='*60}")
    print(f"BATCH PROCESSING CONFIGURATION")
    print(f"{'='*60}")
    print(f"Buffer distance: {buffer_distance}m")
    print(f"Grid size: {grid_size}m")
    print(f"Output naming: *_scans_optimized_{buffer_str}.las")
    print(f"{'='*60}\n")
    
    # Get all plot directories
    plot_dirs = [d for d in data_dir.iterdir() if d.is_dir() and d.name.startswith('ska-ls')]
    
    if not plot_dirs:
        print("❌ No plot directories found!")
        return
    
    print(f"Found {len(plot_dirs)} plots to process:")
    for plot_dir in sorted(plot_dirs):
        print(f"  - {plot_dir.name}")
    print()
    
    # Process each plot
    for i, plot_dir in enumerate(sorted(plot_dirs), 1):
        plot_name = plot_dir.name
        print(f"{'='*60}")
        print(f"Processing {i}/{len(plot_dirs)}: {plot_name} ({buffer_str} buffer)")
        print(f"{'='*60}")
        
        # Define file paths
        pcd_file = plot_dir / "scans.pcd"
        
        # Try to find odom file (case-insensitive)
        odom_file = plot_dir / f"odom_{plot_name}.txt"
        if not odom_file.exists():
            # Try case-insensitive search
            odom_files = list(plot_dir.glob(f"odom_{plot_name.lower()}.txt"))
            if not odom_files:
                odom_files = list(plot_dir.glob(f"odom_*.txt"))
            if odom_files:
                odom_file = odom_files[0]
        
        # Output paths
        las_file = output_dir / f"{plot_name}_scans_temp.las"
        optimized_las = output_dir / f"{plot_name}_scans_optimized_{buffer_str}.las"
        rotated_las = output_dir / f"{plot_name}_scans_optimized_{buffer_str}_rotated.las"
        
        # Check if files exist
        if not pcd_file.exists():
            print(f"❌ Missing {pcd_file.name}")
            continue
        if not odom_file.exists():
            print(f"❌ Missing odom file for {plot_name}")
            continue
        
        # Step 1: Convert PCD to LAS
        print(f"\n📝 Step 1: Converting PCD to LAS...")
        convert_cmd = [
            sys.executable,
            str(script_dir / "tools" / "convert_pcd_to_las.py"),
            "-i", str(pcd_file),
            "-o", str(las_file)
        ]
        
        try:
            result = subprocess.run(convert_cmd, capture_output=True, text=True, check=True)
            print(f"✅ Converted to {las_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Conversion failed: {e.stderr}")
            continue
        
        # Step 2: Apply optimized filter
        buffer_desc = f"{buffer_distance}m buffer" if buffer_distance > 0 else "NO EXPANSION"
        print(f"\n📝 Step 2: Applying optimized filter ({buffer_desc})...")
        filter_cmd = [
            sys.executable,
            str(script_dir / "preprocessing" / "filter_pointcloud_by_odom_optimized.py"),
            str(las_file),
            str(odom_file),
            "-o", str(optimized_las),
            "--grid-size", str(grid_size),
            "--buffer", str(buffer_distance),
            "-p"
        ]
        
        try:
            result = subprocess.run(filter_cmd, capture_output=True, text=True, check=True)
            print(result.stdout)
            print(f"✅ Created {optimized_las.name}")
            
            # Remove intermediate LAS file to save space
            if las_file.exists():
                las_file.unlink()
                print(f"🗑️  Removed intermediate file {las_file.name}")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Filtering failed: {e.stderr}")
            continue
        
        # Step 3: Rotate point cloud to align with horizontal ground plane
        print(f"\n📝 Step 3: Rotating point cloud...")
        rotate_cmd = [
            sys.executable,
            str(script_dir / "tools" / "rotate_pointcloud.py"),
            str(optimized_las),
            str(rotated_las)
        ]
        
        try:
            result = subprocess.run(rotate_cmd, capture_output=True, text=True, check=True)
            print(result.stdout)
            print(f"✅ Created {rotated_las.name}")
            
            # Remove non-rotated optimized file to save disk space
            if optimized_las.exists():
                optimized_las.unlink()
                print(f"🗑️  Removed non-rotated file {optimized_las.name} (keeping only rotated version)")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Rotation failed: {e.stderr}")
            print(f"⚠️  Keeping non-rotated file {optimized_las.name}")
        
        print(f"\n✅ Successfully processed {plot_name}\n")
    
    # Summary
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Output directory: {output_dir}")
    print(f"Buffer used: {buffer_distance}m")
    print(f"\nProcessed files (rotated versions only):")
    
    # Show only rotated files to save disk space
    total_size = 0
    count = 0
    for las_file in sorted(output_dir.glob(f"*_optimized_{buffer_str}_rotated.las")):
        file_size = las_file.stat().st_size / (1024 * 1024)  # MB
        print(f"  ✅ {las_file.name} ({file_size:.1f} MB)")
        total_size += file_size
        count += 1
    
    print(f"\nTotal: {count} files ({total_size:.1f} MB)")
    print(f"Note: Non-rotated versions were removed to save disk space")


if __name__ == "__main__":
    main()


#python batch_process_plots.py --buffer 0
#python batch_process_plots.py --buffer 0.5
#python batch_process_plots.py --buffer 1.0 --grid-size 0.5
