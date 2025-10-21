#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$ROOT_DIR/5g_outputs"
NS3_CMD="$ROOT_DIR/ns3"
PROJECT_DIR="$ROOT_DIR/pic_lab_project"
ANALYZER_DIR="$ROOT_DIR/5g_analyzer"
SCRATCH_DIR="$ROOT_DIR/scratch"
SIM_NAME="5g_playfield_traces"

echo "=========================================="
echo "5G Network Simulation and Analysis Pipeline"
echo "=========================================="

echo "[1/5] Running 5G simulation: $SIM_NAME"
# Copy file to scratch temporarily for ns-3 launcher
cp "$PROJECT_DIR/$SIM_NAME.cc" "$SCRATCH_DIR/$SIM_NAME.cc"
"$NS3_CMD" run "scratch/$SIM_NAME" | cat || true

echo "[2/5] Running trace analyzer (analyze_traces.py)"
python3 "$ANALYZER_DIR/analyze_traces.py" | cat || true

echo "[3/5] Running FlowMonitor analyzer"
python3 "$ANALYZER_DIR/visualize_flowmon_for_5g_playground.py" | cat || true

echo "[4/5] Running PCAP TCP path analyzer if PCAPs exist"
if ls "$OUT_DIR" | grep -q "5g_playfield_rw_pcap"; then
  python3 "$ANALYZER_DIR/analyze_pcap_tcp_paths.py" | cat || true
else
  echo "No PCAPs found; skipping PCAP-based TCP path analysis."
fi

echo "[5/5] Running enhanced visualizer"
python3 "$ANALYZER_DIR/enhanced_visualizer.py" | cat || true

echo ""
echo "=========================================="
echo "Analysis Complete - Key Outputs:"
echo "=========================================="

echo "Listing key outputs:"
ls -l "$OUT_DIR" | sed -n \
  -e '/analysis_report.html/p' \
  -e '/performance_dashboard.png/p' \
  -e '/network_topology.png/p' \
  -e '/throughput_heatmap.png/p' \
  -e '/tr_mac_throughput.png/p' \
  -e '/tr_rate_distribution.png/p' \
  -e '/tcp_analysis.png/p' \
  -e '/flowmon-5g-playfield-rw.xml/p' || true

echo ""
echo "Output directory: $OUT_DIR"
echo "Open enhanced report: firefox $OUT_DIR/analysis_report.html"

# Clean up: remove temporary file from scratch
echo ""
echo "Cleaning up temporary files..."
rm -f "$SCRATCH_DIR/$SIM_NAME.cc"
echo "Cleanup complete."

echo ""
echo "=========================================="
echo "5G Pipeline Complete!"
echo "=========================================="
