#!/bin/bash
#####################################################################
# Mesh AP Height Optimization Testing Script
# Tests 3 AP heights × 6 STA heights × 3 trials = 54 simulations
#####################################################################

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AP_HEIGHTS=(1.5 10 15)
STA_HEIGHTS=(5 10 15 20 25 30)
TRIALS=(trial1 trial2 trial3)
SIM_TIME=35
NUM_STA=10

# Paths
NS3_DIR="/home/sayed/ns-3-dev"
OUTPUT_DIR="$NS3_DIR/wifi_test_research/height_test_with_sta"
RESULTS_DIR="$OUTPUT_DIR/results"

# Counters
TOTAL_TESTS=$((${#AP_HEIGHTS[@]} * ${#STA_HEIGHTS[@]} * ${#TRIALS[@]}))
CURRENT_TEST=0
START_TIME=$(date +%s)

echo "========================================================================"
echo "  MESH AP HEIGHT OPTIMIZATION TESTING"
echo "========================================================================"
echo "  Total configurations: ${#AP_HEIGHTS[@]} AP heights × ${#STA_HEIGHTS[@]} STA heights × ${#TRIALS[@]} trials"
echo "  Total simulations: $TOTAL_TESTS"
echo "  Simulation time: ${SIM_TIME}s per test"
echo "  Number of STAs: $NUM_STA"
echo "  Estimated duration: ~$((TOTAL_TESTS * 40 / 60)) minutes"
echo "========================================================================"
echo ""

# Change to NS-3 directory
cd "$NS3_DIR" || exit 1

# Loop through AP heights
for ap_h in "${AP_HEIGHTS[@]}"; do
    echo -e "${BLUE}=== Testing AP Height: ${ap_h}m ===${NC}"
    
    # Loop through STA heights
    for sta_h in "${STA_HEIGHTS[@]}"; do
        echo -e "${GREEN}  → STA Height: ${sta_h}m${NC}"
        
        # Loop through trials
        for trial in "${TRIALS[@]}"; do
            CURRENT_TEST=$((CURRENT_TEST + 1))
            
            # Convert trial name to seed number
            seed=0
            if [ "$trial" == "trial1" ]; then
                seed=1
            elif [ "$trial" == "trial2" ]; then
                seed=2
            elif [ "$trial" == "trial3" ]; then
                seed=3
            fi
            
            # Calculate progress
            PERCENT=$((CURRENT_TEST * 100 / TOTAL_TESTS))
            ELAPSED=$(($(date +%s) - START_TIME))
            if [ $CURRENT_TEST -gt 1 ]; then
                AVG_TIME=$((ELAPSED / (CURRENT_TEST - 1)))
                REMAINING=$(((TOTAL_TESTS - CURRENT_TEST) * AVG_TIME))
                ETA_MIN=$((REMAINING / 60))
                ETA_SEC=$((REMAINING % 60))
                echo -e "${YELLOW}    [${CURRENT_TEST}/${TOTAL_TESTS} - ${PERCENT}%] ${trial} (ETA: ${ETA_MIN}m ${ETA_SEC}s)${NC}"
            else
                echo -e "${YELLOW}    [${CURRENT_TEST}/${TOTAL_TESTS} - ${PERCENT}%] ${trial}${NC}"
            fi
            
            # Define output directory for this configuration
            TEST_DIR="$OUTPUT_DIR/ap_${ap_h}m/sta_${sta_h}m/$trial"
            mkdir -p "$TEST_DIR"
            
            # Run simulation
            ./ns3 run "wifi-test-2-adhoc-grid \
                --meshApHeight=$ap_h \
                --staHeight=$sta_h \
                --simTime=$SIM_TIME \
                --numStaNodes=$NUM_STA \
                --RngRun=$seed" > "$TEST_DIR/simulation.log" 2>&1
            
            # Check if simulation succeeded
            if [ $? -eq 0 ]; then
                # Copy FlowMonitor XML to results directory with descriptive name
                FLOWMON_FILE="wifi_test_research/wifi-test-2-adhoc-grid-flowmon.xml"
                if [ -f "$FLOWMON_FILE" ]; then
                    cp "$FLOWMON_FILE" "$RESULTS_DIR/ap${ap_h}m_sta${sta_h}m_${trial}_flowmon.xml"
                    echo "      ✓ Completed successfully"
                else
                    echo "      ⚠ Warning: FlowMonitor file not found"
                fi
            else
                echo "      ✗ Simulation failed! Check $TEST_DIR/simulation.log"
            fi
            
        done
        echo ""
    done
    echo ""
done

TOTAL_TIME=$(($(date +%s) - START_TIME))
TOTAL_MIN=$((TOTAL_TIME / 60))
TOTAL_SEC=$((TOTAL_TIME % 60))

echo "========================================================================"
echo "  ALL TESTS COMPLETED!"
echo "========================================================================"
echo "  Total time: ${TOTAL_MIN}m ${TOTAL_SEC}s"
echo "  Results saved to: $RESULTS_DIR"
echo "  Total FlowMonitor files: $(ls -1 $RESULTS_DIR/*.xml 2>/dev/null | wc -l)"
echo "========================================================================"
echo ""
echo "Next step: Run 'python3 parse_results.py' to analyze the data"

