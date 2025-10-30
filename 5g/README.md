# 5G NR Simulation Framework

This directory contains a basic 5G NR (New Radio) simulation framework for ns-3, designed to facilitate data transfer between nodes using the NR module.

## Directory Structure

```
5g/
├── src/                    # Source code for NR simulations
│   └── simple-nr-simulation.cc
├── scripts/                # Helper scripts and functions
│   ├── run-simple-nr.sh
│   └── nr-helper-functions.cc
├── examples/               # Example simulations (to be added)
├── outputs/                # Simulation output files
└── README.md              # This file
```

## Features

- **Basic NR Network Setup**: Create gNBs and UEs with configurable parameters
- **Data Transfer**: UDP-based data transfer between gNBs and UEs
- **Mobility Support**: Configurable node positions
- **Flow Monitoring**: Comprehensive statistics collection
- **Beamforming Support**: Integrated ideal beamforming helper
- **Channel Modeling**: ThreeGPP channel model with UMi scenario
- **Helper Functions**: Reusable functions for common NR operations

## Quick Start

### 1. Run Simple NR Simulation

```bash
# From ns-3-dev root directory
cd /home/sayed/ns-3-dev
./5g/scripts/run-simple-nr.sh
```

### 2. Manual Execution

```bash
# Copy simulation to scratch
cp 5g/src/simple-nr-simulation.cc scratch/

# Build and run
./ns3 build
./ns3 run "simple-nr-simulation --simTime=1 --gNbNum=1 --ueNumPergNb=2"
```

## Simulation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--simTime` | 1.0 | Simulation time in seconds |
| `--numerology` | 0 | Numerology (0-4) |
| `--centralFrequency` | 2.1e9 | Central frequency in Hz (2.1 GHz) |
| `--bandwidth` | 100e6 | Bandwidth in Hz (100 MHz) |
| `--txPower` | 23 | TX power in dBm |
| `--gNbNum` | 1 | Number of gNBs |
| `--ueNumPergNb` | 2 | Number of UEs per gNB |
| `--enableLogging` | false | Enable detailed logging |

## Example Usage

### Basic Simulation
```bash
./ns3 run "simple-nr-simulation --simTime=5 --gNbNum=1 --ueNumPergNb=3"
```

### High Throughput Test
```bash
./ns3 run "simple-nr-simulation --simTime=10 --bandwidth=200e6 --txPower=30"
```

### Multi-gNB Scenario
```bash
./ns3 run "simple-nr-simulation --simTime=5 --gNbNum=2 --ueNumPergNb=2"
```

## Output

The simulation provides:
- **Flow Statistics**: Throughput, delay, packet counts per flow
- **Summary Statistics**: Total throughput, average delay
- **Trace Files**: Detailed traces in the outputs directory

### Sample Output
```
Flow 1 (1.0.0.2:49153 -> 7.0.0.2:1234)
  Tx Packets: 46000
  Tx Bytes:   5888000
  Rx Packets: 45998
  Throughput: 10.239555 Mbps
  Mean delay:  0.275911 ms

=== Summary ===
Total flows: 2
Total throughput: 56.308647 Mbps
Average delay: 0.586464 ms
```

## Helper Functions

The `nr-helper-functions.cc` file provides reusable functions:

- `CreateBasicNrNetwork()`: Set up NR network with gNBs and UEs
- `SetupMobility()`: Configure node positions
- `InstallUdpApplications()`: Install UDP applications for data transfer
- `PrintFlowStatistics()`: Display comprehensive flow statistics

## Requirements

- ns-3.45 with NR module v4.1
- Eigen3 library for MIMO support
- All NR module dependencies

## Troubleshooting

### Common Issues

1. **Build Errors**: Ensure NR module is properly installed and Eigen3 is available
2. **Runtime Crashes**: Check version compatibility (ns-3.45 + NR v4.1)
3. **No Data Transfer**: Verify node positions and antenna configurations

### Debug Mode

Enable detailed logging:
```bash
./ns3 run "simple-nr-simulation --enableLogging=true"
```

## Next Steps

- Add more complex scenarios (handover, interference)
- Implement different traffic patterns
- Add visualization support
- Create performance analysis tools

