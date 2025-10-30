# WiFi Mesh TCP Lab

This directory contains various ns-3 simulations testing TCP communication in WiFi mesh networks.

## Simulation Files

### 1. `tcp_mesh_single_ap.cc`
**Original:** `simple_tcp_mesh_test.cc`

**Topology:**
```
Internet Server ----[Backhaul]---- Mesh AP
                                      |
                              +-------+-------+
                              |               |
                           STA1 (Sayed)   STA2 (Sadia)
```

**Features:**
- 1 Internet server with 100Mbps backhaul
- 1 Mesh AP (802.11n)
- 2 STAs on same WiFi network
- OLSR routing protocol
- TCP bulk transfer: 1MB from Sayed to Sadia

---

### 2. `tcp_mesh_adhoc_mode.cc` ✅ Working Version
**Original:** `simple_tcp_wifi_test_adhoc.cc`

**Topology:**
```
STA1 (Sayed) ---- Mesh AP1 <---> Mesh AP2 ---- STA2 (Sadia)
```

**Features:**
- 2 Mesh APs in ad-hoc mode
- 2 STAs (Sayed and Sadia)
- All nodes use ad-hoc WiFi (802.11g)
- Single subnet (10.1.1.0/24)
- Close positioning: 10-12m spacing
- No AP-STA association complexity

**Notes:** This is the **working baseline version** using ad-hoc mode to bypass infrastructure complexity.

---

### 3. `tcp_mesh_dual_ap_close.cc`
**Original:** `simple_tcp_wifi_test_backup.cc`

**Topology:**
```
STA1 (Sayed) ---- Mesh AP1 ====== Mesh AP2 ---- STA2 (Sadia)
    (5m)           (0m)    [P2P]    (50m)         (55m)
```

**Features:**
- 2 Mesh APs with P2P backhaul (100Mbps)
- Infrastructure mode (proper AP-STA associations)
- 802.11g standard
- Dual subnets:
  - Backhaul: 172.16.0.0/24
  - WiFi: 10.1.1.0/24
- **Close spacing:** 50m between APs

---

### 4. `tcp_mesh_dual_ap_distant.cc`
**Original:** `simple_tcp_wifi_test.cc`

**Topology:**
```
STA1 (Sayed) ---- Mesh AP1 ====== Mesh AP2 ---- STA2 (Sadia)
    (10m)          (0m)    [P2P]    (100m)        (110m)
```

**Features:**
- Similar to `tcp_mesh_dual_ap_close.cc`
- **Extended spacing:** 100m between APs (2x distance)
- Tests impact of distance on mesh performance

---

## Common Parameters

All simulations share these characteristics:
- **Simulation time:** 10 seconds
- **TCP port:** 7000
- **Data transfer:** 1MB bulk send (Sayed → Sadia)
- **Monitoring:** FlowMonitor enabled
- **Tracing:** PCAP and ASCII traces enabled

## Output Files

Each simulation generates:
- `*_flowmon.xml` - FlowMonitor performance data
- `*.tr` - ASCII trace files
- `*.pcap` - Packet capture files for Wireshark analysis

## Usage

Compile and run simulations using ns-3:

```bash
# From ns-3-dev root directory
./ns3 run wifi_mesh_tcp_lab/tcp_mesh_adhoc_mode

# Or copy to scratch directory first
cp wifi_mesh_tcp_lab/tcp_mesh_adhoc_mode.cc scratch/
./ns3 run scratch/tcp_mesh_adhoc_mode
```

## Evolution Path

```
tcp_mesh_single_ap.cc → tcp_mesh_dual_ap_close.cc → tcp_mesh_dual_ap_distant.cc
     (1 AP)                  (2 APs, 50m)              (2 APs, 100m)
                                    ↓
                          tcp_mesh_adhoc_mode.cc
                         (Ad-hoc workaround)
```

## Research Questions

These simulations help answer:
1. How does mesh AP spacing affect TCP throughput?
2. What's the performance difference between ad-hoc and infrastructure modes?
3. How does the backhaul link impact end-to-end communication?
4. What are the routing characteristics in mesh networks?

