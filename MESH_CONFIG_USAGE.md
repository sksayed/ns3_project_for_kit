# Mesh AP Configuration System - Usage Guide

## Overview
Your NS-3 simulation now supports three real-world mesh AP configurations based on actual hardware specifications. The system uses a struct-based approach to store all mesh-related parameters and automatically adjusts the topology (grid size) based on the device's range.

## Three Mesh AP Configurations

### Config 0: Default Balanced (Default if no argument)
- **Use Case**: Medium-range balanced deployment
- **Range**: ~100 meters
- **Grid**: 5x5 (25 APs)
- **AP Spacing**: 85m
- **AP Height**: 20m
- **WiFi Standard**: 802.11n
- **TX Power**: 23 dBm
- **RX Sensitivity**: -96 dBm

### Config 1: TP-Link EAP225-Outdoor
- **Use Case**: Long-range outdoor deployment
- **Range**: ~200 meters
- **Grid**: 3x3 (9 APs)
- **AP Spacing**: 150m
- **AP Height**: 15m (outdoor pole mount)
- **WiFi Standard**: 802.11ac (VhtMcs8)
- **TX Power**: 27 dBm
- **RX Sensitivity**: -96 dBm
- **Gains**: RX Gain 3 dB, TX Gain 3 dB (external antennas)
- **Interfaces**: 2

### Config 2: Netgear Orbi 960 (WiFi 6E)
- **Use Case**: High-end indoor mesh
- **Range**: ~50 meters
- **Grid**: 10x10 (100 APs!)
- **AP Spacing**: 40m
- **AP Height**: 2m (desk/shelf height)
- **WiFi Standard**: 802.11ax (HeMcs11)
- **TX Power**: 20 dBm
- **RX Sensitivity**: -85 dBm
- **Interfaces**: 4 (quad-band)

### Config 3: ASUS ZenWiFi AX (XT8)
- **Use Case**: Premium indoor mesh
- **Range**: ~60 meters
- **Grid**: 9x9 (81 APs)
- **AP Spacing**: 45m
- **AP Height**: 2m (desk/shelf height)
- **WiFi Standard**: 802.11ax (HeMcs9)
- **TX Power**: 20 dBm
- **RX Sensitivity**: -82 dBm
- **Interfaces**: 3 (tri-band)

## Command-Line Usage

### Basic Examples

```bash
# Default configuration (5x5 grid, 100m range)
./ns3 run "scratch/tcp_mesh_backhaul_mode"

# TP-Link EAP225-Outdoor (3x3 grid, 200m range)
./ns3 run "scratch/tcp_mesh_backhaul_mode --meshConfig=1"

# Netgear Orbi 960 (10x10 grid, 50m range)
./ns3 run "scratch/tcp_mesh_backhaul_mode --meshConfig=2"

# ASUS ZenWiFi AX (9x9 grid, 60m range)
./ns3 run "scratch/tcp_mesh_backhaul_mode --meshConfig=3"
```

### Combined with Other Parameters

```bash
# TP-Link with obstacles, 100KB packets, 30 second simulation
./ns3 run "scratch/tcp_mesh_backhaul_mode --meshConfig=1 --obstacles=1 --packetSize=100 --simTime=30"

# Orbi 960 with TCP only traffic, 1MB packets
./ns3 run "scratch/tcp_mesh_backhaul_mode --meshConfig=2 --trafficType=tcp --packetSize=1024"

# ZenWiFi with 5 STAs
./ns3 run "scratch/tcp_mesh_backhaul_mode --meshConfig=3 --nSTAs=5"
```

## Available Command-Line Arguments

| Argument | Description | Default | Valid Range |
|----------|-------------|---------|-------------|
| `--meshConfig` | Mesh AP configuration | 0 | 0-3 |
| `--nSTAs` | Number of STAs | 2 | 2-9 |
| `--packetSize` | Packet size in KB | 10 | ≥1 |
| `--trafficType` | Traffic type | "both" | tcp, udp, both |
| `--simTime` | Simulation time (seconds) | 15.0 | >0 |
| `--obstacles` | Enable obstacles | 0 | 0 (no), 1 (yes) |

## What Changes Automatically with Each Config?

When you select a mesh configuration, the following parameters automatically adjust:

1. **Physical Layer**:
   - TX Power (Start/End)
   - RX Sensitivity
   - RX Gain, TX Gain
   
2. **WiFi Configuration**:
   - WiFi Standard (802.11n/ac/ax)
   - Data Mode (MCS index)
   - Number of mesh interfaces
   
3. **Topology**:
   - Grid size (3x3 to 10x10)
   - Total number of APs (9 to 100)
   - AP spacing
   - AP height
   - Coverage area

4. **STA Distribution**:
   - STAs are automatically distributed across the grid
   - Sayed always at AP0 (bottom-left corner)
   - Sadia always at last AP (top-right corner)
   - Additional STAs spread across center and edges

## Key Features

### Struct-Based Configuration
All mesh parameters are stored in a `MeshAPConfig` struct:
```cpp
struct MeshAPConfig {
    std::string name;           // Device name
    std::string description;    // Use case
    double txPowerStart;        // TX power (dBm)
    double txPowerEnd;
    double rxSensitivity;       // RX sensitivity (dBm)
    double rxGain;              // RX gain (dB)
    double txGain;              // TX gain (dB)
    std::string wifiStandard;   // WiFi standard
    std::string dataMode;       // MCS mode
    uint32_t numInterfaces;     // Number of interfaces
    double meshRange;           // Expected range (m)
    double apHeight;            // AP height (m)
    double apSpacing;           // AP spacing (m)
    uint32_t gridSize;          // Grid size (NxN)
};
```

### Dynamic Topology Adaptation
- **Long-range devices** (TP-Link): Fewer APs with wider spacing (3x3 grid)
- **Medium-range devices** (Default): Balanced deployment (5x5 grid)
- **Short-range devices** (Orbi, ZenWiFi): Dense deployment (9x9 or 10x10 grid)

### Realistic Hardware Parameters
All parameters are based on actual product specifications:
- TP-Link EAP225-Outdoor: Real outdoor mesh AP
- Netgear Orbi 960: Real WiFi 6E mesh system
- ASUS ZenWiFi AX XT8: Real WiFi 6 mesh system

## Expected Behavior

### TP-Link EAP225-Outdoor (Config 1)
- Long-range outdoor scenario
- Only 9 APs needed for 400m x 400m field
- Higher TX power (27 dBm)
- External antenna gains (3 dB)
- Longer hop counts due to sparse topology

### Netgear Orbi 960 (Config 2)
- Dense indoor deployment
- 100 APs for 400m field (overkill, but shows capability)
- WiFi 6E with quad-band
- Lower TX power (indoor regulations)
- Short hop counts, many redundant paths

### ASUS ZenWiFi AX (Config 3)
- Premium indoor mesh
- 81 APs for balanced coverage
- WiFi 6 with tri-band
- Slightly better RX sensitivity than Orbi

## Adding Your Own Configuration

To add a new mesh AP configuration:

1. Add a new case in `GetMeshConfig()` function (lines 61-144)
2. Specify all parameters for your device
3. Calculate appropriate grid size for 400m field
4. Update the command-line help text

Example:
```cpp
case 4:
    return MeshAPConfig(
        "Your Device Name",
        "Use case description",
        txPower, txPower,
        rxSensitivity,
        rxGain, txGain,
        "WIFI_STANDARD_80211ax",
        "HeMcs10",
        numInterfaces,
        targetRange,
        apHeight,
        apSpacing,
        calculatedGridSize
    );
```

## Output Information

The simulation now displays comprehensive configuration information:
- Selected mesh AP device name and description
- Physical layer parameters
- WiFi standard and data mode
- Number of interfaces
- Grid size and topology details
- Expected range and coverage

## Notes

- The default config (0) remains unchanged to preserve backward compatibility
- All configurations work with obstacles (--obstacles=1)
- STA distribution adapts automatically to grid size
- Hop count calculations adjust based on grid dimensions

## Troubleshooting

**Simulation too slow with Config 2 (Orbi 960)?**
- The 10x10 grid creates 100 APs which is computationally intensive
- Use Config 3 (ZenWiFi) with 81 APs or Config 0/1 for faster simulations

**Range seems incorrect?**
- NS-3 range depends on many factors: path loss, obstacles, interference
- The "expected range" is theoretical; actual range varies
- Enable obstacles (--obstacles=1) to see realistic attenuation

**Want to test specific device parameters?**
- Edit the config in `GetMeshConfig()` function
- Adjust TX power, RX sensitivity, or gains
- Recompile and test

