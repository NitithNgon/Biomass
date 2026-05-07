#!/bin/bash
# Simple performance test script

cd /home/pun/Desktop/notebooks_density/dataset_creation

echo "========================================================================"
echo "BATCH PROCESS PLOTS - SIMPLE PERFORMANCE TEST"
echo "========================================================================"
echo ""

# System info
echo "System Information:"
echo "  CPU Cores (Physical): $(nproc --all)"
echo "  Total Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "  Available Memory: $(free -h | grep Mem | awk '{print $7}')"
echo ""

# Test 1: Default (1 thread)
echo "========================================================================"
echo "Test 1: Single thread (OMP_NUM_THREADS=1)"
echo "========================================================================"
export OMP_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export MKL_NUM_THREADS=1

echo "Starting batch processing..."
/usr/bin/time -v python3 batch_process_plots.py --buffer 1.0 --grid-size 0.5 > test1_output.txt 2>&1
echo "Test 1 completed. Output saved to test1_output.txt"
echo ""

# Test 2: 2 threads
echo "========================================================================"
echo "Test 2: Two threads (OMP_NUM_THREADS=2)"
echo "========================================================================"
export OMP_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export MKL_NUM_THREADS=2

echo "Starting batch processing..."
/usr/bin/time -v python3 batch_process_plots.py --buffer 1.0 --grid-size 0.5 > test2_output.txt 2>&1
echo "Test 2 completed. Output saved to test2_output.txt"
echo ""

# Test 3: 4 threads
echo "========================================================================"
echo "Test 3: Four threads (OMP_NUM_THREADS=4)"
echo "========================================================================"
export OMP_NUM_THREADS=4
export NUMEXPR_NUM_THREADS=4
export MKL_NUM_THREADS=4

echo "Starting batch processing..."
/usr/bin/time -v python3 batch_process_plots.py --buffer 1.0 --grid-size 0.5 > test3_output.txt 2>&1
echo "Test 3 completed. Output saved to test3_output.txt"
echo ""

echo "========================================================================"
echo "All tests completed!"
echo "========================================================================"
echo ""
echo "Performance Summary:"
echo "Test 1 (1 thread): $(tail -1 test1_output.txt | grep -oP 'Elapsed.*' || echo 'See test1_output.txt')"
echo "Test 2 (2 threads): $(tail -1 test2_output.txt | grep -oP 'Elapsed.*' || echo 'See test2_output.txt')"
echo "Test 3 (4 threads): $(tail -1 test3_output.txt | grep -oP 'Elapsed.*' || echo 'See test3_output.txt')"
