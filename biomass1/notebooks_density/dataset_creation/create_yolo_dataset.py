#!/usr/bin/env python3
"""
YOLO Dataset Generator for Tree Detection from LiDAR Point Clouds

Creates YOLO-format dataset from LAS files with tree position labels.
Supports:
- Multi-density channel rasterization
- Label generation from CSV (X,Y coordinates → bounding boxes)
- Train/Val/Test split
- Automatic dataset organization

Example:
    python create_yolo_dataset.py --plots_dir /home/pun/Desktop/notebooks_density/processed --csv_dir /home/pun/Desktop/notebooks_density/dataset_creation/dataset/ข้อมูลแปลง
"""

import numpy as np
import pandas as pd
import laspy
import cv2
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import shutil
import sys

# Add parent dir to path for imports
sys.path.append(str(Path(__file__).parent / 'scripts' / 'python' / 'python' / 'tools'))
from pointcloud_rasterization import PointCloudRasterizer


class YOLODatasetGenerator:
    """Generate YOLO dataset from LAS point clouds and CSV labels"""
    
    def __init__(
        self,
        image_size: int = 320,
        pixel_size: float = 0.125,
        area_size: float = 40.0,
        box_size_meters: float = 2.0,  # Default bounding box size in meters (16x16 pixels)
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ):
        self.image_size = image_size
        self.pixel_size = pixel_size
        self.area_size = area_size
        self.box_size_meters = box_size_meters
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        
        # YOLO class (0 = tree)
        self.tree_class = 0
        
        # Init rasterizer
        self.rasterizer = PointCloudRasterizer(
            image_size=image_size,
            pixel_size=pixel_size,
            area_size=area_size
        )
        
    def load_tree_labels(self, csv_path: str) -> pd.DataFrame:
        """Load tree positions from CSV file"""
        print(f"Loading labels from: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Filter valid coordinates
        df = df.dropna(subset=['X', 'Y'])
        
        print(f"  Found {len(df)} valid tree labels")
        return df
        
    def meters_to_pixels(
        self,
        x_meters: float,
        y_meters: float,
        x_min: float,
        y_min: float
    ) -> Tuple[float, float]:
        """Convert meter coordinates to pixel coordinates"""
        px = (x_meters - x_min) / self.pixel_size
        py = (y_meters - y_min) / self.pixel_size
        return px, py
        
    def create_yolo_labels(
        self,
        trees_df: pd.DataFrame,
        meta: Dict,
        output_path: Path
    ) -> int:
        """
        Create YOLO format labels from tree coordinates
        
        YOLO format: <class> <x_center> <y_center> <width> <height>
        All values normalized to [0, 1]
        
        Returns:
            Number of labels created
        """
        x_min = meta['x_min']
        y_min = meta['y_min']
        width = meta['width']
        height = meta['height']
        
        # Calculate box size in pixels
        box_size_px = self.box_size_meters / self.pixel_size
        
        labels = []
        for _, tree in trees_df.iterrows():
            x_px, y_px = self.meters_to_pixels(tree['X'], tree['Y'], x_min, y_min)
            
            # Skip if outside bounds
            if x_px < 0 or x_px >= width or y_px < 0 or y_px >= height:
                continue
                
            # Normalize to [0, 1]
            x_norm = x_px / width
            y_norm = y_px / height
            w_norm = box_size_px / width
            h_norm = box_size_px / height
            
            # Ensure within bounds [0, 1]
            x_norm = np.clip(x_norm, 0, 1)
            y_norm = np.clip(y_norm, 0, 1)
            w_norm = np.clip(w_norm, 0, 1)
            h_norm = np.clip(h_norm, 0, 1)
            
            # YOLO format: class x_center y_center width height
            labels.append(f"{self.tree_class} {x_norm:.6f} {y_norm:.6f} {w_norm:.6f} {h_norm:.6f}")
        
        # Write labels to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write('\n'.join(labels))
        
        print(f"  Created {len(labels)} labels → {output_path}")
        return len(labels)
    
    def create_density_image(
        self,
        grid: np.ndarray,
        meta: Dict,
        output_path: Path,
        channel_name: str = 'density'
    ) -> np.ndarray:
        """Create normalized grayscale image from specific channel"""
        ch_idx = meta['channel_names'].index(channel_name)
        channel = grid[:, :, ch_idx]
        
        # Normalize to [0, 255]
        ch_min, ch_max = channel.min(), channel.max()
        if ch_max > ch_min:
            img = ((channel - ch_min) / (ch_max - ch_min) * 255).astype(np.uint8)
        else:
            img = np.zeros_like(channel, dtype=np.uint8)
        
        # Save as grayscale
        cv2.imwrite(str(output_path), img)
        return img
    
    def create_rgb_composite(
        self,
        grid: np.ndarray,
        meta: Dict,
        output_path: Path,
        r_channel: str = 'z_p25',
        g_channel: str = 'z_p50',
        b_channel: str = 'z_p75'
    ) -> np.ndarray:
        """Create RGB composite from 3 channels"""
        ch_names = meta['channel_names']
        
        def normalize_channel(ch_name):
            idx = ch_names.index(ch_name)
            ch = grid[:, :, idx]
            ch_min, ch_max = ch.min(), ch.max()
            if ch_max > ch_min:
                return ((ch - ch_min) / (ch_max - ch_min) * 255).astype(np.uint8)
            return np.zeros_like(ch, dtype=np.uint8)
        
        rgb = np.zeros((*grid.shape[:2], 3), dtype=np.uint8)
        rgb[:, :, 0] = normalize_channel(r_channel)  # R
        rgb[:, :, 1] = normalize_channel(g_channel)  # G
        rgb[:, :, 2] = normalize_channel(b_channel)  # B
        
        # Save as BGR for OpenCV
        cv2.imwrite(str(output_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        return rgb
    
    def create_density_std_mean_composite(
        self,
        grid: np.ndarray,
        meta: Dict,
        output_path: Path
    ) -> np.ndarray:
        """Create RGB composite from density (R), z_std (G), z_mean (B)"""
        return self.create_rgb_composite(
            grid, meta, output_path,
            r_channel='density',
            g_channel='z_std',
            b_channel='z_mean'
        )
    
    def process_plot(
        self,
        las_path: Path,
        csv_path: Path,
        output_dir: Path,
        split: str = 'train',
        create_variants: bool = True
    ) -> Dict:
        """
        Process single plot: rasterize + create labels + save images
        
        Args:
            las_path: Path to LAS file
            csv_path: Path to CSV file with tree labels
            output_dir: Base output directory
            split: 'train', 'val', or 'test'
            create_variants: Create multiple image variants (density, RGB, etc.)
        
        Returns:
            Dictionary with processing statistics
        """
        plot_name = las_path.stem
        print(f"\n{'='*60}")
        print(f"Processing: {plot_name}")
        print(f"{'='*60}")
        
        # Load and rasterize point cloud
        points, _ = self.rasterizer.load_pointcloud(str(las_path))
        grid, meta = self.rasterizer.rasterize_multi_channel(points, normalize=False)
        
        # Add HAG bands
        grid = self.rasterizer.add_hag_band_count(grid, 0.2, 1.5)
        grid = self.rasterizer.add_hag_multiband_counts(grid, 0.4, 1.4)
        
        # Resize to target size
        grid = self.rasterizer.resize_to_target(grid, self.image_size)
        meta['resized_to'] = self.image_size
        
        # Load tree labels
        trees_df = self.load_tree_labels(str(csv_path))
        
        # Create output directories
        img_dir = output_dir / 'images' / split
        label_dir = output_dir / 'labels' / split
        img_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        
        stats = {
            'plot_name': plot_name,
            'split': split,
            'num_trees': len(trees_df),
            'variants_created': []
        }
        
        # Create YOLO labels (same for all image variants)
        label_path = label_dir / f"{plot_name}.txt"
        num_labels = self.create_yolo_labels(trees_df, meta, label_path)
        stats['num_labels'] = num_labels
        
        if create_variants:
            # Create subdirectories for each variant type
            variants_info = [
                ('density', 'density', None),  # (variant_name, channel_name, is_composite)
                ('std', 'z_std', None),
                ('mean', 'z_mean', None),
                ('density_std_mean', None, 'composite'),  # RGB composite
                ('rgb_percentile', None, 'rgb'),  # z_p25, z_p50, z_p75
                ('hag', 'hag_mean', None)
            ]
            
            for variant_name, channel_name, composite_type in variants_info:
                # Create subdirectory for this variant
                variant_img_dir = img_dir / variant_name
                variant_label_dir = label_dir / variant_name
                variant_img_dir.mkdir(parents=True, exist_ok=True)
                variant_label_dir.mkdir(parents=True, exist_ok=True)
                
                # Create image
                img_path = variant_img_dir / f"{plot_name}.jpg"
                
                if composite_type == 'composite':
                    # Density-Std-Mean composite
                    self.create_density_std_mean_composite(grid, meta, img_path)
                elif composite_type == 'rgb':
                    # RGB percentile composite
                    self.create_rgb_composite(grid, meta, img_path, 'z_p25', 'z_p50', 'z_p75')
                else:
                    # Single channel
                    self.create_density_image(grid, meta, img_path, channel_name)
                
                # Copy label file for this variant
                variant_label_path = variant_label_dir / f"{plot_name}.txt"
                shutil.copy(label_path, variant_label_path)
                
                stats['variants_created'].append(variant_name)
            
        else:
            # Default: just density
            img_path = img_dir / f"{plot_name}.jpg"
            self.create_density_image(grid, meta, img_path, 'density')
            stats['variants_created'].append('default')
        
        print(f"\n✓ Processed {plot_name}:")
        print(f"  Trees found: {num_labels}/{len(trees_df)}")
        print(f"  Variants: {', '.join(stats['variants_created'])}")
        
        return stats
    
    def split_dataset(
        self,
        plot_paths: List[Path],
        seed: int = 42
    ) -> Dict[str, List[Path]]:
        """Split plots into train/val/test sets"""
        np.random.seed(seed)
        
        # Shuffle plots
        plots = np.array(plot_paths)
        np.random.shuffle(plots)
        
        n = len(plots)
        n_train = int(n * self.train_ratio)
        n_val = int(n * self.val_ratio)
        
        splits = {
            'train': plots[:n_train].tolist(),
            'val': plots[n_train:n_train + n_val].tolist(),
            'test': plots[n_train + n_val:].tolist()
        }
        
        print(f"\nDataset Split:")
        print(f"  Train: {len(splits['train'])} plots ({self.train_ratio*100:.0f}%)")
        print(f"  Val:   {len(splits['val'])} plots ({self.val_ratio*100:.0f}%)")
        print(f"  Test:  {len(splits['test'])} plots ({self.test_ratio*100:.0f}%)")
        
        return splits
    
    def create_data_yaml(
        self,
        output_dir: Path,
        class_names: List[str] = None,
        variant_name: str = None
    ):
        """Create data.yaml for YOLO training"""
        if class_names is None:
            class_names = ['tree']
        
        # Adjust paths if using variants
        if variant_name:
            train_path = f"images/train/{variant_name}"
            val_path = f"images/val/{variant_name}"
            test_path = f"images/test/{variant_name}"
        else:
            train_path = "images/train"
            val_path = "images/val"
            test_path = "images/test"
        
        yaml_content = f"""# YOLO Dataset Configuration
# LiDAR Tree Detection Dataset

path: {output_dir.absolute()}
train: {train_path}
val: {val_path}
test: {test_path}

# Classes
names:
  0: tree

# Number of classes
nc: {len(class_names)}

# Image info
image_size: {self.image_size}
pixel_size: {self.pixel_size}
area_coverage: {self.area_size}x{self.area_size}m

# Box size
default_box_size: {self.box_size_meters}m
"""
        
        if variant_name:
            yaml_path = output_dir / f'data_{variant_name}.yaml'
        else:
            yaml_path = output_dir / 'data.yaml'
            
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)
        
        print(f"\n✓ Created data.yaml: {yaml_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate YOLO dataset from LAS point clouds and CSV labels'
    )
    
    # Input/Output
    parser.add_argument('--plots_dir', type=str, required=True,
                       help='Directory containing processed LAS files')
    parser.add_argument('--csv_dir', type=str, required=True,
                       help='Directory containing plot folders with CSV labels')
    parser.add_argument('--output_dir', type=str, default='yolov11/dataset',
                       help='Output dataset directory')
    
    # Rasterization parameters
    parser.add_argument('--image_size', type=int, default=320,
                       help='Output image size (square)')
    parser.add_argument('--pixel_size', type=float, default=0.125,
                       help='Pixel size in meters')
    parser.add_argument('--area_size', type=float, default=40.0,
                       help='Coverage area size in meters')
    
    # Label parameters
    parser.add_argument('--box_size', type=float, default=2.0,
                       help='Bounding box size in meters (default 2.0m = 16x16 pixels)')
    
    # Dataset split
    parser.add_argument('--train_ratio', type=float, default=0.7)
    parser.add_argument('--val_ratio', type=float, default=0.15)
    parser.add_argument('--test_ratio', type=float, default=0.15)
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for splitting')
    
    # Options
    parser.add_argument('--use_rotated', action='store_true',
                       help='Use rotated LAS files (recommended)')
    parser.add_argument('--create_variants', action='store_true',
                       help='Create multiple image variants (density, RGB, HAG)')
    parser.add_argument('--overwrite', action='store_true',
                       help='Overwrite existing dataset')
    
    args = parser.parse_args()
    
    # Setup paths
    plots_dir = Path(args.plots_dir)
    csv_dir = Path(args.csv_dir)
    output_dir = Path(args.output_dir)
    
    if output_dir.exists() and not args.overwrite:
        print(f"Error: Output directory exists: {output_dir}")
        print("Use --overwrite to replace it")
        return
    
    # Find LAS files
    las_pattern = "*_rotated.las" if args.use_rotated else "*_optimized_*.las"
    las_files = sorted(plots_dir.glob(las_pattern))
    
    if not las_files:
        print(f"Error: No LAS files found in {plots_dir}")
        print(f"  Pattern: {las_pattern}")
        return
    
    print(f"\nFound {len(las_files)} LAS files:")
    for f in las_files:
        print(f"  - {f.name}")
    
    # Match with CSV files
    plot_pairs = []
    for las_file in las_files:
        # Extract plot name (e.g., ska-ls-h201 from ska-ls-h201_scans_optimized_1m_rotated.las)
        plot_name = las_file.stem.split('_scans')[0]
        
        # Find corresponding CSV
        csv_file = csv_dir / plot_name / 'DBHaverage.csv'
        if not csv_file.exists():
            print(f"Warning: CSV not found for {plot_name}, skipping")
            continue
        
        plot_pairs.append((las_file, csv_file))
    
    if not plot_pairs:
        print("Error: No matching LAS/CSV pairs found")
        return
    
    print(f"\nMatched {len(plot_pairs)} plot pairs")
    
    # Initialize generator
    generator = YOLODatasetGenerator(
        image_size=args.image_size,
        pixel_size=args.pixel_size,
        area_size=args.area_size,
        box_size_meters=args.box_size,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio
    )
    
    # Split dataset
    splits = generator.split_dataset([p[0] for p in plot_pairs], seed=args.seed)
    
    # Create split mapping
    split_map = {}
    for split, paths in splits.items():
        for path in paths:
            split_map[path] = split
    
    # Process all plots
    all_stats = []
    for las_file, csv_file in plot_pairs:
        split = split_map[las_file]
        stats = generator.process_plot(
            las_file, csv_file, output_dir, split,
            create_variants=args.create_variants
        )
        all_stats.append(stats)
    
    # Create data.yaml files
    if args.create_variants:
        # Create separate yaml for each variant
        variants = ['density', 'std', 'mean', 'density_std_mean', 'rgb_percentile', 'hag']
        for variant in variants:
            generator.create_data_yaml(output_dir, variant_name=variant)
    else:
        generator.create_data_yaml(output_dir)
    
    # Print summary
    print(f"\n{'='*60}")
    print("DATASET GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"\nOutput: {output_dir}")
    print(f"\nStatistics:")
    
    for split in ['train', 'val', 'test']:
        split_stats = [s for s in all_stats if s['split'] == split]
        if split_stats:
            total_trees = sum(s['num_trees'] for s in split_stats)
            total_labels = sum(s['num_labels'] for s in split_stats)
            print(f"\n{split.upper()}:")
            print(f"  Plots: {len(split_stats)}")
            print(f"  Trees: {total_labels}/{total_trees} (in bounds)")
            print(f"  Images: {sum(len(s['variants_created']) for s in split_stats)}")
    
    print(f"\nReady for YOLO training! 🎯")
    print(f"Next: python yolov11/scripts/train_yolo.py")


if __name__ == '__main__':
    main()
