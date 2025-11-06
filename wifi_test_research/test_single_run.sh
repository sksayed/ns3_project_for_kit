#!/bin/bash
################################################################################
# Test script to run a single simulation before full study
# Tests with minimal parameters: 3 STAs, 10KB packets, Config 1 (TP-Link)
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

NS3_DIR="/home/sayed/ns-3-dev"
TEST_OUTPUT="$NS3_DIR/wifi_test_research/test_output"

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}        TESTING SINGLE SIMULATION RUN${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

cd "$NS3_DIR"

# Clean test output
echo "Cleaning previous test output..."
rm -rf "$TEST_OUTPUT"
mkdir -p "$TEST_OUTPUT"

# Test parameters
STA_COUNT=3
PACKET_SIZE=10240  # 10KB
MESH_CONFIG=1      # TP-Link

echo "Test Configuration:"
echo "  STAs: $STA_COUNT"
echo "  Packet Size: $PACKET_SIZE bytes (10KB)"
echo "  Mesh Config: $MESH_CONFIG (TP-Link EAP225)"
echo ""

# Compile first
echo -e "${YELLOW}Step 1: Compiling...${NC}"
./ns3 build || { echo "Compilation failed!"; exit 1; }
echo -e "${GREEN}✓ Compiled${NC}"
echo ""

# Run simulation
echo -e "${YELLOW}Step 2: Running test simulation...${NC}"
echo "Command: ./ns3 run \"wifi_test_research/wifi-test-2-adhoc-grid --numStaNodes=$STA_COUNT --meshConfig=$MESH_CONFIG --packetSize=$PACKET_SIZE\""
echo ""

START=$(date +%s)

./ns3 run "wifi_test_research/wifi-test-2-adhoc-grid --numStaNodes=$STA_COUNT --meshConfig=$MESH_CONFIG --packetSize=$PACKET_SIZE" || {
    echo -e "${RED}Simulation failed!${NC}"
    exit 1
}

END=$(date +%s)
DURATION=$((END - START))

echo ""
echo -e "${GREEN}✓ Simulation completed in ${DURATION}s${NC}"
echo ""

# Move outputs to test directory
echo -e "${YELLOW}Step 3: Organizing outputs...${NC}"
mv wifi_test_research/wifi-test-2-adhoc-grid.xml "$TEST_OUTPUT/" 2>/dev/null || echo "  Warning: XML file not found"
mv wifi_test_research/wifi-test-2-sta.tr "$TEST_OUTPUT/" 2>/dev/null || echo "  Warning: STA trace file not found"
mv wifi_test_research/wifi-test-2-adhoc-grid.tr "$TEST_OUTPUT/" 2>/dev/null || echo "  Warning: mesh trace file not found"
mv wifi_test_research/wifi-test-2-adhoc-grid-flowmon.xml "$TEST_OUTPUT/" 2>/dev/null || echo "  Warning: FlowMonitor file not found"
mv wifi_test_research/wifi-test-2-adhoc-grid-routes.xml "$TEST_OUTPUT/" 2>/dev/null || echo "  Warning: routes file not found"
mv wifi_test_research/config_test_2.json "$TEST_OUTPUT/" 2>/dev/null || echo "  Warning: config JSON not found"

echo -e "${GREEN}✓ Outputs moved to $TEST_OUTPUT${NC}"
echo ""

# Run path verification
if [ -f "$TEST_OUTPUT/wifi-test-2-adhoc-grid.xml" ]; then
    echo -e "${YELLOW}Step 4: Running path verification...${NC}"
    python3 wifi_test_research/test_2_verify_mesh_path.py \
        --xml "$TEST_OUTPUT/wifi-test-2-adhoc-grid.xml" \
        --sta-tr "$TEST_OUTPUT/wifi-test-2-sta.tr" || {
        echo "  Warning: Path verification had issues"
    }
    echo ""
fi

# Check output files
echo -e "${YELLOW}Step 5: Verifying outputs...${NC}"
echo "Files generated:"
ls -lh "$TEST_OUTPUT" | tail -n +2 | awk '{print "  " $9 " (" $5 ")"}'
echo ""

# Parse FlowMonitor if exists
if [ -f "$TEST_OUTPUT/wifi-test-2-adhoc-grid-flowmon.xml" ]; then
    echo -e "${YELLOW}Step 6: Quick metrics check...${NC}"
    
    # Extract basic metrics using grep/sed
    TOTAL_FLOWS=$(grep -c '<Flow flowId=' "$TEST_OUTPUT/wifi-test-2-adhoc-grid-flowmon.xml" || echo "0")
    echo "  Total flows: $TOTAL_FLOWS"
    
    # Show first flow details
    if [ "$TOTAL_FLOWS" -gt "0" ]; then
        echo ""
        echo "  Sample flow metrics:"
        grep '<Flow flowId=' "$TEST_OUTPUT/wifi-test-2-adhoc-grid-flowmon.xml" | head -1 | \
            sed 's/.*txPackets="\([^"]*\)".*/    TX Packets: \1/' | head -1
        grep '<Flow flowId=' "$TEST_OUTPUT/wifi-test-2-adhoc-grid-flowmon.xml" | head -1 | \
            sed 's/.*rxPackets="\([^"]*\)".*/    RX Packets: \1/' | head -1
    fi
    echo ""
fi

# Summary
echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}                      TEST COMPLETE!${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""
echo "Test output location: $TEST_OUTPUT"
echo ""
echo "If everything looks good, you can now run the full study with:"
echo -e "  ${BLUE}./wifi_test_research/run_complete_study.sh${NC}"
echo ""
echo -e "${GREEN}================================================================================${NC}"


