#!/bin/bash

ROOT_FOLDER="$1"
ROTATE_SCRIPT="/Users/songkarn/Desktop/handheld-lidar-slam-toolbox/scripts/python/tools/rotate_pointcloud.py"
CONVERT_SCRIPT="/Users/songkarn/Desktop/handheld-lidar-slam-toolbox/scripts/python/tools/convert_pcd_to_las.py"

for folder in "$ROOT_FOLDER"/*; do
    if [ -d "$folder" ]; then
        input_file="$folder/filtered.las"
        output_file="$folder/Test_PCA.las"

        if [ ! -f "$input_file" ]; then
            pcd_file="$folder/filtered.las"
            if [ -f "$pcd_file" ]; then
                echo ">>> Converting $pcd_file to $input_file"
                python3 "$CONVERT_SCRIPT" -i "$pcd_file" -o "$input_file"
            else
                echo ">>> Skipping $folder: neither scans.las nor scans.pcd found"
                continue
            fi
        fi

        if [ -f "$input_file" ]; then
            echo ">>> Rotating $input_file"
            python3 "$ROTATE_SCRIPT" "$input_file" "$output_file"
        else
            echo ">>> Error: $input_file not found after conversion"
        fi
    fi
done

# sudo chmod +x rotate_all_filtered.sh
# ./rotate_all_filtered.sh "/Users/songkarn/Downloads/LiDAR Forestsense"


# chmod +x rotate_all_filtered.sh
# ./rotate_all_filtered.sh "/Users/songkarn/Downloads/LiDAR Forestsense"
