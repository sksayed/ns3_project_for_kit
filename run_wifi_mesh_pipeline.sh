#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$ROOT_DIR/wifi_mesh_backhaul_outputs"
NS3_CMD="$ROOT_DIR/ns3"
ANALYZER_DIR="$ROOT_DIR/wifi_mesh_analyzer"
SIM_NAME="tcp_mesh_backhaul_mode"

echo "=========================================="
echo "WiFi Mesh Backhaul Simulation Pipeline"
echo "=========================================="
echo "Simulation: $SIM_NAME (9 APs Optimized Mesh with TCP+UDP)"
echo "Output Directory: $OUT_DIR"
echo ""

echo "[1/3] Running simulation: $SIM_NAME"
"$NS3_CMD" run "$SIM_NAME" --no-build || {
    echo "Building and running simulation..."
    "$NS3_CMD" run "$SIM_NAME"
}

echo ""
echo "[2/3] Running enhanced visualizer (professional plots + HTML)"
echo "   • Network topology, throughput heatmap, hop count analysis"
echo "   • Transmission analysis, performance dashboard, HTML report"
python3 "$ANALYZER_DIR/enhanced_visualizer.py" || echo "⚠️ Enhanced visualizer failed"

echo ""
echo "[3/3] Creating network animation (optional)"
python3 "$ANALYZER_DIR/wifi_mesh_backhaul_animation.py" || echo "⚠️ Animation generator failed (optional)"

# Note: Old topology analyzer archived as wifi_mesh_backhaul_analyzer_OLD_4AP.py.bak
# It's specific to the old 4-AP topology and is no longer used

echo ""
echo "=========================================="
echo "Pipeline Complete!"
echo "=========================================="
echo ""
echo "📁 Output Directory: $OUT_DIR"
echo ""

# Count generated files
XML_COUNT=$(ls "$OUT_DIR"/*.xml 2>/dev/null | wc -l)
PCAP_COUNT=$(ls "$OUT_DIR"/*.pcap 2>/dev/null | wc -l)
PNG_COUNT=$(ls "$OUT_DIR"/*.png 2>/dev/null | wc -l)
HTML_COUNT=$(ls "$OUT_DIR"/*.html 2>/dev/null | wc -l)
GIF_COUNT=$(ls "$OUT_DIR"/*.gif 2>/dev/null | wc -l)

echo "📊 Generated Files:"
echo "   • FlowMonitor XML: $XML_COUNT files"
echo "   • PCAP captures: $PCAP_COUNT files"
echo "   • PNG visualizations: $PNG_COUNT files"
echo "   • HTML reports: $HTML_COUNT files"
echo "   • Animations: $GIF_COUNT files"
echo ""

echo "🎯 Key Analysis Files:"
if [ -f "$OUT_DIR/analysis_report.html" ]; then
    echo "   ✅ analysis_report.html (Main report - open this!)"
fi
if [ -f "$OUT_DIR/performance_dashboard.png" ]; then
    echo "   ✅ performance_dashboard.png (Comprehensive dashboard)"
fi
if [ -f "$OUT_DIR/network_topology.png" ]; then
    echo "   ✅ network_topology.png (Auto-detected topology)"
fi
if [ -f "$OUT_DIR/hop_count_analysis.png" ]; then
    echo "   ✅ hop_count_analysis.png (Multi-hop analysis)"
fi
if [ -f "$OUT_DIR/throughput_heatmap.png" ]; then
    echo "   ✅ throughput_heatmap.png (Time-based heatmap)"
fi
if [ -f "$OUT_DIR/transmission_analysis.png" ]; then
    echo "   ✅ transmission_analysis.png (Efficiency analysis)"
fi
if [ -f "$OUT_DIR/wifi_mesh_backhaul_animation.gif" ]; then
    echo "   ✅ wifi_mesh_backhaul_animation.gif (Network animation)"
fi

echo ""
echo "🌐 Open Main Report:"
echo "   firefox $OUT_DIR/analysis_report.html"
echo ""
echo "✅ All analysis complete!"