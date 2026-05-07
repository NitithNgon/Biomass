#!/usr/bin/env python3
"""
Simple performance monitoring wrapper for batch_process_plots.py
Uses /usr/bin/time and subprocess for robust monitoring
"""

import os
import sys
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
import psutil

def get_system_info():
    """Get system information"""
    return {
        'cpu_count': psutil.cpu_count(logical=False),
        'cpu_count_logical': psutil.cpu_count(logical=True),
        'total_memory_gb': psutil.virtual_memory().total / (1024**3),
        'available_memory_gb': psutil.virtual_memory().available / (1024**3),
        'python_version': sys.version.split()[0]
    }

def run_benchmark(buffer_dist=1.0, grid_size=0.5, num_threads=None):
    """Run batch processing with timing"""
    
    script_dir = Path(__file__).parent
    batch_script = script_dir / "batch_process_plots.py"
    
    cmd = [
        sys.executable,
        str(batch_script),
        '--buffer', str(buffer_dist),
        '--grid-size', str(grid_size)
    ]
    
    env = os.environ.copy()
    if num_threads:
        env['OMP_NUM_THREADS'] = str(num_threads)
        env['NUMEXPR_NUM_THREADS'] = str(num_threads)
        env['MKL_NUM_THREADS'] = str(num_threads)
    
    print(f"\n{'='*70}")
    if num_threads:
        print(f"Running with {num_threads} threads")
    else:
        print("Running batch_process_plots.py")
    print(f"{'='*70}\n")
    
    # Run with /usr/bin/time if available, otherwise just run
    try:
        time_cmd = ['/usr/bin/time', '-v'] + cmd
        result = subprocess.run(time_cmd, env=env, capture_output=True, text=True)
        output = result.stdout + result.stderr
    except FileNotFoundError:
        # Fallback if /usr/bin/time is not available
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        output = result.stdout + result.stderr
    
    # Print output
    print(output)
    
    return {
        'return_code': result.returncode,
        'output': output,
        'success': result.returncode == 0
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Run batch_process_plots with monitoring')
    parser.add_argument('--buffer', '-b', type=float, default=1.0, help='Buffer distance')
    parser.add_argument('--grid-size', '-g', type=float, default=0.5, help='Grid size')
    parser.add_argument('--threads', type=int, nargs='+', default=[1, 2, 4], help='Thread counts')
    parser.add_argument('--single-run', action='store_true', help='Run once only')
    parser.add_argument('--output', '-o', default='batch_results.json', help='Output file')
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print("BATCH PROCESS PLOTS - PERFORMANCE MONITORING")
    print(f"{'='*70}\n")
    
    sys_info = get_system_info()
    print("System Information:")
    print(f"  CPU Cores (Physical): {sys_info['cpu_count']}")
    print(f"  CPU Cores (Logical): {sys_info['cpu_count_logical']}")
    print(f"  Total Memory: {sys_info['total_memory_gb']:.2f} GB")
    print(f"  Available Memory: {sys_info['available_memory_gb']:.2f} GB")
    print(f"  Python Version: {sys_info['python_version']}")
    print()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'system_info': sys_info,
        'runs': []
    }
    
    thread_counts = [None] if args.single_run else args.threads
    
    for threads in thread_counts:
        result = run_benchmark(args.buffer, args.grid_size, threads)
        results['runs'].append({
            'thread_count': threads,
            'buffer_distance': args.buffer,
            'grid_size': args.grid_size,
            **result
        })
    
    # Save results
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"✅ Results saved to: {output_path}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
