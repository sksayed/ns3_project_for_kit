#!/bin/bash

# LTE Animation Runner
# This script runs the LTE animation visualization

echo "LTE Network Animation"
echo "====================="

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
mkdir -p Lte_outputs

# Run the animation
echo "Running LTE animation..."
python3 lte_animation.py

echo "Animation complete! Check the Lte_outputs directory for:"
echo "  - lte_animation.gif (animated GIF)"
echo "  - lte_animation.mp4 (MP4 video, if ffmpeg available)"
echo "  - lte_static_layout.png (static layout)"
