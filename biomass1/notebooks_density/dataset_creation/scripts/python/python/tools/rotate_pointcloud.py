import numpy as np
import laspy
import argparse
from sklearn.decomposition import PCA
from scipy.spatial import KDTree

def fit_plane_and_get_angle(points):
    """
    Fit a plane to the ground points and calculate rotation angle needed.
    
    Args:
        points: numpy array of shape (N, 3) containing point cloud data
    Returns:
        angle in degrees needed to rotate around Y axis to align with horizontal plane
    """
    # Use lowest points as approximate ground points
    z_min = np.percentile(points[:, 2], 5)  # Use bottom 5% of points
    ground_mask = points[:, 2] < z_min + 0.2  # Points within 20cm of lowest points
    ground_points = points
    # Fit plane using PCA
    pca = PCA(n_components=3)
    pca.fit(ground_points)
    
    # Get the normal vector of the fitted plane
    normal = pca.components_[2]  # Third component is normal to the plane
    
    # Project normal vector onto XZ plane (since we're rotating around Y)
    normal_xz = np.array([normal[0], 0, normal[2]])
    normal_xz = normal_xz / np.linalg.norm(normal_xz)
    
    # Calculate angle between normal_xz and vertical (0,0,1)
    vertical = np.array([0, 0, 1])
    cos_angle = np.dot(normal_xz, vertical)
    angle = np.arccos(cos_angle)
    
    # Convert to degrees
    angle_degrees = np.degrees(angle)
    
    # Adjust angle to be in the range [-90, 90]
    if angle_degrees > 90:
        angle_degrees = -(180 - angle_degrees)
    elif normal_xz[0] < 0:
        angle_degrees = -angle_degrees
        
    return angle_degrees

def rotate_pointcloud(input_file, output_file, angle_degrees=None):
    """
    Rotate a point cloud file around the Y axis using Python.
    If angle_degrees is None, automatically determine angle by fitting a plane.
    
    Args:
        input_file (str): Path to input LAS file
        output_file (str): Path to output LAS file
        angle_degrees (float, optional): Rotation angle in degrees around Y axis
    """
    try:
        # Read the input LAS file
        las = laspy.read(input_file)
        
        # Get all points as numpy array
        points = np.vstack((las.x, las.y, las.z)).T
        
        # Automatically determine angle if not provided
        if angle_degrees is None:
            angle_degrees = fit_plane_and_get_angle(points)
            print(f"Automatically determined rotation angle: {angle_degrees:.2f} degrees")
        
        # Convert angle to radians and create rotation matrix
        angle_rad = np.radians(angle_degrees)
        rotation_matrix = np.array([
            [np.cos(angle_rad), 0, -np.sin(angle_rad)],
            [0, 1, 0],
            [np.sin(angle_rad), 0, np.cos(angle_rad)]
        ])
        
        # Apply rotation to all points
        rotated_points = np.dot(points, rotation_matrix.T)
        
        # Create output LAS file with same parameters as input
        output_las = laspy.create(point_format=las.header.point_format, file_version=las.header.version)
        
        # Copy the rotated coordinates back
        output_las.x = rotated_points[:, 0]
        output_las.y = rotated_points[:, 1]
        output_las.z = rotated_points[:, 2]
        
        # Copy all other point attributes
        for dimension in las.point_format.dimension_names:
            if dimension not in ('X', 'Y', 'Z'):  # Skip coordinates as we already set them
                setattr(output_las, dimension, getattr(las, dimension))
        
        # Write the output file
        output_las.write(output_file)
        print(f"Successfully rotated point cloud and saved to {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Rotate a point cloud around the Y axis')
    parser.add_argument('input', help='Input LAS file path')
    parser.add_argument('output', help='Output LAS file path')
    parser.add_argument('--angle', type=float, help='Rotation angle in degrees (optional, will be automatically determined if not provided)')
    
    args = parser.parse_args()
    
    rotate_pointcloud(args.input, args.output, args.angle)

if __name__ == '__main__':
    main()
