#!/usr/bin/env bash
# Quick test script for tcp_mesh_adhoc_mode simulation

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Testing TCP Mesh Ad-hoc Mode Simulation                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Get script directory (wifi_mesh_tcp_lab)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "SCRIPT_DIR: $SCRIPT_DIR"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
echo "ROOT_DIR: $ROOT_DIR"

echo "📁 Working directory: $ROOT_DIR"
echo "📂 Output directory: $SCRIPT_DIR"
echo ""

# Navigate to ns-3 root
cd "$ROOT_DIR" || exit 1

# Run simulation
echo "▶️  Running simulation..."
echo "   Command: ./ns3 run wifi_mesh_tcp_lab/tcp_mesh_adhoc_mode"
echo ""
./ns3 run wifi_mesh_tcp_lab/tcp_mesh_adhoc_mode

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Simulation Complete - Checking Output Files            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check for output files
if [ -f "$SCRIPT_DIR/tcp_mesh_adhoc_mode_flowmon.xml" ]; then
    echo "✅ FlowMonitor XML: $(ls -lh "$SCRIPT_DIR/tcp_mesh_adhoc_mode_flowmon.xml" | awk '{print $5, $9}')"
else
    echo "❌ FlowMonitor XML not found"
fi

if [ -f "$SCRIPT_DIR/tcp_mesh_adhoc_mode.tr" ]; then
    echo "✅ ASCII Trace:     $(ls -lh "$SCRIPT_DIR/tcp_mesh_adhoc_mode.tr" | awk '{print $5, $9}')"
else
    echo "❌ ASCII Trace not found"
fi

PCAP_COUNT=$(ls -1 "$SCRIPT_DIR"/tcp_mesh_adhoc_mode-*.pcap 2>/dev/null | wc -l)
if [ "$PCAP_COUNT" -gt 0 ]; then
    echo "✅ PCAP files:      $PCAP_COUNT files found"
    ls -lh "$SCRIPT_DIR"/tcp_mesh_adhoc_mode-*.pcap | awk '{print "   •", $9}'
else
    echo "❌ PCAP files not found"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Analyzing Results                                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Run analysis script
if [ -f "$SCRIPT_DIR/tcp_calculation_example.py" ]; then
    echo "▶️  Running analysis script..."
    python3 "$SCRIPT_DIR/tcp_calculation_example.py"
else
    echo "❌ Analysis script not found"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  All Done!                                               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📂 All output files are in: wifi_mesh_tcp_lab/"
echo ""

