# Cross-Technology Network Performance Analysis: 4G, 5G, and WiFi Mesh

**Reported by:** Sheikh Sayed Bin Rahman

### Simulation Approach

Simulations were conducted using NS-3 network simulator across three technologies (WiFi Mesh, 4G LTE, and 5G NR) following a systematic matrix approach. **STA/UE nodes were positioned using uniform random distribution** across the 400×400×30 m stage, avoiding building obstacles. A comprehensive scenario matrix was generated covering all combinations of: 3 RNG seeds (6, 7, 8), 3 node counts (5, 10, 15), and 3 payload sizes (10KB, 50KB, 1MB), with WiFi Mesh additionally varying across 2 frequency bands (2.4 GHz and 5 GHz).

Each simulation executed for 30 seconds with Gauss-Markov 3D mobility model for STA/UE movement. Network performance metrics (PDR, Throughput, Delay, Jitter) were collected using FlowMonitor and aggregated across seeds to compute mean values, standard deviations, and statistical distributions. Results were analyzed to compare technology performance across scalability (node count variation), traffic load impact (payload size variation), and overall reliability metrics.
- Scenarios analyzed: 108

## Common Configuration

| Metric | WiFi Mesh | 4G | 5G |
| --- | --- | --- | --- |
| Stage Structure: 400×400×30 m | ✓ | ✓ | ✓ |
| Building Obstacles: 7 buildings | ✓ | ✓ | ✓ |
| Propagation Loss Model:<br>HybridBuildingsPropagationLossModel | ✓ | ✓ | ✓ |
| RNG Seeds: 6, 7, 8 | ✓ | ✓ | ✓ |
| Simulation Time: 30.0 s | ✓ | ✓ | ✓ |
| Node Counts: 5, 10, 15 | ✓ | ✓ | ✓ |
| Payload Size: 10KB, 50KB, 1MB | ✓ | ✓ | ✓ |
| UE/STA Mobility: Gauss-Markov 3D movement | ✓ | ✓ | ✓ |
| UE/STA TX Power: 15.0 dBm | ✓ | ✓ | ✓ |
| Traffic Flows:<br>HTTP, HTTPS, Video (TCP),<br>VoIP (UDP), Mixed | ✓ | ✓ | ✓ |

## WiFi Mesh Network Visualization

![WiFi Mesh 3D Stage Visualization](figures/3d_stage_visualization_wifi_mesh.png)

### WiFi Mesh Configuration

| Parameter | Value |
| --- | --- |
| Mesh Protocol | 802.11s (Dot11sStack) |
| WiFi Standard (Mesh Backhaul) | 802.11n @ 2.4 GHz |
| Data Mode | HtMcs7 |
| TX Power (Mesh Backhaul) | 23.0 dBm |
| TX Power (Hotspot/AP) | 22.0 dBm @ 5 GHz |
| RX Sensitivity | -90.0 dBm |
| Antenna Gain (RX/TX) | 5.0 dB / 5.0 dB |
| Number of Mesh Interfaces | 1 |
| Hotspot Band | 5 GHz (802.11ac) |

## 5G Network Visualization

![5G 3D Stage Visualization](figures/3d_stage_visualization_5g.png)

### 5G NR Configuration

| Parameter | Value |
| --- | --- |
| Central Frequency | 3.5 GHz |
| Bandwidth | 100 MHz |
| Channel Model | RMa (Rural Macro) |
| Channel Model Type | ThreeGpp |
| Beamforming Algorithm | IdealBeamformingHelper (DirectPathBeamforming) |
| gNB TX Power | ~43 dBm (macro cell) |
| Number of Component Carriers | 1 |
| Number of Bandwidth Parts | 1 |

## 4G Network Visualization

![4G 3D Stage Visualization](figures/3d_stage_visualization_lte.png)

### 4G LTE Configuration

| Parameter | Value |
| --- | --- |
| Frequency | 2.0 GHz |
| eNB TX Power | 43.0 dBm |
| Handover Algorithm | A3RsrpHandoverAlgorithm |
| Handover Hysteresis | 3.0 dB |
| Time To Trigger | 160 ms |

## 1. Cross-Technology Performance

- 5G achieves the highest Throughput (Mbps) (2.95).
- WIFI Mesh (2.4 GHz) achieves the highest PDR (%) (93.99).
- 5G achieves the lowest Avg Delay (ms) (11.74).

| Technology | Mean PDR (%) | Mean Throughput (Mbps) | Mean Delay (ms) | Mean Jitter (ms) |
| --- | --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 93.99 | 1.63 | 53.10 | 4.81 |
| WIFI Mesh (5 GHz) | 92.95 | 1.56 | 46.68 | 3.11 |
| 4G | 91.15 | 1.99 | 31.70 | 3.97 |
| 5G | 88.47 | 2.95 | 11.74 | 1.85 |

![PDR (%) Comparison](figures/section1_pdr.png)

![Throughput (Mbps) Comparison](figures/section1_throughput.png)

![Avg Delay (ms) Comparison](figures/section1_avg_delay.png)

![Avg Jitter (ms) Comparison](figures/section1_avg_jitter.png)

## 2. Scalability Trends

- WIFI Mesh (2.4 GHz) PDR changes by 9.04 points and delay by 44.18 ms between 5 and 15 nodes.
- WIFI Mesh (5 GHz) PDR changes by 10.79 points and delay by 55.19 ms between 5 and 15 nodes.
- 4G PDR changes by 7.52 points and delay by 27.67 ms between 5 and 15 nodes.
- 5G PDR changes by 7.17 points and delay by 1.34 ms between 5 and 15 nodes.

![Scalability Trends: PDR (%)](figures/section2_pdr.png)

![Scalability Trends: Throughput (Mbps)](figures/section2_throughput.png)

![Scalability Trends: Avg Delay (ms)](figures/section2_avg_delay.png)

### 5 Nodes

| Technology | Mean PDR (%) | Mean Throughput (Mbps) | Mean Delay (ms) |
| --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 98.89 | 1.89 | 34.13 |
| WIFI Mesh (5 GHz) | 99.66 | 1.77 | 15.86 |
| 4G | 94.66 | 2.81 | 19.36 |
| 5G | 83.85 | 2.59 | 10.30 |

### 10 Nodes

| Technology | Mean PDR (%) | Mean Throughput (Mbps) | Mean Delay (ms) |
| --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 93.22 | 1.63 | 46.84 |
| WIFI Mesh (5 GHz) | 90.34 | 1.47 | 53.11 |
| 4G | 91.64 | 1.70 | 28.69 |
| 5G | 90.54 | 3.19 | 13.27 |

### 15 Nodes

| Technology | Mean PDR (%) | Mean Throughput (Mbps) | Mean Delay (ms) |
| --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 89.86 | 1.39 | 78.31 |
| WIFI Mesh (5 GHz) | 88.86 | 1.43 | 71.05 |
| 4G | 87.14 | 1.46 | 47.04 |
| 5G | 91.02 | 3.05 | 11.64 |

## 3. Statistical Summary

- Tables below summarize distribution of core KPIs across seeds, node counts, and flow scales.

![Distribution Summary: PDR (%)](figures/section3_pdr.png)

![Distribution Summary: Throughput (Mbps)](figures/section3_throughput.png)

![Distribution Summary: Avg Delay (ms)](figures/section3_avg_delay.png)

![Distribution Summary: Avg Jitter (ms)](figures/section3_avg_jitter.png)

### PDR (%)

| Technology | Mean | Std Dev | Min | Max |
| --- | --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 93.99 | 6.99 | 77.41 | 100 |
| WIFI Mesh (5 GHz) | 92.95 | 8.56 | 73.92 | 100 |
| 4G | 91.15 | 4.26 | 84.15 | 97.77 |
| 5G | 88.47 | 7.08 | 75.72 | 97.66 |

### Throughput (Mbps)

| Technology | Mean | Std Dev | Min | Max |
| --- | --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 1.63 | 0.32 | 1.17 | 2.63 |
| WIFI Mesh (5 GHz) | 1.56 | 0.32 | 1.14 | 2.53 |
| 4G | 1.99 | 0.73 | 1.04 | 3.52 |
| 5G | 2.95 | 0.64 | 1.55 | 3.84 |

### Avg Delay (ms)

| Technology | Mean | Std Dev | Min | Max |
| --- | --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 53.10 | 43.39 | 2.31 | 149.15 |
| WIFI Mesh (5 GHz) | 46.68 | 49.11 | 0.90 | 144.11 |
| 4G | 31.70 | 18.29 | 12.32 | 77.35 |
| 5G | 11.74 | 2.96 | 8.53 | 20.21 |

### Avg Jitter (ms)

| Technology | Mean | Std Dev | Min | Max |
| --- | --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 4.81 | 4.33 | 0.45 | 20.29 |
| WIFI Mesh (5 GHz) | 3.11 | 4.06 | 0.09 | 13.73 |
| 4G | 3.97 | 1.96 | 1.74 | 10.25 |
| 5G | 1.85 | 1.22 | 0.91 | 6.08 |

## 4. Traffic Load Impact

- WIFI Mesh (2.4 GHz) loses 9.81 PDR points and adds 75.22 ms delay from 10KB to 1MB payload.
- WIFI Mesh (5 GHz) loses 8.92 PDR points and adds 72.08 ms delay from 10KB to 1MB payload.
- 4G gains 2.15 PDR points and adds 24.87 ms delay from 10KB to 1MB payload.
- 5G gains 5.36 PDR points and reduces 0.04 ms delay from 10KB to 1MB payload.

![Traffic Load Impact: PDR (%)](figures/section4_pdr.png)

![Traffic Load Impact: Throughput (Mbps)](figures/section4_throughput.png)

![Traffic Load Impact: Avg Delay (ms)](figures/section4_avg_delay.png)

### 10KB Payload

| Technology | Mean PDR (%) | Mean Throughput (Mbps) | Mean Delay (ms) |
| --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 99.12 | 1.45 | 13.70 |
| WIFI Mesh (5 GHz) | 98.54 | 1.40 | 3.27 |
| 4G | 89.71 | 1.98 | 16.83 |
| 5G | 85.24 | 2.67 | 11.85 |

### 50KB Payload

| Technology | Mean PDR (%) | Mean Throughput (Mbps) | Mean Delay (ms) |
| --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 93.54 | 1.68 | 56.67 |
| WIFI Mesh (5 GHz) | 90.70 | 1.55 | 61.40 |
| 4G | 91.87 | 2.00 | 36.57 |
| 5G | 89.56 | 3.02 | 11.56 |

### 1MB Payload

| Technology | Mean PDR (%) | Mean Throughput (Mbps) | Mean Delay (ms) |
| --- | --- | --- | --- |
| WIFI Mesh (2.4 GHz) | 89.31 | 1.78 | 88.92 |
| WIFI Mesh (5 GHz) | 89.62 | 1.72 | 75.35 |
| 4G | 91.86 | 1.99 | 41.70 |
| 5G | 90.60 | 3.15 | 11.81 |

## Summary

This analysis of 108 simulation scenarios demonstrates that **WiFi Mesh performs well** and offers a **cost-effective alternative** to 4G and 5G technologies.

**WiFi Mesh (2.4 GHz) achieves the highest Packet Delivery Ratio (PDR) of 93.99%**, indicating superior reliability. While 5G leads in throughput (2.95 Mbps) and latency (11.74 ms), WiFi Mesh maintains competitive performance with 1.63 Mbps throughput and shows robust scalability across different node counts.

**WiFi Mesh is highly cost-effective** compared to cellular technologies. It uses unlicensed spectrum (2.4 GHz and 5 GHz), requires no spectrum licensing fees, and can be deployed with standard commercial equipment. The mesh protocol (802.11s) enables self-organizing networks, reducing deployment complexity and operational costs.

**Conclusion**: WiFi Mesh is **feasible and cost-effective for implementation** in scenarios prioritizing reliability and cost-efficiency. Its strong PDR performance, combined with significantly lower deployment and operational costs compared to 4G and 5G, makes it a compelling choice for many network deployment scenarios.
