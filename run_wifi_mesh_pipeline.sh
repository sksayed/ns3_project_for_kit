#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$ROOT_DIR/wifi_mesh_outputs"

echo "[1/4] Running simulation: scratch/wifi_mesh_playfield_traces"
./ns3 run "scratch/wifi_mesh_playfield_traces" | cat

echo "[2/4] Running trace analyzer (analyze_traces.py)"
python3 "$ROOT_DIR/wifi_mesh_analyzer/analyze_traces.py" | cat || true

## Removed FlowMonitor notebook execution step (no notebook present)

echo "[3/4] Running PCAP TCP path analyzer if PCAPs exist"
if ls "$OUT_DIR" | grep -q "wifi_mesh_playfield_rw_pcap"; then
  python3 "$ROOT_DIR/wifi_mesh_analyzer/analyze_pcap_tcp_paths.py" | cat || true
else
  echo "No PCAPs found; skipping PCAP-based TCP path analysis."
fi

echo "[4/4] Listing key outputs"
ls -l "$OUT_DIR" | sed -n \
  -e '/tr_paths_udp5000.csv/p' \
  -e '/tr_paths_tcp6000.csv/p' \
  -e '/tr_paths_tcp6001.csv/p' \
  -e '/tr_paths_tcp6000_pcap.csv/p' \
  -e '/tr_paths_tcp6001_pcap.csv/p' \
  -e '/tr_path_most_common.png/p' \
  -e '/tr_mac_throughput.png/p' \
  -e '/tr_rate_distribution.png/p' \
  -e '/flowmon-wifi-mesh-playfield-rw.xml/p' || true

echo "Done. Outputs are under $OUT_DIR"

echo "Run flow visualizer: python3 $ROOT_DIR/wifi_mesh_analyzer/visualize_flowmon_for_wifi_mesh_playground.py"


