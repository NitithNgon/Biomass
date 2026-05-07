# Batch Process Plots - Performance Monitoring Guide

## System Specification
Your machine has the following specifications for comparison:
```
CPU Cores (Physical): 16
CPU Cores (Logical): 32  
Total Memory: 31.18 GB
Available Memory: 22.71 GB (at test time)
Python Version: 3.12.12
```

## Performance Test Scripts Created

### 1. Simple Benchmark Shell Script
**File:** `notebooks_density/dataset_creation/simple_benchmark.sh`

This script runs batch_process_plots.py with different thread configurations:
- Test 1: OMP_NUM_THREADS=1 (single-threaded)
- Test 2: OMP_NUM_THREADS=2 (dual-threaded)
- Test 3: OMP_NUM_THREADS=4 (quad-threaded)

**How to run:**
```bash
cd /home/pun/Desktop
chmod +x notebooks_density/dataset_creation/simple_benchmark.sh
notebooks_density/dataset_creation/simple_benchmark.sh
```

**Output files created:**
- `test1_output.txt` - Single-thread results with /usr/bin/time statistics
- `test2_output.txt` - Dual-thread results with /usr/bin/time statistics
- `test3_output.txt` - Quad-thread results with /usr/bin/time statistics

### 2. Python Monitoring Script
**File:** `notebooks_density/dataset_creation/run_with_monitoring.py`

This script uses /usr/bin/time for robust resource monitoring.

**How to run single test:**
```bash
cd /home/pun/Desktop
python3 notebooks_density/dataset_creation/run_with_monitoring.py --single-run
```

**How to run multiple thread tests:**
```bash
python3 notebooks_density/dataset_creation/run_with_monitoring.py --threads 1 2 4 --output results.json
```

## What to Look For in /usr/bin/time Output

```
	Command being timed: "python3 batch_process_plots.py --buffer 1.0 --grid-size 0.5"
	User time (seconds): XX.XX        ← CPU time in user space
	System time (seconds): XX.XX      ← CPU time in kernel space
	Elapsed time (seconds): XX.XX     ← Total wall-clock time
	Maximum resident set size (kbytes): XXXXX  ← Peak memory usage
	Average resident set size (kbytes): XXXXX  ← Average memory during run
	Percent of CPU this job got: XX%  ← CPU utilization percentage
	Major page faults: X              ← Disk cache misses
	Minor page faults: XXXXX          ← Memory page reclamations
	Voluntary context switches: XXXXX ← Thread/process switches
	Involuntary context switches: XXXX ← Forced context switches (CPU overloaded)
```

## Key Performance Metrics to Compare

### 1. **Elapsed Time (seconds)**
- Best metric for actual wall-clock time
- Lower is better
- Compare across different thread counts to find optimal configuration

### 2. **User + System Time**
- Combined CPU time
- Should be roughly constant regardless of thread count (same work, different distribution)

### 3. **Maximum resident set size (Memory)**
- Peak RAM usage during execution
- Important for determining server memory requirements
- Consider both maximum and sustained usage

### 4. **Percent of CPU this job got**
- Shows CPU utilization efficiency
- 100% = fully utilizing all available CPU
- Important for multi-threaded vs single-threaded comparison

### 5. **Context Switches**
- Involuntary context switches increase when CPU is oversubscribed
- Higher counts indicate CPU contention

## Performance Data Collection

### Running the benchmark safely:
The script processes 12 plots with 3 processing steps each (conversion, filtering, rotation).
Expected total time: 30-120 seconds per test depending on your system and thread count.

### Recommended process:
1. Run all tests sequentially using the bash script
2. Each test redirects output to a separate file
3. Use /usr/bin/time -v for verbose statistics
4. Compare the three test outputs to identify optimal threading

## Interpreting Results

### Example comparison:
```
1 Thread:  Elapsed: 120.5s | Max Memory: 2.5GB | CPU%: 98%
2 Threads: Elapsed: 78.3s  | Max Memory: 3.1GB | CPU%: 156% (on 16 cores)
4 Threads: Elapsed: 65.2s  | Max Memory: 3.8GB | CPU%: 198% (on 16 cores)
```

In this case:
- 4 threads is fastest (45% time reduction)
- Memory usage increases with threads (expected)
- CPU utilization improves with more threads

### Server Sizing Considerations:
Based on your measurements:
1. **Minimum CPU cores needed**: Match thread count where you see best performance
2. **Memory required**: Use peak memory observed + 20% buffer
3. **Sustained memory**: Average/sustained memory is more important for long-running servers
4. **CPU architecture**: Consider if workload benefits from multi-threading

## Example Server Spec Recommendation Template

```
Based on single plot batch processing:
- CPU Cores: [Optimal threads from testing]
- CPU Type: [Your CPU model or equivalent]
- RAM: [Peak memory * 1.2] GB (with headroom)
- Storage: [Enough for processed files]
- Network: [Based on data transfer needs]
```

## Notes

- The data directory contains 12 plot directories (ska-ls-h201 through ska-ls-l301)
- Each plot requires: PCD → LAS conversion → Filtering → Rotation
- Output files are generated in `notebooks_density/processed/`
- Intermediate files are cleaned up automatically to save disk space

## Files Created for Monitoring

1. `batch_process_with_monitoring.py` - Advanced Python monitoring (may have performance issues)
2. `run_with_monitoring.py` - Simplified Python monitoring wrapper
3. `simple_benchmark.sh` - Bash script using /usr/bin/time (recommended)

**Recommendation: Use the bash script (simple_benchmark.sh) for the most reliable results.**
