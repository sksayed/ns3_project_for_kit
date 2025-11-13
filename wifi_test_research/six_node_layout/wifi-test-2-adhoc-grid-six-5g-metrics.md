# FlowMonitor STA Metrics (5G Hotspot)

## East Direction (positive X from mesh AP)

| Distance (m) | STA IP | Protocol | PDR (%) | Avg Delay (ms) | Throughput (Mbps) | TX Packets | RX Packets | Lost Packets | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 192.168.1.1 | TCP/UDP | 100.00 | 0.13 | 0.9509 | 752 | 752 | 0 | Stable |
| 40 | 192.168.1.1 | TCP/UDP | 100.00 | 0.13 | 0.9509 | 752 | 752 | 0 | Stable |
| 60 | 192.168.1.1 | TCP/UDP | 100.00 | 0.14 | 0.9509 | 752 | 752 | 0 | Stable |
| 80 | 192.168.1.1 | TCP/UDP | 100.00 | 0.14 | 0.9509 | 752 | 752 | 0 | Stable |
| 100 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 120 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 140 | 192.168.1.1 | TCP/UDP | 100.00 | 0.17 | 0.9509 | 752 | 752 | 0 | Stable |
| 160 | 192.168.1.1 | TCP/UDP | 100.00 | 0.17 | 0.9509 | 752 | 752 | 0 | Stable |
| 180 | 192.168.1.1 | TCP/UDP | 100.00 | 0.17 | 0.9509 | 752 | 752 | 0 | Stable |
| 200 | 192.168.1.1 | UDP | 100.00 | 0.22 | 1.5320 | 749 | 749 | 0 | TCP downlink starves (repeated disassoc before 10 s) |
| 220 | - | No data | 0.00 | N/A | 0.0000 | 0 | 0 | - | STA never re-associated |

## North Direction (positive Y from mesh AP)

| Distance (m) | STA IP | Protocol | PDR (%) | Avg Delay (ms) | Throughput (Mbps) | TX Packets | RX Packets | Lost Packets | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 180 | 192.168.1.1 | TCP/UDP | 100.00 | 0.17 | 0.9509 | 752 | 752 | 0 | Stable |
| 190 | 192.168.1.1 | TCP/UDP | 100.00 | 0.17 | 0.9509 | 752 | 752 | 0 | Stable |
| 200 | 192.168.1.1 | TCP/UDP | 100.00 | 0.17 | 0.9509 | 752 | 752 | 0 | Stable |
| 210 | 192.168.1.1 | UDP | 100.00 | 0.22 | 1.5320 | 749 | 749 | 0 | Repeated disassoc until ~23 s; TCP flows dropped |
| 220 | - | No data | 0.00 | N/A | 0.0000 | 0 | 0 | - | STA never re-associated |

## West Direction (negative X from mesh AP)

| Distance (m) | STA IP | Protocol | PDR (%) | Avg Delay (ms) | Throughput (Mbps) | TX Packets | RX Packets | Lost Packets | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 180 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 240 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 300 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 380 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 420 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable (farthest tested, no drop) |

## South Direction (negative Y from mesh AP)

| Distance (m) | STA IP | Protocol | PDR (%) | Avg Delay (ms) | Throughput (Mbps) | TX Packets | RX Packets | Lost Packets | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 180 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 200 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 240 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 260 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable |
| 320 | 192.168.1.1 | TCP/UDP | 100.00 | 0.15 | 0.9509 | 752 | 752 | 0 | Stable (farthest tested) |

> All tests used `--hotspotBand=5g` with STA height 5 m. TCP downlink refers to the OnOff download flow from internet server to STA; when “UDP” appears it indicates only the uplink VoIP/UDP remained active because the TCP download could not sustain connections.


