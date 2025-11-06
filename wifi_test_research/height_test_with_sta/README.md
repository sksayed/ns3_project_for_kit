# Mesh AP Height Optimization Testing Framework

## Overview

Comprehensive testing framework to determine the optimal mesh AP mounting height by testing all combinations of:
- **AP Heights**: 1.5m, 10m, 15m
- **STA Heights**: 5m, 10m, 15m, 20m, 25m, 30m
- **Trials**: 3 runs per configuration (with different random seeds)

**Total**: 54 simulations (3 × 6 × 3)

## Directory Structure

```
height_test_with_sta/
├── README.md                  # This file
├── run_analysis.sh            # Master script (runs everything)
├── run_all_tests.sh           # Test automation script
├── parse_results.py           # FlowMonitor XML parser
├── generate_summary.py        # Summary table generator
├── ap_1.5m/                   # Results for AP height 1.5m
│   ├── sta_5m/
│   │   ├── trial1/
│   │   ├── trial2/
│   │   └── trial3/
│   ├── sta_10m/
│   └── ... (6 STA heights)
├── ap_10m/                    # Results for AP height 10m
├── ap_15m/                    # Results for AP height 15m
└── results/
    ├── parsed_results.csv     # Aggregated statistics
    └── ap*_sta*_trial*_flowmon.xml  # All FlowMonitor XMLs
```

## Quick Start

### Option 1: Run Complete Analysis (Recommended)

```bash
cd /home/sayed/ns-3-dev/wifi_test_research/height_test_with_sta
bash run_analysis.sh
```

This will:
1. Build the simulation
2. Run all 54 tests (~40 minutes)
3. Parse FlowMonitor results
4. Generate analysis report

### Option 2: Step-by-Step Execution

```bash
# 1. Build simulation
cd /home/sayed/ns-3-dev
./ns3 build wifi-test-2-adhoc-grid

# 2. Run tests
cd wifi_test_research/height_test_with_sta
bash run_all_tests.sh

# 3. Parse results
python3 parse_results.py

# 4. Generate summary
python3 generate_summary.py
```

## Test Configuration

### Simulation Parameters
- **Simulation Time**: 35 seconds per test
- **Number of STAs**: 10 mobile clients
- **Traffic Type**: TCP (STA → Internet Server 8.8.8.2)
- **Mesh Network**: 9 nodes in 3×3 grid, 250m spacing
- **Buildings**: 4 buildings (15m tall) with HybridBuildingsPropagationLossModel
- **Random Seeds**: trial1=1, trial2=2, trial3=3

### Command Format
```bash
./ns3 run "wifi-test-2-adhoc-grid \
    --meshApHeight=<1.5|10|15> \
    --staHeight=<5|10|15|20|25|30> \
    --simTime=35 \
    --numStaNodes=10 \
    --RngRun=<1|2|3>"
```

## Output Metrics

### Per Configuration (Mean ± Std from 3 trials)
- **PDR (Packet Delivery Ratio)**: Percentage of successfully delivered packets
- **Throughput**: Average data rate in Mbps
- **End-to-End Delay**: Average packet latency in milliseconds
- **Rating**: Performance classification (Excellent, Very Good, Good, Fair, Poor)

### Output Files
1. **`results/parsed_results.csv`**: Raw statistics for all configurations
2. **`ANALYSIS-RESULTS.md`**: Complete analysis with:
   - Overall results table (sorted by performance)
   - Results grouped by AP height
   - Top 5 configurations by PDR, delay, and throughput
   - Recommendations

## Understanding Results

### Rating System
- ⭐ **Excellent**: PDR ≥ 99% AND Delay < 10ms
- ✅ **Very Good**: PDR ≥ 98% AND Delay < 15ms
- ✅ **Good**: PDR ≥ 95% AND Delay < 20ms
- ⚠️ **Fair**: PDR ≥ 90%
- ❌ **Poor**: PDR < 90%

### Interpreting Results
- **High PDR** (>95%): Good connectivity
- **Low Delay** (<15ms): Suitable for real-time applications
- **High Throughput** (>5 Mbps): Adequate for video streaming

## Customization

### Modify Test Parameters

Edit `run_all_tests.sh`:
```bash
AP_HEIGHTS=(1.5 10 15)      # Add/remove AP heights
STA_HEIGHTS=(5 10 15 20 25 30)  # Add/remove STA heights
SIM_TIME=35                 # Simulation duration
NUM_STA=10                  # Number of STA clients
```

### Modify Simulation

Edit `/home/sayed/ns-3-dev/wifi_test_research/wifi-test-2-adhoc-grid.cc`:
- Node spacing (line ~743)
- Building configuration (line ~120)
- Traffic patterns (line ~500)

## Troubleshooting

### Build Errors
```bash
cd /home/sayed/ns-3-dev
./ns3 clean
./ns3 configure --enable-examples
./ns3 build wifi-test-2-adhoc-grid
```

### Missing FlowMonitor Files
Check simulation logs in test directories:
```bash
cat ap_1.5m/sta_5m/trial1/simulation.log
```

### Parsing Errors
Verify FlowMonitor XML files exist:
```bash
ls -lh results/*_flowmon.xml | wc -l  # Should show 54 files
```

## Time Estimates

- **Per simulation**: ~40 seconds
- **Total runtime**: ~36 minutes (54 × 40s)
- **Parsing**: ~1 minute
- **Summary generation**: <10 seconds
- **Total**: ~40 minutes

## Example Output

```
=== Testing AP Height: 1.5m ===
  → STA Height: 5m
    [1/54 - 1%] trial1
      ✓ Completed successfully
    [2/54 - 3%] trial2 (ETA: 35m 20s)
      ✓ Completed successfully
...
```

## Next Steps

After analysis completes:
1. Review `ANALYSIS-RESULTS.md`
2. Identify optimal AP height configuration
3. Use optimal height in production deployments
4. Consider vertical mesh topology for tall buildings

## References

- NS-3 Documentation: https://www.nsnam.org/documentation/
- HybridBuildingsPropagationLossModel: NS-3 Buildings Module
- 802.11s Mesh: IEEE Standard for Mesh Networking

