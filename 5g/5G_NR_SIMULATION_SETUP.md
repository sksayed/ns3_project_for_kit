# 5G NR Playfield Simulation - Setup and Run Instructions

## Files Created

### Main Simulation File
- **Location**: `/home/sayed/ns-3-dev/scratch/nr_playfield_traces.cc` (also in `/home/sayed/ns-3-dev/5g/src/`)
- **Size**: 575 lines
- **Purpose**: Complete 5G NR simulation with TCP/UDP traffic, mobile nodes, and obstacles

## Critical Fix Applied

### Issue Found
The simulation was crashing with a TypeId error during initialization. Using gdb, we identified the problem was in the `NrPointToPointEpcHelper` constructor.

### Solution
Add this line **BEFORE** creating any NR helpers (around line 297-298):

```cpp
// Set default configuration before creating helpers
Config::SetDefault("ns3::NrEpsBearer::Release", UintegerValue(15));
```

This fix has already been applied to the scratch version of the file.

## Simulation Features

### Network Topology
- **10 UE nodes** (User Equipment / mobile devices)
  - UE 0 (Sayed): Fixed at (0, 0, 1.5)
  - UE 9 (Sadia): Fixed at (400, 400, 1.5)
  - UE 1-8: Mobile nodes with RandomWalk2d mobility
- **3 gNB nodes** (5G base stations)
  - gNB 0: (100, 200, 15)
  - gNB 1: (100, 50, 15)
  - gNB 2: (300, 300, 15)
- **EPC Core Network** with PGW, SGW, and Remote Host

### 5G Configuration
- **Frequency**: 3.5 GHz (mid-band 5G)
- **Bandwidth**: 100 MHz
- **Numerology**: 1 (SCS = 30 kHz)
- **Scenario**: UMi (Urban Micro)
- **Channel Model**: 3GPP TR 38.901
- **Transmit Power**: 
  - gNB: 16 dBm
  - UE: 10 dBm

### Traffic Patterns
1. **Bidirectional UDP**: Sayed ↔ Sadia (4 Mbps each direction)
2. **Bidirectional TCP**: Sayed ↔ Sadia (bulk transfer)
3. **IoT bursts**: Middle UEs → Sayed (small packets)

### Obstacles
- **7 static buildings** creating realistic urban obstacles
- **Dynamic building movements** (currently commented out for initial testing)

### Output Files (saved to `5g_outputs/` directory)
- FlowMonitor XML: `flowmon-nr-playfield-rw.xml`
- NetAnim visualization: `netanim-nr-playfield-rw.xml`
- PCAP traces: `nr_playfield_rw_pcap-*.pcap`
- ASCII traces: `nr_playfield_ascii_traces.tr`
- IPv4 L3 traces: `ipv4-l3.tr`

## How to Run

### After Current Build Completes:

```bash
cd /home/sayed/ns-3-dev
./ns3 run nr_playfield_traces.cc
```

### Expected Runtime
- Simulation time: 10 seconds
- Real time: varies (2-5 minutes depending on system)

### Expected Output
1. Console output showing:
   - gNB positions and distances
   - UE attachment to gNBs
   - Distance calculations
   - UDP server info logs

2. Files in `5g_outputs/` directory ready for analysis

## Troubleshooting

### If you get the TypeId error:
Make sure this line is present before creating the EPC helper:
```cpp
Config::SetDefault("ns3::NrEpsBearer::Release", UintegerValue(15));
```

### If compilation fails:
The file should compile cleanly with the NR module installed. Make sure:
- NR module is in `contrib/nr/`
- All NR module dependencies are met

### To enable dynamic building movements:
Uncomment lines 248-294 in the simulation file.

## Differences from LTE Version

1. **Helpers**: Uses `NrHelper`, `NrPointToPointEpcHelper`, `NrChannelHelper`, `IdealBeamformingHelper`
2. **Spectrum Configuration**: Uses `CcBwpCreator` for bandwidth part configuration
3. **Channel Model**: 3GPP TR 38.901 (5G specific)
4. **Antenna Configuration**: MIMO with configurable rows/columns
5. **Attachment**: Uses `AttachToGnb()` instead of `Attach()`
6. **Traces**: Uses `EnableTraces()` instead of individual trace enables

## Next Steps

1. Wait for current build to complete
2. Run the simulation
3. Analyze output files
4. If successful, enable dynamic building movements
5. Compare results with LTE version

## File Locations

- Main simulation: `/home/sayed/ns-3-dev/scratch/nr_playfield_traces.cc`
- Backup: `/home/sayed/ns-3-dev/5g/src/nr_playfield_traces.cc`
- Build output: `build/scratch/ns3-dev-nr_playfield_traces-default`
- Results: `5g_outputs/`

