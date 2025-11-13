## Mesh AP Range Findings

### Overview
- Scenario: single mesh AP (node 0) with one STA client, 802.11n @ 2.4 GHz backhaul and hotspot.
- Traffic: UDP VoIP (BulkSend/OnOff mix) from STA to external server; 30 s simulation time.
- FlowMonitor used to confirm throughput, delay, and packet loss.

### Baseline
- STA anchored 20 m east (`Vector(170, 0 , 5)`) – throughput ≈ 1.53 Mb/s, delay ≈ 0.185 ms, 0 % loss.

### Range by Direction
| Direction | Max reliable distance | Notes |
|-----------|-----------------------|-------|
| East | ≥ 190 m | Stable traffic out to 190 m; no obstacles in path. |
| South | ≥ 190 m | Same as east; clear LOS, zero loss. |
| West | ≥ 190 m | Stable despite `Cluster50` building nearby; minimal delay variation. |
| North | ≈ 170 m | 170 m: solid link. 190 m: repeated disassociations, 100 % loss. Likely due to pure path loss. |

### Building Impact
#### Left Below (0–60 x, 96–104 y, 0–10 z)
- STA positions tested: in front (30 , 90), inside (30 , 100), just behind (30 , 110), 30 m behind (30 , 130) – all at z = 5 m.
- Findings: throughput constant (~1.53 Mb/s); only “just behind” case saw delay rise to ~0.24 ms (still 0 % loss).

#### Cluster50 (255–335 x, 20–28 y, 0–18 z)
- STA positions: south (295 , 10), inside (295 , 24), north (295 , 38) – all at z = 5 m.
- Findings: throughput unchanged, delays ~0.185 ms, 0 % loss even inside the building.

### Radius Summary
- Practical coverage radius ≈ 170 m in all directions (guaranteed).
- Up to ≈ 190 m achievable in east/south/west directions with current PHY settings.
- Buildings tested (Left Below, Cluster50) do not materially degrade throughput or PDR at these distances.

### Recommendations
- Treat 170 m as conservative design radius; plan for possible extension to 190 m where obstructions are minimal.
- For northbound coverage beyond 170 m consider higher Tx power, antenna gain, or additional mesh nodes.

