#!/usr/bin/env python3
"""
Organize experimental output files into categorized folders.

This script moves experimental output files into organized folders:
- experiments/visualizations/ - All PNG/image files
- experiments/point_clouds/ - All LAS files (filtered results)
- experiments/reports/ - All text reports
- experiments/timing/ - Timing-related outputs

Keeps essential files in the output/ directory (like main scans.las, scans.pcd)
"""

import os
import shutil
from pathlib import Path


def organize_outputs(output_dir='output', create_structure=True):
    """
    Organize experimental output files into categorized folders.
    
    Args:
        output_dir: Path to output directory
        create_structure: Whether to create folder structure if it doesn't exist
    """
    output_path = Path(output_dir)
    
    if not output_path.exists():
        print(f"✗ Output directory {output_dir} doesn't exist")
        return
    
    # Define folder structure
    experiments_base = output_path / 'experiments'
    folders = {
        'visualizations': experiments_base / 'visualizations',
        'point_clouds': experiments_base / 'point_clouds',
        'reports': experiments_base / 'reports',
        'timing': experiments_base / 'timing'
    }
    
    # Create folders if needed
    if create_structure:
        for folder_name, folder_path in folders.items():
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created {folder_path}")
    
    # Define file categorization rules
    # Format: (pattern, destination_folder, description)
    categorization_rules = [
        # Visualizations (PNG files)
        ('2d_*.png', 'visualizations', '2D method visualizations'),
        ('3d_*.png', 'visualizations', '3D method visualizations'),
        ('grid_*.png', 'visualizations', 'Grid method visualizations'),
        ('*_comparison.png', 'visualizations', 'Comparison visualizations'),
        ('*_expansion.png', 'visualizations', 'Expansion visualizations'),
        ('timing_*.png', 'timing', 'Timing visualizations'),
        
        # Point clouds (LAS files - experimental only)
        ('scans_test_*.las', 'point_clouds', 'Test point clouds'),
        ('scans_minkowski.las', 'point_clouds', 'Minkowski expansion result'),
        ('scans_rotated.las', 'point_clouds', 'Rotated point cloud'),
        ('scans_buffered.las', 'point_clouds', 'Buffered point cloud'),
        ('test_*.las', 'point_clouds', 'Test outputs'),
        
        # Reports (TXT files)
        ('*_report.txt', 'reports', 'Experiment reports'),
        ('comparison_*.txt', 'reports', 'Comparison reports'),
    ]
    
    # Files to keep in main output folder (essential outputs)
    keep_in_output = {
        'scans.las',
        'scans.pcd',
        'odom_ska-ls-h201.txt',
        '.DS_Store'
    }
    
    moved_files = {folder: [] for folder in folders.keys()}
    skipped_files = []
    
    # Process files
    for file_path in output_path.iterdir():
        if file_path.is_file():
            filename = file_path.name
            
            # Skip essential files
            if filename in keep_in_output:
                skipped_files.append(filename)
                continue
            
            # Check against categorization rules
            moved = False
            for pattern, folder_key, description in categorization_rules:
                if file_path.match(pattern):
                    dest_folder = folders[folder_key]
                    dest_path = dest_folder / filename
                    
                    # Move file
                    try:
                        shutil.move(str(file_path), str(dest_path))
                        moved_files[folder_key].append(filename)
                        moved = True
                        break
                    except Exception as e:
                        print(f"✗ Error moving {filename}: {e}")
            
            if not moved and filename not in keep_in_output:
                # File doesn't match any rule and isn't essential
                print(f"  ℹ Unmatched file (keeping in output/): {filename}")
    
    # Print summary
    print("\n" + "="*60)
    print("ORGANIZATION SUMMARY")
    print("="*60)
    
    total_moved = 0
    for folder_key, files in moved_files.items():
        if files:
            print(f"\n{folder_key.upper()}: ({len(files)} files)")
            for f in sorted(files):
                print(f"  ✓ {f}")
            total_moved += len(files)
    
    if skipped_files:
        print(f"\nKEPT IN OUTPUT/: ({len(skipped_files)} files)")
        for f in sorted(skipped_files):
            print(f"  → {f}")
    
    print(f"\n{'='*60}")
    print(f"Total files moved: {total_moved}")
    print(f"Files kept in output/: {len(skipped_files)}")
    print(f"{'='*60}\n")
    
    # Create README in experiments folder
    readme_path = experiments_base / 'README.md'
    with open(readme_path, 'w') as f:
        f.write("""# Experimental Outputs

This directory contains organized experimental outputs from filter testing.

## Folder Structure

- **visualizations/** - PNG images showing filtering process steps, comparisons, and timing
- **point_clouds/** - LAS files from various experimental filter methods
- **reports/** - Text reports with performance metrics and comparisons
- **timing/** - Timing analysis outputs and visualizations

## File Naming Conventions

### Visualizations
- `2d_*.png` - 2D filtering method visualizations
- `3d_*.png` - 3D filtering method visualizations  
- `grid_*.png` - Grid-based filtering method visualizations
- `*_comparison.png` - Method comparison visualizations
- `*_expansion.png` - Hull expansion visualizations

### Point Clouds
- `scans_test_*.las` - Test outputs from different methods
- `scans_minkowski.las` - Minkowski expansion result
- `scans_buffered.las` - Buffered convex hull result
- `scans_rotated.las` - Rotated point cloud

### Reports
- `*_report.txt` - Detailed experiment reports with metrics
- `comparison_*.txt` - Comparison between different methods

## Main Output Directory

The parent `output/` directory contains essential files:
- `scans.las` - Main filtered point cloud output
- `scans.pcd` - Point cloud in PCD format
- `odom_*.txt` - Odometry data files
""")
    print(f"✓ Created README at {readme_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Organize experimental output files into categorized folders'
    )
    parser.add_argument('--output-dir', default='output',
                       help='Output directory path (default: output)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without moving files')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be moved\n")
        # TODO: Implement dry run logic
        print("Dry run not yet implemented. Run without --dry-run to organize files.")
    else:
        organize_outputs(args.output_dir)


if __name__ == '__main__':
    main()
