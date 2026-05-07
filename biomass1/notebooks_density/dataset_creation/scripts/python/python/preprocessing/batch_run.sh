#!/bin/bash

INPUT_ROOT="$1"
PY_SCRIPT="/Users/songkarn/Desktop/handheld-lidar-slam-toolbox/scripts/python/preprocessing/filter_pointcloud_by_odom.py"

for folder in "$INPUT_ROOT"/*; do
    if [ -d "$folder" ]; then
        name=$(basename "$folder")
        echo "📁 Processing folder: $name"
        echo "📄 Files in $name:"
        ls "$folder"

        # Detect LAS or fallback to PCD
        las_input=$(find "$folder" -maxdepth 1 -iname "*.las" ! -name "filtered.las" | head -n 1)
        pcd_path="$folder/scans.pcd"  # original PCD assumed here
        odom_path=$(find "$folder" -iname "odom*.txt" | head -n 1)

        if [ -f "$odom_path" ] && { [ -f "$las_input" ] || [ -f "$pcd_path" ]; }; then
            output_las="$folder/filtered.las"
            odom_copy="$folder/Odom.txt"

            if [ -f "$las_input" ]; then
                echo "✅ [$name] Found existing LAS: $(basename "$las_input")"
                temp_las="$las_input"
            else
                echo ">>> [$name] Converting PCD to LAS..."
                temp_las="$folder/$name.las"
                python3 -c "
import open3d as o3d
import laspy
import numpy as np
pcd = o3d.io.read_point_cloud('$pcd_path')
points = np.asarray(pcd.points)
las = laspy.create(point_format=3)
las.x, las.y, las.z = points[:,0], points[:,1], points[:,2]
las.write('$temp_las')
"
            fi

            echo ">>> [$name] Filtering with normal plane..."
            python3 "$PY_SCRIPT" "$temp_las" "$odom_path" -o "$output_las" -p

            echo ">>> [$name] Copying odometry to Odom.txt"
            cp "$odom_path" "$odom_copy"

            if [ "$temp_las" = "$folder/$name.las" ]; then
                echo "🗑️ Removing temporary LAS: $temp_las"
                rm "$temp_las"
            fi
        else
            echo "⚠️ Skipping $name: missing LAS/PCD or odometry"
        fi

        echo "--------------------------------------"
    fi
done

# วิธีใช้งาน:
# chmod +x batch_run.sh
# ./batch_run.sh "/Users/songkarn/Downloads/LiDAR Forestsense"
