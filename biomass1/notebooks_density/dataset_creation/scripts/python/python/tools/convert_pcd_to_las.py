#!/usr/bin/env python3
import open3d as o3d
import laspy
import numpy as np
import argparse

def convert_pcd_to_las(input_file, output_file=None):
    # Use input file as output if not specified
    if output_file is None:
        output_file = input_file.replace('.pcd', '.las')

    try:
        # Read PCD file using Open3D
        pcd = o3d.io.read_point_cloud(input_file)
        
        # Convert to NumPy array
        points = np.asarray(pcd.points)
        
        # Create LAS file
        las = laspy.create(point_format=3)
        
        # Set coordinates
        las.x = points[:, 0]
        las.y = points[:, 1]
        las.z = points[:, 2]
        
        # Check if there are additional point features like intensity
        if hasattr(pcd, 'colors') and len(pcd.colors) > 0:
            colors = np.asarray(pcd.colors)
            # You might want to convert color to intensity or store differently
            las.red = (colors[:, 0] * 65535).astype(np.uint16)
            las.green = (colors[:, 1] * 65535).astype(np.uint16)
            las.blue = (colors[:, 2] * 65535).astype(np.uint16)
        
        # Write LAS file
        las.write(output_file)
        
        print(f"Converted {input_file} to {output_file} successfully")
    
    except Exception as e:
        print(f"Error converting file: {e}")


def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Convert PCD files to LAS format')
    parser.add_argument('-i', '--input', required=True, help='Input folder containing PCD files')
    parser.add_argument('-o', '--output', help='Output folder for LAS files (optional)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run conversion
    convert_pcd_to_las(args.input, args.output)

if __name__ == "__main__":
    main()


# # Usage example
# input_file = './exat.pcd'
# output_file = './exat.las'
# convert_pcd_to_las(input_file, output_file)