#!/usr/bin/env python3
"""
Flip Y-axis in LAS files to align with rasterization coordinate system.

This script flips the Y coordinates by inverting them around the center point:
new_y = y_max + y_min - y

This ensures that the point cloud coordinates match the image coordinate system
where the Y-axis increases downward (which is typical for images/rasters).
"""

import laspy
import numpy as np
import argparse
from pathlib import Path
import sys


def flip_y_axis(input_las: str, output_las: str, verbose: bool = True):
    """
    Flip Y-axis of a LAS file by inverting Y coordinates around the center.
    
    Args:
        input_las: Path to input LAS file
        output_las: Path to output LAS file
        verbose: Print information about the flip
    """
    if verbose:
        print(f"\nProcessing: {input_las}")
    
    # Read the LAS file
    las = laspy.read(input_las)
    
    # Get original Y range
    y_min = float(las.y.min())
    y_max = float(las.y.max())
    y_center = (y_max + y_min) / 2
    y_range = y_max - y_min
    
    if verbose:
        print(f"  Original Y range: {y_min:.2f} to {y_max:.2f} m (span: {y_range:.2f} m)")
        print(f"  Y center: {y_center:.2f} m")
    
    # Create a copy of the LAS file
    las_flipped = laspy.LasData(las.header)
    
    # Copy all point data
    las_flipped.points = las.points.copy()
    
    # Flip Y coordinates around the center
    # new_y = y_max + y_min - old_y
    # This is equivalent to: new_y = 2 * y_center - old_y
    new_y_values = y_max + y_min - np.array(las.y)
    
    # Verify the flip before writing
    new_y_min = float(new_y_values.min())
    new_y_max = float(new_y_values.max())
    
    if verbose:
        print(f"  Flipped Y range: {new_y_min:.2f} to {new_y_max:.2f} m")
        print(f"  Verification: old_min={y_min:.2f} ≈ new_max={new_y_max:.2f}? {abs(y_min - new_y_max) < 0.01}")
        print(f"                old_max={y_max:.2f} ≈ new_min={new_y_min:.2f}? {abs(y_max - new_y_min) < 0.01}")
    
    # Set the flipped Y coordinates
    las_flipped.Y = new_y_values / las_flipped.header.y_scale + las_flipped.header.y_offset
    
    # Save the flipped LAS file
    las_flipped.write(output_las)
    
    if verbose:
        print(f"  ✓ Saved flipped file: {output_las}")
    
    return {
        'original_y_min': y_min,
        'original_y_max': y_max,
        'flipped_y_min': new_y_min,
        'flipped_y_max': new_y_max,
        'y_center': y_center,
        'y_range': y_range
    }


def process_directory(input_dir: str, output_dir: str = None, suffix: str = "_flipped", 
                     pattern: str = "*.las", verbose: bool = True):
    """
    Process all LAS files in a directory.
    
    Args:
        input_dir: Directory containing input LAS files
        output_dir: Directory for output files (default: same as input_dir)
        suffix: Suffix to add to output filenames (default: "_flipped")
        pattern: File pattern to match (default: "*.las")
        verbose: Print progress information
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    if output_dir is None:
        output_path = input_path
    else:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all LAS files
    las_files = sorted(input_path.glob(pattern))
    
    if not las_files:
        print(f"No files matching pattern '{pattern}' found in {input_dir}")
        sys.exit(1)
    
    print(f"\nFound {len(las_files)} file(s) to process")
    print(f"Input directory: {input_path}")
    print(f"Output directory: {output_path}")
    print(f"Suffix: '{suffix}'")
    print("=" * 70)
    
    results = []
    for i, las_file in enumerate(las_files, 1):
        # Create output filename
        if suffix:
            output_name = las_file.stem + suffix + las_file.suffix
        else:
            output_name = las_file.name
        
        output_file = output_path / output_name
        
        print(f"\n[{i}/{len(las_files)}]")
        
        try:
            result = flip_y_axis(str(las_file), str(output_file), verbose=verbose)
            result['input_file'] = las_file.name
            result['output_file'] = output_name
            result['success'] = True
            results.append(result)
        except Exception as e:
            print(f"  ✗ Error processing {las_file.name}: {e}")
            results.append({
                'input_file': las_file.name,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    successful = sum(1 for r in results if r.get('success', False))
    print(f"Successfully processed: {successful}/{len(results)} files")
    
    if successful > 0:
        print("\nFlipped files saved to:")
        for r in results:
            if r.get('success', False):
                print(f"  ✓ {r['output_file']}")
    
    failed = [r for r in results if not r.get('success', False)]
    if failed:
        print("\nFailed files:")
        for r in failed:
            print(f"  ✗ {r['input_file']}: {r.get('error', 'Unknown error')}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Flip Y-axis in LAS files to align with rasterization coordinate system.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Flip a single file
  python flip_y_axis_las.py input.las -o output_flipped.las
  
  # Process all LAS files in a directory
  python flip_y_axis_las.py yolov11/processed/ --batch
  
  # Process with custom output directory and suffix
  python flip_y_axis_las.py yolov11/processed/ --batch -o yolov11/processed_flipped -s "_y_flipped"
        """
    )
    
    parser.add_argument('input', help='Input LAS file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory (default: same as input with suffix)')
    parser.add_argument('-s', '--suffix', default='_flipped', help='Suffix for output files in batch mode (default: "_flipped")')
    parser.add_argument('--batch', action='store_true', help='Process all LAS files in input directory')
    parser.add_argument('--pattern', default='*.las', help='File pattern for batch mode (default: "*.las")')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress verbose output')
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    if args.batch:
        # Batch mode: process directory
        process_directory(
            args.input,
            output_dir=args.output,
            suffix=args.suffix,
            pattern=args.pattern,
            verbose=verbose
        )
    else:
        # Single file mode
        input_path = Path(args.input)
        
        if not input_path.exists():
            print(f"Error: Input file does not exist: {args.input}")
            sys.exit(1)
        
        if not input_path.is_file():
            print(f"Error: Input is not a file: {args.input}")
            print("Use --batch flag to process a directory")
            sys.exit(1)
        
        # Determine output path
        if args.output:
            output_path = args.output
        else:
            output_path = str(input_path.parent / f"{input_path.stem}{args.suffix}{input_path.suffix}")
        
        flip_y_axis(args.input, output_path, verbose=verbose)
        
        print("\n✓ Flip complete!")


if __name__ == "__main__":
    main()
