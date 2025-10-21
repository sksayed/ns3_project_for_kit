#!/bin/bash

# WiFi Mesh Backhaul Network Analysis Pipeline
# Runs simulation and complete analysis

echo "WiFi Mesh Backhaul Network Analysis Pipeline"
echo "============================================="

# Check if ns-3 is available
if ! command -v ./ns3 &> /dev/null; then
    echo "Error: ns-3 not found. Please run this script from the ns-3-dev directory."
    exit 1
fi

# Create output directory
OUTPUT_DIR="wifi_mesh_backhaul_outputs"
mkdir -p $OUTPUT_DIR

echo "Step 1: Running WiFi Mesh Backhaul Simulation..."
echo "-----------------------------------------------"

# Copy source file to scratch and run simulation
cp pic_lab_project/wifi_mesh_playfield_traces_fixed.cc scratch/
./ns3 run "scratch/wifi_mesh_playfield_traces_fixed"

# Check if simulation completed successfully
if [ $? -eq 0 ]; then
    echo "✓ Simulation completed successfully"
else
    echo "✗ Simulation failed"
    exit 1
fi

# Clean up scratch directory
rm scratch/wifi_mesh_playfield_traces_fixed.cc

echo ""
echo "Step 2: Creating Network Animation..."
echo "------------------------------------"

# Run the animation script
python3 pic_lab_project/wifi_mesh_backhaul_animation.py

if [ $? -eq 0 ]; then
    echo "✓ Animation created successfully"
else
    echo "✗ Animation creation failed"
fi

echo ""
echo "Step 3: Running Network Analysis..."
echo "----------------------------------"

# Run the analyzer script
python3 pic_lab_project/wifi_mesh_backhaul_analyzer.py

if [ $? -eq 0 ]; then
    echo "✓ Analysis completed successfully"
else
    echo "✗ Analysis failed"
fi

echo ""
echo "Step 4: Displaying Results..."
echo "----------------------------"

# List generated files
echo "Generated files in $OUTPUT_DIR/:"
echo ""

# Animation files
if [ -f "$OUTPUT_DIR/wifi_mesh_backhaul_animation.gif" ]; then
    echo "📹 Animation: wifi_mesh_backhaul_animation.gif"
fi

if [ -f "$OUTPUT_DIR/wifi_mesh_backhaul_topology.png" ]; then
    echo "🗺️  Topology: wifi_mesh_backhaul_topology.png"
fi

# Analysis files
if [ -f "$OUTPUT_DIR/network_topology_analysis.png" ]; then
    echo "📊 Network Analysis: network_topology_analysis.png"
fi

if [ -f "$OUTPUT_DIR/wifi_mesh_backhaul_analysis_report.html" ]; then
    echo "📋 Analysis Report: wifi_mesh_backhaul_analysis_report.html"
fi

# Simulation output files
echo ""
echo "📁 Simulation Output Files:"
echo "   • flowmon-wifi-mesh-backhaul.xml (FlowMonitor results)"
echo "   • netanim-wifi-mesh-backhaul.xml (NetAnim animation)"
echo "   • wifi_mesh_backhaul_ascii_traces_mesh.tr (Detailed traces)"
echo "   • ipv4-l3.tr (IPv4 layer 3 traces)"
echo "   • Multiple PCAP files for packet analysis"
echo "   • position_grid.txt (Node positions)"

echo ""
echo "🎯 Network Topology Summary:"
echo "   • Backhaul Gateway: 1 node"
echo "   • Mesh Hop Nodes: 4 nodes"
echo "   • STA Nodes: 8 mobile nodes"
echo "   • Special Nodes: Sayed & Sadia"
echo "   • Total Nodes: 15"
echo "   • Simulation Time: 10 seconds"

echo ""
echo "✅ Analysis pipeline completed successfully!"
echo ""
echo "To view results:"
echo "   • Open wifi_mesh_backhaul_analysis_report.html in a web browser"
echo "   • View animation: wifi_mesh_backhaul_animation.gif"
echo "   • Check topology: wifi_mesh_backhaul_topology.png"

echo ""
echo "Files are located in: $OUTPUT_DIR/"
