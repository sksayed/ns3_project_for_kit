#!/bin/bash
#####################################################################
# Master Script for Mesh AP Height Optimization Analysis
# Orchestrates: Build → Test → Parse → Generate Summary
#####################################################################

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Paths
NS3_DIR="/home/sayed/ns-3-dev"
SCRIPT_DIR="$NS3_DIR/wifi_test_research/height_test_with_sta"

echo ""
echo "========================================================================"
echo "  MESH AP HEIGHT OPTIMIZATION - COMPLETE ANALYSIS"
echo "========================================================================"
echo "  This will:"
echo "    1. Build the simulation"
echo "    2. Run 54 test simulations (3 AP heights × 6 STA heights × 3 trials)"
echo "    3. Parse FlowMonitor results"
echo "    4. Generate summary analysis report"
echo ""
echo "  Estimated time: ~40 minutes"
echo "========================================================================"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""

# Step 1: Build the simulation
echo -e "${BLUE}[Step 1/4] Building simulation...${NC}"
cd "$NS3_DIR" || exit 1
./ns3 build wifi-test-2-adhoc-grid

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Build successful${NC}"
echo ""

# Step 2: Run all tests
echo -e "${BLUE}[Step 2/4] Running 54 test simulations...${NC}"
cd "$SCRIPT_DIR" || exit 1
bash run_all_tests.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Tests failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ All tests completed${NC}"
echo ""

# Step 3: Parse results
echo -e "${BLUE}[Step 3/4] Parsing FlowMonitor results...${NC}"
python3 parse_results.py

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Parsing failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Results parsed${NC}"
echo ""

# Step 4: Generate summary
echo -e "${BLUE}[Step 4/4] Generating summary report...${NC}"
python3 generate_summary.py

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Summary generation failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Summary generated${NC}"
echo ""

# Display summary
echo "========================================================================"
echo -e "${GREEN}  ANALYSIS COMPLETE!${NC}"
echo "========================================================================"
echo ""
echo "Results available at:"
echo "  - Raw data: $SCRIPT_DIR/results/parsed_results.csv"
echo "  - Analysis: $SCRIPT_DIR/ANALYSIS-RESULTS.md"
echo ""
echo "To view the analysis:"
echo "  cat $SCRIPT_DIR/ANALYSIS-RESULTS.md"
echo ""
echo "Or open in your editor:"
echo "  code $SCRIPT_DIR/ANALYSIS-RESULTS.md"
echo ""
echo "========================================================================"

