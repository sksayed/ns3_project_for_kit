#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$ROOT_DIR/Lte_outputs"
NS3_CMD="$ROOT_DIR/ns3"
PROJECT_DIR="$ROOT_DIR/pic_lab_project"
ANALYZER_DIR="$ROOT_DIR/lte_analyzer"
SCRATCH_DIR="$ROOT_DIR/scratch"
SIM_NAME="lte_playfield_traces"

echo "[1/6] Running simulation: $SIM_NAME"
# Copy file to scratch temporarily for ns-3 launcher
cp "$PROJECT_DIR/$SIM_NAME.cc" "$SCRATCH_DIR/$SIM_NAME.cc"
"$NS3_CMD" run "scratch/$SIM_NAME" | cat || true

echo "[2/6] Running FlowMonitor analyzer"
python3 "$ANALYZER_DIR/visualize_flowmon_for_lte_playground_lte.py" | cat || true

echo "[3/6] Running PCAP TCP path analyzer if PCAPs exist"
if ls "$OUT_DIR" | grep -q "lte_playfield_rw_pcap"; then
  python3 "$ANALYZER_DIR/analyze_pcap_tcp_paths_lte.py" | cat || true
else
  echo "No PCAPs found; skipping PCAP-based TCP path analysis."
fi

echo "[4/6] Parsing IPv4 L3 traces (LTE-specific)"
python3 "$ANALYZER_DIR/analyze_lte_ipv4.py" | cat || true

echo "[5/6] Generating LTE topology visualization"
# Ensure imageio is available for GIF generation (topology animation)
python3 - <<'PY'
try:
    import imageio.v2 as _
    print('imageio present')
except Exception:
    print('installing imageio for GIF support...')
    import subprocess, sys
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'imageio'], check=False)
PY
python3 "$ANALYZER_DIR/visualize_lte_topology.py" | cat || true

echo "[6/6] Generating updated LTE HTML report"
python3 "$ANALYZER_DIR/generate_lte_report.py" | cat || true

echo "Listing key outputs"
ls -l "$OUT_DIR" | sed -n \
  -e '/flowmon-lte-playfield-rw.xml/p' \
  -e '/flowmon_analysis.png/p' \
  -e '/flowmon_analysis.csv/p' \
  -e '/lte_throughput_analysis.png/p' \
  -e '/lte_topology_visualization.png/p' \
  -e '/lte_topology_animation.gif/p' \
  -e '/lte_analysis_report_updated.html/p' || true

echo "Done. Outputs are under $OUT_DIR"

echo "Open updated LTE report: firefox $OUT_DIR/lte_analysis_report_updated.html"

# Clean up: remove temporary file from scratch
echo "Cleaning up temporary files..."
rm -f "$SCRATCH_DIR/$SIM_NAME.cc"
echo "Cleanup complete."
