#!/usr/bin/env python3
"""
Performance monitoring wrapper for batch_process_plots.py
Measures execution time, CPU usage, and memory consumption
"""

import os
import sys
import subprocess
import argparse
import time
import psutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class PerformanceMonitor:
    def __init__(self, process_pid: int, interval: float = 0.5):
        self.pid = process_pid
        self.interval = interval
        self.metrics = {
            'cpu_percent': [],
            'memory_mb': [],
            'memory_percent': [],
            'num_threads': []
        }
        self.process = psutil.Process(process_pid)
        self.start_time = time.time()
        
    def monitor(self):
        """Monitor process metrics"""
        try:
            while self.process.is_running():
                try:
                    cpu = self.process.cpu_percent(interval=0.1)
                    mem_info = self.process.memory_info()
                    memory_mb = mem_info.rss / (1024 * 1024)
                    memory_percent = self.process.memory_percent()
                    num_threads = self.process.num_threads()
                    
                    self.metrics['cpu_percent'].append(cpu)
                    self.metrics['memory_mb'].append(memory_mb)
                    self.metrics['memory_percent'].append(memory_percent)
                    self.metrics['num_threads'].append(num_threads)
                    
                except (psutil.ProcessLookupError, psutil.AccessDenied):
                    break
                    
                time.sleep(self.interval)
        except Exception as e:
            print(f"Monitoring error: {e}")
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.metrics['cpu_percent']:
            return {}
        
        return {
            'avg_cpu_percent': sum(self.metrics['cpu_percent']) / len(self.metrics['cpu_percent']),
            'max_cpu_percent': max(self.metrics['cpu_percent']),
            'avg_memory_mb': sum(self.metrics['memory_mb']) / len(self.metrics['memory_mb']),
            'max_memory_mb': max(self.metrics['memory_mb']),
            'avg_memory_percent': sum(self.metrics['memory_percent']) / len(self.metrics['memory_percent']),
            'max_memory_percent': max(self.metrics['memory_percent']),
            'avg_threads': sum(self.metrics['num_threads']) / len(self.metrics['num_threads']),
            'max_threads': max(self.metrics['num_threads'])
        }


def get_system_info() -> Dict:
    """Get system information"""
    return {
        'cpu_count': psutil.cpu_count(logical=False),
        'cpu_count_logical': psutil.cpu_count(logical=True),
        'total_memory_gb': psutil.virtual_memory().total / (1024**3),
        'available_memory_gb': psutil.virtual_memory().available / (1024**3),
        'python_version': sys.version.split()[0]
    }


def run_with_monitoring(cmd: List[str], num_threads: int = None) -> Tuple[Dict, int]:
    """Run command with monitoring"""
    
    print(f"\n{'='*70}")
    if num_threads:
        print(f"Running with {num_threads} threads")
    else:
        print("Running script")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    # Start process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Monitor in a simple way (just collect before and after)
    monitor = PerformanceMonitor(process.pid)
    
    # Output process stdout in real-time
    for line in process.stdout:
        print(line, end='')
        monitor.monitor()
    
    # Wait for process to complete
    return_code = process.wait()
    elapsed_time = time.time() - start_time
    
    # Get final metrics
    monitor_summary = monitor.get_summary()
    
    results = {
        'return_code': return_code,
        'elapsed_time_seconds': elapsed_time,
        'performance_metrics': monitor_summary,
        'success': return_code == 0
    }
    
    return results, return_code


def main():
    parser = argparse.ArgumentParser(
        description='Run batch_process_plots.py with performance monitoring'
    )
    parser.add_argument(
        '--buffer', '-b',
        type=float,
        default=1.0,
        help='Buffer distance in meters (default: 1.0)'
    )
    parser.add_argument(
        '--grid-size', '-g',
        type=float,
        default=0.5,
        help='Grid size in meters (default: 0.5)'
    )
    parser.add_argument(
        '--threads',
        type=int,
        nargs='+',
        default=[1, 2, 4],
        help='Thread counts to test (default: 1 2 4)'
    )
    parser.add_argument(
        '--single-run',
        action='store_true',
        help='Run only once without thread variations'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='batch_process_results.json',
        help='Output results file (JSON format)'
    )
    
    args = parser.parse_args()
    
    # Get script directory
    script_dir = Path(__file__).parent
    batch_script = script_dir / "batch_process_plots.py"
    
    if not batch_script.exists():
        print(f"❌ Script not found: {batch_script}")
        return 1
    
    # Collect results
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'system_info': get_system_info(),
        'runs': []
    }
    
    print(f"\n{'='*70}")
    print("BATCH PROCESS PLOTS - PERFORMANCE MONITORING")
    print(f"{'='*70}\n")
    
    # Print system info
    print("System Information:")
    print(f"  CPU Cores (Physical): {all_results['system_info']['cpu_count']}")
    print(f"  CPU Cores (Logical): {all_results['system_info']['cpu_count_logical']}")
    print(f"  Total Memory: {all_results['system_info']['total_memory_gb']:.2f} GB")
    print(f"  Available Memory: {all_results['system_info']['available_memory_gb']:.2f} GB")
    print(f"  Python Version: {all_results['system_info']['python_version']}")
    
    # Determine thread counts to test
    if args.single_run:
        thread_counts = [None]  # Just run once
    else:
        thread_counts = args.threads if args.threads else [None]
    
    # Run with different thread counts
    for threads in thread_counts:
        cmd = [sys.executable, str(batch_script)]
        cmd.extend(['--buffer', str(args.buffer)])
        cmd.extend(['--grid-size', str(args.grid_size)])
        
        # Set environment variable for thread count if specified
        env = os.environ.copy()
        if threads is not None:
            env['OMP_NUM_THREADS'] = str(threads)
            env['NUMEXPR_NUM_THREADS'] = str(threads)
            env['MKL_NUM_THREADS'] = str(threads)
        
        results, return_code = run_with_monitoring(cmd, threads)
        
        run_record = {
            'thread_count': threads,
            'buffer_distance': args.buffer,
            'grid_size': args.grid_size,
            **results
        }
        all_results['runs'].append(run_record)
        
        if return_code != 0:
            print(f"\n⚠️  Script exited with code {return_code}")
        else:
            print(f"\n✅ Script completed successfully")
    
    # Print summary
    print(f"\n{'='*70}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*70}\n")
    
    for i, run in enumerate(all_results['runs'], 1):
        threads = run['thread_count'] if run['thread_count'] else "Default"
        elapsed = run['elapsed_time_seconds']
        
        print(f"Run {i} (Threads: {threads}):")
        print(f"  Elapsed Time: {elapsed:.2f} seconds")
        
        if run['performance_metrics']:
            metrics = run['performance_metrics']
            print(f"  Avg CPU Usage: {metrics.get('avg_cpu_percent', 0):.1f}%")
            print(f"  Max CPU Usage: {metrics.get('max_cpu_percent', 0):.1f}%")
            print(f"  Avg Memory: {metrics.get('avg_memory_mb', 0):.1f} MB")
            print(f"  Max Memory: {metrics.get('max_memory_mb', 0):.1f} MB")
            print(f"  Max Memory %: {metrics.get('max_memory_percent', 0):.2f}%")
            print(f"  Avg Threads: {metrics.get('avg_threads', 0):.1f}")
            print(f"  Max Threads: {metrics.get('max_threads', 0)}")
        print()
    
    # Save results to JSON
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"{'='*70}")
    print(f"✅ Results saved to: {output_path}")
    print(f"{'='*70}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
