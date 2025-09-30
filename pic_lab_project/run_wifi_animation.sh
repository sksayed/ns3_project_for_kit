#!/bin/bash

# WiFi Mesh Animation Runner
# This script runs the WiFi mesh animation visualization

echo "WiFi Mesh Network Animation"
echo "=========================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# Check if required packages are available
python3 -c "import matplotlib, numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required Python packages..."
    pip3 install matplotlib numpy pillow
fi

# Create output directory
mkdir -p wifi_mesh_outputs

# Run the animation
echo "Running WiFi mesh animation..."
python3 wifi_mesh_animation.py

echo "Animation complete! Check the wifi_mesh_outputs directory for:"
echo "  - wifi_mesh_animation.gif (animated GIF)"
echo "  - wifi_mesh_animation.mp4 (MP4 video, if ffmpeg available)"
echo "  - wifi_mesh_static_layout.png (static layout)"
