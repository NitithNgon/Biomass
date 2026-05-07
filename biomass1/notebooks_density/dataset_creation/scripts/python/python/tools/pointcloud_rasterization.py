#!/usr/bin/env python3
"""
Point Cloud Rasterization to Multi-Channel 2D Grid
(Full + Extended Z/HAG Percentiles + HAG band & multiband with blur)

Features:
- Multi-channel raster (density, z stats, z percentiles, HAG mean & HAG percentiles)
- HAG band count: count of points whose HAG is in [low, high]
- HAG multiband counts: low/mid/high by two cutpoints (b1, b2) + RGB composite
- Pretty plots for Z and HAG channels, optional Gaussian blur on HAG-derived maps
- Optional comparison figure: density vs hag_high_count (side-by-side + overlay)

CLI tips:
  --no_normalize         keep raw meters for z/hag (density always raw count)
  --min-density N        mask pixels with density < N (in plots/PNGs)
  --hag-sigma S          Gaussian blur sigma (pixels) applied to HAG-derived maps
  --hag-band-low/--hag-band-high
  --hag-b1/--hag-b2
"""

import numpy as np
import laspy
import cv2
import os
import json
import argparse
from pathlib import Path
from typing import Tuple, Dict, List, Optional
import matplotlib.pyplot as plt
from scipy import ndimage


# ----------------------------- Helpers -----------------------------
def _apply_optional_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    if sigma is None or sigma <= 0:
        return img
    # heuristic kernel (odd)
    k = int(max(3, (int(round(sigma * 6)) | 1)))
    return cv2.GaussianBlur(img, (k, k), sigmaX=sigma, sigmaY=sigma, borderType=cv2.BORDER_REPLICATE)


def _norm01(x: np.ndarray) -> np.ndarray:
    x = x.astype(float)
    mn, mx = float(x.min()), float(x.max())
    if mx <= mn:
        return np.zeros_like(x, dtype=float)
    return (x - mn) / (mx - mn)


def save_density_vs_hag_high(grid: np.ndarray, meta: Dict, out_path_base: Path, *,
                             min_density: int = 10, overlay_alpha: float = 0.65) -> None:
    """Save (1) side-by-side and (2) overlay comparison between density and hag_high_count."""
    ch = meta['channel_names']
    den = np.nan_to_num(grid[:, :, 0], nan=0.0)
    high = np.nan_to_num(grid[:, :, ch.index('hag_high_count')], nan=0.0)

    high_masked = high.copy()
    high_masked[den < min_density] = 0.0

    den_n = _norm01(den)
    high_n = _norm01(high_masked)

    # Side-by-side
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    im0 = axes[0].imshow(den_n, cmap='gray')
    axes[0].set_title('Density (normalized)'); axes[0].axis('off')
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(high_n, cmap='inferno')
    axes[1].set_title('HAG High Count (normalized, masked)'); axes[1].axis('off')
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    plt.tight_layout()
    p1 = Path(f"{out_path_base}_density_vs_hag_high_side_by_side.png")
    plt.savefig(str(p1), dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved comparison (side-by-side): {p1}")

    # Overlay
    fig = plt.figure(figsize=(8, 8))
    plt.imshow(den_n, cmap='gray')
    plt.imshow(high_n, cmap='inferno', alpha=overlay_alpha)
    plt.title(f"Overlay: HAG High on Density (alpha={overlay_alpha})")
    plt.axis('off')
    p2 = Path(f"{out_path_base}_density_vs_hag_high_overlay.png")
    plt.savefig(str(p2), dpi=150, bbox_inches='tight'); plt.close()
    print(f"Saved comparison (overlay): {p2}")


# ----------------------------- Rasterizer -----------------------------
class PointCloudRasterizer:
    def __init__(self, image_size=320, pixel_size=0.125, area_size=40.0):
        self.image_size = image_size
        self.pixel_size = pixel_size
        self.area_size = area_size
        print("Rasterizer Configuration:")
        print(f"  Image size: {image_size}×{image_size} px")
        print(f"  Pixel size: {pixel_size} m/pixel")
        print(f"  Area coverage (target): {area_size}×{area_size} m")

    # ---------- IO ----------
    def load_pointcloud(self, las_path: str) -> Tuple[np.ndarray, Dict]:
        print(f"\nLoading point cloud: {las_path}")
        las = laspy.read(las_path)
        points = np.vstack((las.x, las.y, las.z)).T.astype(np.float64)
        meta = {
            'num_points': int(points.shape[0]),
            'x_min': float(points[:,0].min()), 'x_max': float(points[:,0].max()),
            'y_min': float(points[:,1].min()), 'y_max': float(points[:,1].max()),
            'z_min': float(points[:,2].min()), 'z_max': float(points[:,2].max()),
        }
        print(f"  Points: {meta['num_points']:,}")
        print(f"  X range: {meta['x_min']:.2f} – {meta['x_max']:.2f} m")
        print(f"  Y range: {meta['y_min']:.2f} – {meta['y_max']:.2f} m")
        print(f"  Z range: {meta['z_min']:.2f} – {meta['z_max']:.2f} m")
        return points, meta

    # ---------- Percentile helper ----------
    def _compute_percentiles_per_pixel(
        self,
        values_sorted: np.ndarray,
        pid_sorted: np.ndarray,
        width: int,
        percentiles: List[int]
    ) -> Dict[int, np.ndarray]:
        uniq, starts = np.unique(pid_sorted, return_index=True)
        ends = np.r_[starts[1:], pid_sorted.size]

        grids = {p: np.full(self._grid_hw, np.nan, dtype=np.float32) for p in percentiles}
        H, W = self._grid_hw

        for s, e, pid in zip(starts, ends, uniq):
            vals = values_sorted[s:e]
            if vals.size == 0: 
                continue
            r, c = divmod(int(pid), width)
            for p in percentiles:
                grids[p][r, c] = np.percentile(vals, p)

        return grids

    # ---------- Core rasterization ----------
    def rasterize_multi_channel(self, points: np.ndarray, normalize: bool = True) -> Tuple[np.ndarray, Dict]:
        """
        Channels layout (C=23):
          0: density (raw count)
          1: z_max
          2: z_min
          3: z_range
          4: z_mean
          5: z_std
          6: hag_mean
          7..15 : z_p01, z_p05, z_p10, z_p25, z_p50, z_p75, z_p90, z_p95, z_p99
          16..18: hag_p05, hag_p10, hag_p25
          19: hag_band_count          (single band; filled later)
          20..22: hag_low/mid/high_count (multiband; filled later)
        """
        print("\nRasterizing to multi-channel grid...")
        x_min, y_min = points[:,0].min(), points[:,1].min()
        x_max, y_max = points[:,0].max(), points[:,1].max()

        width  = int(np.ceil((x_max - x_min) / self.pixel_size))
        height = int(np.ceil((y_max - y_min) / self.pixel_size))
        self._grid_hw = (height, width)

        print(f"  Grid size: {width}×{height} px ({width*height:,} total)")
        print(f"  Coverage: {width*self.pixel_size:.2f}×{height*self.pixel_size:.2f} m")

        # map points → pixel indices
        x_idx = np.clip(((points[:,0] - x_min) / self.pixel_size).astype(int), 0, width-1)
        y_idx = np.clip(((points[:,1] - y_min) / self.pixel_size).astype(int), 0, height-1)
        pid = y_idx * width + x_idx
        z = points[:,2].astype(np.float64)

        # allocate channels
        z_percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]      # 9
        hag_percentiles = [5, 10, 25]                           # 3
        C = 23
        chans = np.zeros((height, width, C), dtype=np.float32)

        # ch0 density (fast bincount)
        print("  Computing density...")
        flat_density = np.bincount(pid, minlength=height*width)
        chans[:,:,0] = flat_density.reshape(height, width)

        # z stats
        print("  Computing z_min/z_max/z_range/z_mean/z_std ...")
        idx = np.arange(height*width)
        z_max_grid = ndimage.maximum(z, pid, index=idx).reshape(height, width)
        z_min_grid = ndimage.minimum(z, pid, index=idx).reshape(height, width)
        chans[:,:,1] = z_max_grid
        chans[:,:,2] = z_min_grid
        chans[:,:,3] = z_max_grid - z_min_grid

        z_sum = np.bincount(pid, weights=z, minlength=height*width).reshape(height, width)
        with np.errstate(divide='ignore', invalid='ignore'):
            chans[:,:,4] = z_sum / np.maximum(chans[:,:,0], 1)
        
        # Compute z_std (standard deviation)
        z_mean_flat = chans[:,:,4].reshape(-1)
        z_sq_sum = np.bincount(pid, weights=(z - z_mean_flat[pid])**2, minlength=height*width).reshape(height, width)
        with np.errstate(divide='ignore', invalid='ignore'):
            chans[:,:,5] = np.sqrt(z_sq_sum / np.maximum(chans[:,:,0], 1))

        # HAG per-point
        print("  Computing HAG (height above ground) ...")
        zmin_flat = z_min_grid.reshape(-1)
        hag_per_point = z - zmin_flat[pid]
        hag_sum = np.bincount(pid, weights=hag_per_point, minlength=height*width).reshape(height, width)
        with np.errstate(divide='ignore', invalid='ignore'):
            chans[:,:,6] = hag_sum / np.maximum(chans[:,:,0], 1)

        # Z percentiles per pixel
        print("  Computing Z percentiles per pixel ...")
        order_z = np.argsort(pid, kind='mergesort')
        z_grids = self._compute_percentiles_per_pixel(z[order_z], pid[order_z], width, z_percentiles)
        for i, p in enumerate(z_percentiles):
            chans[:,:,7 + i] = z_grids[p]

        # HAG percentiles per pixel
        print("  Computing HAG percentiles per pixel ...")
        order_h = np.argsort(pid, kind='mergesort')
        hag_grids = self._compute_percentiles_per_pixel(hag_per_point[order_h], pid[order_h], width, hag_percentiles)
        chans[:,:,16] = hag_grids[5]    # hag_p05
        chans[:,:,17] = hag_grids[10]   # hag_p10
        chans[:,:,18] = hag_grids[25]   # hag_p25

        # keep per-point HAG & pid for band counting later
        self._hag_per_point = hag_per_point
        self._pid = pid

        # Fill NaN/Inf → 0 globally
        chans = np.nan_to_num(chans, nan=0.0, posinf=0.0, neginf=0.0)

        channel_names = [
            'density','z_max','z_min','z_range','z_mean','z_std','hag_mean',
            *[f"z_p{p:02d}" for p in z_percentiles],
            'hag_p05','hag_p10','hag_p25','hag_band_count',
            'hag_low_count','hag_mid_count','hag_high_count'
        ]
        meta = {
            'width': width, 'height': height,
            'x_min': float(x_min), 'y_min': float(y_min),
            'x_max': float(x_max), 'y_max': float(y_max),
            'pixel_size': float(self.pixel_size),
            'num_channels': C,
            'channel_names': channel_names,
            'normalized': bool(normalize)
        }
        print(f"  ✓ Created {C}-channel grid: {height}×{width}×{C}")
        return chans, meta

    # ---- HAG band (single) ----
    def add_hag_band_count(self, grid: np.ndarray, low: float, high: float) -> np.ndarray:
        H, W, _ = grid.shape
        pid = self._pid
        hag = self._hag_per_point
        mask = (hag >= low) & (hag <= high)
        band_flat = np.bincount(pid[mask], minlength=H*W)
        grid[:,:,19] = band_flat.reshape(H, W).astype(np.float32)
        return grid

    # ---- HAG multiband (low/mid/high by two cutpoints) ----
    def add_hag_multiband_counts(self, grid: np.ndarray, b1: float, b2: float) -> np.ndarray:
        H, W, _ = grid.shape
        pid = self._pid
        hag = self._hag_per_point
        low_mask  = (hag > 0) & (hag <= b1)
        mid_mask  = (hag > b1) & (hag <= b2)
        high_mask = (hag > b2)
        low_flat  = np.bincount(pid[low_mask],  minlength=H*W)
        mid_flat  = np.bincount(pid[mid_mask],  minlength=H*W)
        high_flat = np.bincount(pid[high_mask], minlength=H*W)
        grid[:,:,20] = low_flat.reshape(H, W).astype(np.float32)
        grid[:,:,21] = mid_flat.reshape(H, W).astype(np.float32)
        grid[:,:,22] = high_flat.reshape(H, W).astype(np.float32)
        return grid

    # ---------- Resize ----------
    def resize_to_target(self, grid: np.ndarray, target_size: Optional[int] = None) -> np.ndarray:
        if target_size is None:
            target_size = self.image_size
        H, W, C = grid.shape
        if (H, W) == (target_size, target_size):
            return np.nan_to_num(grid, nan=0.0, posinf=0.0, neginf=0.0)
        print(f"Resizing {H}×{W} → {target_size}×{target_size} ...")
        out = np.zeros((target_size, target_size, C), dtype=np.float32)
        for c in range(C):
            interp = cv2.INTER_NEAREST if c == 0 else cv2.INTER_LINEAR
            out[:,:,c] = cv2.resize(grid[:,:,c], (target_size, target_size), interpolation=interp)
        return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)

    # ---------- Save channels as PNG ----------
    def save_channels_png(self, grid: np.ndarray, out_dir: str, base_name: str, channel_names: List[str], *,
                          min_density:int=0, blur_sigma:float=0.0):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ch_dir = out_dir / f"{base_name}_channels"
        ch_dir.mkdir(parents=True, exist_ok=True)

        density = grid[:,:,0]
        for c, name in enumerate(channel_names):
            ch = np.nan_to_num(grid[:,:,c], nan=0.0, posinf=0.0, neginf=0.0)

            # optional mask by density
            if min_density > 0:
                ch = ch.copy()
                ch[density < min_density] = 0.0

            # optional blur for HAG-derived maps
            if blur_sigma and name.startswith('hag_'):
                ch = _apply_optional_blur(ch, blur_sigma)

            ch_min, ch_max = float(ch.min()), float(ch.max())
            if ch_max > ch_min:
                img = ((ch - ch_min) / (ch_max - ch_min) * 255).astype(np.uint8)
            else:
                img = np.zeros_like(ch, dtype=np.uint8)
            cv2.imwrite(str(ch_dir / f"{name}.png"), img)
        print(f"Saved {len(channel_names)} channel PNGs to {ch_dir}")

    # ---------- RGB composite (generic) ----------
    def create_rgb_composite(self, grid: np.ndarray, channels=(0,4,5), out_path: Optional[Path] = None):
        rgb = np.zeros((*grid.shape[:2], 3), dtype=np.uint8)
        for i, c in enumerate(channels):
            ch = np.nan_to_num(grid[:,:,c], nan=0.0, posinf=0.0, neginf=0.0)
            mn, mx = float(ch.min()), float(ch.max())
            if mx > mn:
                rgb[:,:,i] = ((ch - mn) / (mx - mn) * 255).astype(np.uint8)
        if out_path is not None:
            out_path = Path(out_path)
            cv2.imwrite(str(out_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
            print(f"Saved RGB composite: {out_path}")
        return rgb

    # ---------- Pretty plot ----------
    @staticmethod
    def _save_single_plot(grid, meta, ch_name, out_path: Path, min_density=10, label='Value', blur_sigma:float=0.0):
        ch_names = meta['channel_names']
        if ch_name not in ch_names:
            print(f"[skip] channel '{ch_name}' not found.")
            return
        idx = ch_names.index(ch_name)
        img = np.nan_to_num(grid[:, :, idx].astype(float), nan=0.0, posinf=0.0, neginf=0.0)
        den = np.nan_to_num(grid[:, :, ch_names.index('density')], nan=0.0)
        masked = img.copy()
        masked[den < min_density] = 0.0
        if blur_sigma and ch_name.startswith('hag_'):
            masked = _apply_optional_blur(masked, blur_sigma)

        plt.figure(figsize=(8, 8))
        im = plt.imshow(masked, cmap='viridis')
        plt.title(f"{ch_name} (density < {min_density} → 0)", fontsize=14, fontweight='bold')
        plt.axis('off')
        cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
        unit = '' if meta.get('normalized', True) else ' (m)'
        cbar.set_label(label + unit, rotation=270, labelpad=16)
        plt.tight_layout()
        out_path = Path(out_path)
        plt.savefig(str(out_path), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Saved: {out_path}")

    # ---------- Density histogram ----------
    @staticmethod
    def save_density_histogram(grid: np.ndarray, meta: Dict, out_path: Path, bins: int = 50):
        """Create and save histogram of points per pixel (density distribution)."""
        density = np.nan_to_num(grid[:, :, 0], nan=0.0, posinf=0.0, neginf=0.0).flatten()
        
        # Remove zero values (empty pixels) for clearer visualization
        density_nonzero = density[density > 0]
        
        if density_nonzero.size == 0:
            print("[skip] No non-zero density values for histogram")
            return
        
        # Calculate statistics
        stats = {
            'total_pixels': int(density.size),
            'non_zero_pixels': int(density_nonzero.size),
            'min': float(density_nonzero.min()),
            'max': float(density_nonzero.max()),
            'mean': float(density_nonzero.mean()),
            'median': float(np.median(density_nonzero)),
            'std': float(density_nonzero.std()),
            'percentile_25': float(np.percentile(density_nonzero, 25)),
            'percentile_75': float(np.percentile(density_nonzero, 75)),
            'percentile_95': float(np.percentile(density_nonzero, 95)),
            'percentile_99': float(np.percentile(density_nonzero, 99))
        }
        
        # Create histogram figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Top plot: Full range histogram
        counts, bins_edges, patches = ax1.hist(density_nonzero, bins=bins, color='steelblue', 
                                                edgecolor='black', alpha=0.7)
        ax1.axvline(stats['mean'], color='red', linestyle='--', linewidth=2, label=f"Mean: {stats['mean']:.1f}")
        ax1.axvline(stats['median'], color='green', linestyle='--', linewidth=2, label=f"Median: {stats['median']:.1f}")
        ax1.axvline(stats['percentile_95'], color='orange', linestyle='--', linewidth=2, label=f"P95: {stats['percentile_95']:.1f}")
        ax1.set_xlabel('Points per Pixel', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax1.set_title('Density Distribution: Points per Pixel (Full Range)', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Bottom plot: Zoomed to 95th percentile for better detail
        density_p95 = density_nonzero[density_nonzero <= stats['percentile_95']]
        ax2.hist(density_p95, bins=bins, color='steelblue', edgecolor='black', alpha=0.7)
        ax2.axvline(stats['mean'], color='red', linestyle='--', linewidth=2, label=f"Mean: {stats['mean']:.1f}")
        ax2.axvline(stats['median'], color='green', linestyle='--', linewidth=2, label=f"Median: {stats['median']:.1f}")
        ax2.set_xlabel('Points per Pixel', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax2.set_title('Density Distribution: Points per Pixel (Zoomed to P95)', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        out_path = Path(out_path)
        plt.savefig(str(out_path), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Saved density histogram: {out_path}")
        
        # Print statistics
        print("\nDensity Statistics (non-zero pixels):")
        print(f"  Total pixels: {stats['total_pixels']:,}")
        print(f"  Non-zero pixels: {stats['non_zero_pixels']:,} ({stats['non_zero_pixels']/stats['total_pixels']*100:.1f}%)")
        print(f"  Min: {stats['min']:.1f} points/pixel")
        print(f"  Max: {stats['max']:.1f} points/pixel")
        print(f"  Mean: {stats['mean']:.1f} points/pixel")
        print(f"  Median: {stats['median']:.1f} points/pixel")
        print(f"  Std: {stats['std']:.1f}")
        print(f"  P25: {stats['percentile_25']:.1f}")
        print(f"  P75: {stats['percentile_75']:.1f}")
        print(f"  P95: {stats['percentile_95']:.1f}")
        print(f"  P99: {stats['percentile_99']:.1f}")
        
        # Save statistics to text file
        stats_path = out_path.parent / f"{out_path.stem}_stats.txt"
        with open(stats_path, 'w') as f:
            f.write("Density Statistics (Points per Pixel)\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total pixels: {stats['total_pixels']:,}\n")
            f.write(f"Non-zero pixels: {stats['non_zero_pixels']:,} ({stats['non_zero_pixels']/stats['total_pixels']*100:.1f}%)\n")
            f.write(f"Zero pixels: {stats['total_pixels']-stats['non_zero_pixels']:,} ({(stats['total_pixels']-stats['non_zero_pixels'])/stats['total_pixels']*100:.1f}%)\n\n")
            f.write(f"Min: {stats['min']:.1f} points/pixel\n")
            f.write(f"Max: {stats['max']:.1f} points/pixel\n")
            f.write(f"Mean: {stats['mean']:.1f} points/pixel\n")
            f.write(f"Median: {stats['median']:.1f} points/pixel\n")
            f.write(f"Std Dev: {stats['std']:.1f}\n\n")
            f.write("Percentiles:\n")
            f.write(f"  P25: {stats['percentile_25']:.1f}\n")
            f.write(f"  P75: {stats['percentile_75']:.1f}\n")
            f.write(f"  P95: {stats['percentile_95']:.1f}\n")
            f.write(f"  P99: {stats['percentile_99']:.1f}\n")
        print(f"Saved density statistics: {stats_path}")

    # ---------- Z-axis histogram ----------
    @staticmethod
    def save_z_histogram(las_path: str, out_path: Path, bins: int = 100):
        """Create and save histogram of Z-axis (height) distribution from original point cloud."""
        print(f"\nAnalyzing Z-axis distribution from: {las_path}")
        
        # Load point cloud
        las = laspy.read(las_path)
        z_values = np.array(las.z)  # Convert to numpy array
        
        print(f"  Total points: {len(z_values):,}")
        
        # Calculate statistics
        stats = {
            'count': int(len(z_values)),
            'min': float(z_values.min()),
            'max': float(z_values.max()),
            'range': float(z_values.max() - z_values.min()),
            'mean': float(z_values.mean()),
            'median': float(np.median(z_values)),
            'std': float(z_values.std()),
            'p01': float(np.percentile(z_values, 1)),
            'p05': float(np.percentile(z_values, 5)),
            'p10': float(np.percentile(z_values, 10)),
            'p25': float(np.percentile(z_values, 25)),
            'p75': float(np.percentile(z_values, 75)),
            'p90': float(np.percentile(z_values, 90)),
            'p95': float(np.percentile(z_values, 95)),
            'p99': float(np.percentile(z_values, 99))
        }
        
        # Create figure with three subplots
        fig = plt.figure(figsize=(14, 16))
        gs = fig.add_gridspec(3, 1, hspace=0.3)
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1])
        ax3 = fig.add_subplot(gs[2])
        
        # Top plot: Full range histogram
        counts, bin_edges, patches = ax1.hist(z_values, bins=bins, color='forestgreen', 
                                              edgecolor='black', alpha=0.7)
        ax1.axvline(stats['mean'], color='red', linestyle='--', linewidth=2, 
                   label=f"Mean: {stats['mean']:.2f} m")
        ax1.axvline(stats['median'], color='blue', linestyle='--', linewidth=2, 
                   label=f"Median: {stats['median']:.2f} m")
        ax1.axvline(stats['p05'], color='orange', linestyle=':', linewidth=1.5, 
                   label=f"P05: {stats['p05']:.2f} m")
        ax1.axvline(stats['p95'], color='purple', linestyle=':', linewidth=1.5, 
                   label=f"P95: {stats['p95']:.2f} m")
        ax1.set_xlabel('Elevation (Z) [meters]', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Frequency (Point Count)', fontsize=12, fontweight='bold')
        ax1.set_title('Z-Axis Distribution: Full Range', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10, loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Middle plot: Zoomed to P5-P95 range
        z_p5_p95 = z_values[(z_values >= stats['p05']) & (z_values <= stats['p95'])]
        ax2.hist(z_p5_p95, bins=bins, color='seagreen', edgecolor='black', alpha=0.7)
        ax2.axvline(stats['mean'], color='red', linestyle='--', linewidth=2, 
                   label=f"Mean: {stats['mean']:.2f} m")
        ax2.axvline(stats['median'], color='blue', linestyle='--', linewidth=2, 
                   label=f"Median: {stats['median']:.2f} m")
        ax2.set_xlabel('Elevation (Z) [meters]', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Frequency (Point Count)', fontsize=12, fontweight='bold')
        ax2.set_title('Z-Axis Distribution: P5-P95 Range (Main Distribution)', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10, loc='best')
        ax2.grid(True, alpha=0.3)
        
        # Bottom plot: Cumulative distribution
        sorted_z = np.sort(z_values)
        cumulative = np.arange(1, len(sorted_z) + 1) / len(sorted_z) * 100
        ax3.plot(sorted_z, cumulative, color='darkgreen', linewidth=2)
        ax3.axhline(50, color='blue', linestyle='--', linewidth=1.5, alpha=0.7, label='Median (50%)')
        ax3.axhline(5, color='orange', linestyle=':', linewidth=1.5, alpha=0.7, label='P05 (5%)')
        ax3.axhline(95, color='purple', linestyle=':', linewidth=1.5, alpha=0.7, label='P95 (95%)')
        ax3.axvline(stats['median'], color='blue', linestyle='--', linewidth=1.5, alpha=0.5)
        ax3.axvline(stats['p05'], color='orange', linestyle=':', linewidth=1.5, alpha=0.5)
        ax3.axvline(stats['p95'], color='purple', linestyle=':', linewidth=1.5, alpha=0.5)
        ax3.set_xlabel('Elevation (Z) [meters]', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Cumulative Percentage (%)', fontsize=12, fontweight='bold')
        ax3.set_title('Cumulative Distribution Function (CDF)', fontsize=14, fontweight='bold')
        ax3.legend(fontsize=10, loc='best')
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        out_path = Path(out_path)
        plt.savefig(str(out_path), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Saved Z-axis histogram: {out_path}")
        
        # Print statistics
        print("\nZ-Axis Statistics:")
        print(f"  Total points: {stats['count']:,}")
        print(f"  Min elevation: {stats['min']:.2f} m")
        print(f"  Max elevation: {stats['max']:.2f} m")
        print(f"  Range: {stats['range']:.2f} m")
        print(f"  Mean: {stats['mean']:.2f} m")
        print(f"  Median: {stats['median']:.2f} m")
        print(f"  Std Dev: {stats['std']:.2f} m")
        print(f"\n  Percentiles:")
        print(f"    P01: {stats['p01']:.2f} m")
        print(f"    P05: {stats['p05']:.2f} m")
        print(f"    P10: {stats['p10']:.2f} m")
        print(f"    P25: {stats['p25']:.2f} m")
        print(f"    P50: {stats['median']:.2f} m")
        print(f"    P75: {stats['p75']:.2f} m")
        print(f"    P90: {stats['p90']:.2f} m")
        print(f"    P95: {stats['p95']:.2f} m")
        print(f"    P99: {stats['p99']:.2f} m")
        
        # Save statistics to text file
        stats_path = out_path.parent / f"{out_path.stem}_stats.txt"
        with open(stats_path, 'w') as f:
            f.write("Z-Axis (Elevation) Statistics\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total points: {stats['count']:,}\n\n")
            f.write(f"Min elevation: {stats['min']:.2f} m\n")
            f.write(f"Max elevation: {stats['max']:.2f} m\n")
            f.write(f"Range: {stats['range']:.2f} m\n")
            f.write(f"Mean: {stats['mean']:.2f} m\n")
            f.write(f"Median: {stats['median']:.2f} m\n")
            f.write(f"Std Dev: {stats['std']:.2f} m\n\n")
            f.write("Percentiles:\n")
            f.write(f"  P01: {stats['p01']:.2f} m\n")
            f.write(f"  P05: {stats['p05']:.2f} m\n")
            f.write(f"  P10: {stats['p10']:.2f} m\n")
            f.write(f"  P25: {stats['p25']:.2f} m\n")
            f.write(f"  P50 (Median): {stats['median']:.2f} m\n")
            f.write(f"  P75: {stats['p75']:.2f} m\n")
            f.write(f"  P90: {stats['p90']:.2f} m\n")
            f.write(f"  P95: {stats['p95']:.2f} m\n")
            f.write(f"  P99: {stats['p99']:.2f} m\n")
        print(f"Saved Z-axis statistics: {stats_path}")

    # ---------- HAG multiband RGB ----------
    def save_hag_multiband_rgb(self, grid, meta, out_path: Path, min_density:int=10, blur_sigma:float=0.0):
        ch_names = meta['channel_names']
        low  = np.nan_to_num(grid[:,:,ch_names.index('hag_low_count')], 0.0)
        mid  = np.nan_to_num(grid[:,:,ch_names.index('hag_mid_count')], 0.0)
        high = np.nan_to_num(grid[:,:,ch_names.index('hag_high_count')],0.0)

        den = np.nan_to_num(grid[:,:,0], 0.0)
        low [den < min_density] = 0.0
        mid [den < min_density] = 0.0
        high[den < min_density] = 0.0

        if blur_sigma:
            low  = _apply_optional_blur(low,  blur_sigma)
            mid  = _apply_optional_blur(mid,  blur_sigma)
            high = _apply_optional_blur(high, blur_sigma)

        def norm255(x):
            mn, mx = float(x.min()), float(x.max())
            return np.zeros_like(x, dtype=np.uint8) if mx <= mn else ((x - mn)/(mx-mn)*255).astype(np.uint8)

        rgb = np.zeros((*low.shape, 3), dtype=np.uint8)
        rgb[:,:,0] = norm255(mid)   # R=mid band
        rgb[:,:,1] = norm255(low)   # G=low band
        rgb[:,:,2] = norm255(high)  # B=high band
        out_path = Path(out_path)
        cv2.imwrite(str(out_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        print(f"Saved HAG multiband RGB: {out_path}")


# ----------------------------- CLI -----------------------------
def main():
    ap = argparse.ArgumentParser(
        description='Rasterize point cloud to multi-channel 2D grid (Z/HAG percentiles + HAG band & multiband).'
    )
    ap.add_argument('input_las', help='Input .las file path')
    ap.add_argument('--output_dir', default='./raster_output', help='Output directory')
    ap.add_argument('--image_size', type=int, default=320, help='Target image size (square)')
    ap.add_argument('--pixel_size', type=float, default=0.125, help='Pixel size (m)')
    ap.add_argument('--area_size', type=float, default=40.0, help='Target area size (m, for info)')

    ap.add_argument('--no_normalize', action='store_true', help='Do not normalize channels (except density)')
    ap.add_argument('--min-density', type=int, default=10, help='Mask/zero values where density < this (plots/PNGs)')
    ap.add_argument('--hag-sigma', type=float, default=0.0, help='Gaussian blur sigma (pixels) for HAG-derived maps')

    ap.add_argument('--visualize', action='store_true', help='Create density + (Z P95-P05) span figure')
    ap.add_argument('--plot-z', action='store_true', help='Export pretty plots for all z_p** channels')
    ap.add_argument('--plot-hag', action='store_true', help='Export pretty plots for HAG channels')
    ap.add_argument('--plot-hag-multiband', action='store_true', help='Export low/mid/high HAG band PNGs + RGB composite')

    ap.add_argument('--hag-band-low', type=float, default=0.2, help='HAG band lower bound (m)')
    ap.add_argument('--hag-band-high', type=float, default=1.5, help='HAG band upper bound (m)')

    ap.add_argument('--hag_b1', type=float, default=0.4, help='HAG multiband cutpoint b1 (low→mid) in meters')
    ap.add_argument('--hag_b2', type=float, default=1.4, help='HAG multiband cutpoint b2 (mid→high) in meters')

    ap.add_argument('--save-npy', action='store_true', help='Also save the multi-channel .npy + metadata.json')
    ap.add_argument('--save-metadata', action='store_true', help='Save metadata.json without .npy')

    ap.add_argument('--compare-density-hag-high', action='store_true',
        help='Save comparison figure: density vs hag_high_count (side-by-side + overlay)')
    
    ap.add_argument('--plot-density-histogram', action='store_true',
        help='Create and save histogram of points per pixel (density distribution)')
    
    ap.add_argument('--plot-z-histogram', action='store_true',
        help='Create and save histogram of Z-axis (elevation) distribution')

    args = ap.parse_args()

    # init
    rz = PointCloudRasterizer(image_size=args.image_size, pixel_size=args.pixel_size, area_size=args.area_size)

    # load & rasterize
    pts, _ = rz.load_pointcloud(args.input_las)
    grid, meta = rz.rasterize_multi_channel(pts, normalize=not args.no_normalize)

    # Fill HAG band(s)
    grid = rz.add_hag_band_count(grid, args.hag_band_low, args.hag_band_high)
    grid = rz.add_hag_multiband_counts(grid, args.hag_b1, args.hag_b2)

    # normalize (except density) unless disabled
    if not args.no_normalize:
        print("  Normalizing channels (except density)...")
        for c in range(1, grid.shape[2]):
            ch = grid[:,:,c]
            mn, mx = float(ch.min()), float(ch.max())
            if mx > mn:
                grid[:,:,c] = (ch - mn) / (mx - mn)
        meta['normalized'] = True
        print("  Note: density channel kept as raw count")
    else:
        meta['normalized'] = False

    # resize after all channels are ready
    grid = rz.resize_to_target(grid, args.image_size)
    meta['resized_to'] = int(args.image_size)

    # outputs
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    base = Path(args.input_las).stem
    out_base = out_dir / f"{base}_raster"

    # (optional) comparison figures (needs out_dir/base defined)
    if args.compare_density_hag_high:
        save_density_vs_hag_high(
            grid, meta, out_dir / f"{base}",
            min_density=args.min_density, overlay_alpha=0.65
        )

    # channel PNGs (with optional density mask & blur on HAG*)
    rz.save_channels_png(
        grid, str(out_dir), f"{base}_raster", meta['channel_names'],
        min_density=args.min_density, blur_sigma=args.hag_sigma
    )

    # RGB composite (density,z_mean,hag_mean)
    rz.create_rgb_composite(grid, channels=(0,4,6), out_path=out_dir / f"{base}_rgb.png")

    # save npy/metadata
    if args.save_npy:
        np.save(str(out_base) + ".npy", np.nan_to_num(grid, nan=0.0, posinf=0.0, neginf=0.0))
        with open(str(out_base) + "_metadata.json", 'w') as f:
            json.dump(meta, f, indent=2)
        print(f"Saved multi-channel array: {str(out_base)}.npy")
        print(f"Saved metadata: {str(out_base)}_metadata.json")
    elif args.save_metadata:
        with open(str(out_base) + "_metadata.json", 'w') as f:
            json.dump(meta, f, indent=2)
        print(f"Saved metadata only: {str(out_base)}_metadata.json")

    # quick visualize: density + Z (P95-P05) span
    if args.visualize:
        density = np.nan_to_num(grid[:,:,0], nan=0.0)
        ch_names = meta['channel_names']
        p95 = grid[:,:,ch_names.index('z_p95')]
        p05 = grid[:,:,ch_names.index('z_p05')]
        span = np.nan_to_num(p95, nan=0.0) - np.nan_to_num(p05, nan=0.0)
        span[density < args.min_density] = 0.0

        fig, axes = plt.subplots(1, 2, figsize=(16,7))
        im0 = axes[0].imshow(density, cmap='viridis')
        axes[0].set_title('Density (RAW count)', fontsize=14, fontweight='bold'); axes[0].axis('off')
        c0 = plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04); c0.set_label('Points', rotation=270, labelpad=18)

        im1 = axes[1].imshow(span, cmap='viridis')
        axes[1].set_title(f'Z span (P95 - P05), density < {args.min_density} → 0', fontsize=14, fontweight='bold'); axes[1].axis('off')
        c1 = plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)
        unit = '' if meta.get('normalized', True) else ' (m)'; c1.set_label('Height'+unit, rotation=270, labelpad=18)

        plt.tight_layout()
        vis_path = out_dir / f"{base}_percentile_span.png"
        plt.savefig(str(vis_path), dpi=150, bbox_inches='tight'); plt.close()
        print(f"Saved visualization: {vis_path}")

    # pretty: all z_p**
    if args.plot_z:
        for name in [n for n in meta['channel_names'] if n.startswith('z_p')]:
            out_path = out_dir / f"{base}_{name}_pretty.png"
            PointCloudRasterizer._save_single_plot(
                grid, meta, name, out_path, min_density=args.min_density, label='Value', blur_sigma=0.0
            )

    # pretty: HAG family
    if args.plot_hag:
        for name in ['hag_mean','hag_p05','hag_p10','hag_p25','hag_band_count','hag_low_count','hag_mid_count','hag_high_count']:
            out_path = out_dir / f"{base}_{name}_pretty.png"
            label = 'Count' if ('count' in name) else 'Value'
            PointCloudRasterizer._save_single_plot(
                grid, meta, name, out_path, min_density=args.min_density, label=label, blur_sigma=args.hag_sigma
            )

    # multiband RGB
    if args.plot_hag_multiband:
        rz.save_hag_multiband_rgb(
            grid, meta, out_dir / f"{base}_hag_multiband_rgb.png",
            min_density=args.min_density, blur_sigma=args.hag_sigma
        )

    # density histogram
    if args.plot_density_histogram:
        PointCloudRasterizer.save_density_histogram(
            grid, meta, out_dir / f"{base}_density_histogram.png", bins=50
        )

    # z-axis histogram
    if args.plot_z_histogram:
        PointCloudRasterizer.save_z_histogram(
            args.input_las, out_dir / f"{base}_z_histogram.png", bins=100
        )

    print("\n✓ Rasterization complete!")
    print(f"  Output directory: {out_dir}")
    print(f"  Channels PNGs + RGB saved. {'Also saved .npy.' if args.save_npy else '(no .npy saved)'}")


if __name__ == "__main__":
    main()
