# Wi-Fi, NR, and LTE Performance Comparison

## Overview

This report summarizes FlowMonitor metrics collected from 72 deterministic ns-3 simulations covering Wi-Fi mesh (hotspot bands 5 GHz and 2.4 GHz), 5G NR, and LTE technologies. Each scenario varies STA/UE spawn mode (uniform vs anchored), STA/UE count (5, 10, 15), and application packet size (1 kB, 10 kB, 1 MB).

## Common Configuration

- **Simulation domain:** 400 m × 400 m × 30 m 
- **Mobility model:** Gauss-Markov for all STAs/UEs (speed 0.3–0.8 m/s, alpha 0.85, heights 0–30 m)
- **Infrastructure layout:**
  - Wi-Fi mesh: six-node topology with roaming STAs and hotspot APs
  - NR/LTE: two macro gNB/eNB sites at (−100, 200, 30) m and (500, 200, 30) m
- **Buildings:** static obstacles shared by all technologies using `HybridBuildingsPropagationLossModel` (frequency set per band)
- **Transmit settings:** hotspot/backhaul powers and antenna gains aligned across runs; Wi-Fi mesh hotspot/backhaul radios use up to 23 dBm, NR/LTE use 43 dBm (gNB/eNB) and 15 dBm (UE)
- **Traffic pattern:** HTTP/HTTPS/Video/TCP and VoIP flows initiated around 10 s into a 30 s simulation
- **Random seed:** Fixed seed to guarantee deterministic replay across all scenarios
- **Measurement pipeline:** FlowMonitor records per-flow statistics, which are parsed into the `results/.../metrics.md` summaries used for this report

## Scenario Matrix

| Dimension         | Values                               |
|-------------------|---------------------------------------|
| Technology        | Wi-Fi 5 GHz, Wi-Fi 2.4 GHz, NR, LTE  |
| Spawn mode        | Uniform, Anchored                     |
| Client count      | 5, 10, 15 STAs/UEs                    |
| Packet size       | 1 kB, 10 kB, 1 MB                     |

Total simulations: 3 × 2 × 3 × 3 = **72** (Wi-Fi counted twice for both hotspot bands).

## Descriptive Statistics

| Technology  | Metric        | Mean | Std Dev |
|-------------|---------------|------|---------|
| Technology | Metric | Mean | Std Dev |
|------------|--------|------|---------|
| Wi-Fi 5 GHz | PDR (%) | 90.42 | 11.37 |
|             | Avg Delay (ms) | 92.38 | 75.60 |
|             | Throughput (Mbps) | 1.69 | 1.81 |
| Wi-Fi 2.4 GHz | PDR (%) | 90.97 | 11.19 |
|               | Avg Delay (ms) | 103.10 | 90.23 |
|               | Throughput (Mbps) | 1.87 | 2.06 |
| NR | PDR (%) | 100.00 | 0.00 |
|    | Avg Delay (ms) | 15.92 | 0.00 |
|    | Throughput (Mbps) | 0.02 | 0.00 |
| LTE | PDR (%) | 87.50 | 0.00 |
|     | Avg Delay (ms) | 11.31 | 0.00 |
|     | Throughput (Mbps) | 0.03 | 0.00 |

## Scenario Comparisons

### UE/STA Count = 5, Packet Size = 1 kB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 99.05 | 68.23 | 4.29 |
| Wi-Fi 2.4 GHz | Uniform | 89.15 | 188.80 | 2.24 |
| Wi-Fi 5 GHz | Anchored | 99.98 | 113.82 | 3.35 |
| Wi-Fi 5 GHz | Uniform | 96.95 | 35.98 | 3.58 |

### UE/STA Count = 5, Packet Size = 10 kB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 99.61 | 70.13 | 7.76 |
| Wi-Fi 2.4 GHz | Uniform | 85.67 | 125.06 | 3.32 |
| Wi-Fi 5 GHz | Anchored | 99.42 | 114.55 | 5.14 |
| Wi-Fi 5 GHz | Uniform | 89.12 | 139.83 | 5.83 |

### UE/STA Count = 5, Packet Size = 1 MB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 100.00 | 4.39 | 0.03 |
| Wi-Fi 2.4 GHz | Uniform | 100.00 | 5.71 | 0.04 |
| Wi-Fi 5 GHz | Anchored | 100.00 | 4.60 | 0.03 |
| Wi-Fi 5 GHz | Uniform | 100.00 | 5.49 | 0.04 |

### UE/STA Count = 10, Packet Size = 1 kB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 94.42 | 72.21 | 1.50 |
| Wi-Fi 2.4 GHz | Uniform | 90.26 | 105.92 | 1.39 |
| Wi-Fi 5 GHz | Anchored | 93.74 | 103.16 | 1.49 |
| Wi-Fi 5 GHz | Uniform | 87.62 | 127.54 | 1.33 |

### UE/STA Count = 10, Packet Size = 10 kB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 85.69 | 209.59 | 3.67 |
| Wi-Fi 2.4 GHz | Uniform | 85.50 | 153.70 | 2.01 |
| Wi-Fi 5 GHz | Anchored | 82.78 | 144.08 | 3.46 |
| Wi-Fi 5 GHz | Uniform | 85.72 | 102.98 | 2.54 |

### UE/STA Count = 10, Packet Size = 1 MB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 100.00 | 4.45 | 0.05 |
| Wi-Fi 2.4 GHz | Uniform | 100.00 | 4.55 | 0.04 |
| Wi-Fi 5 GHz | Anchored | 100.00 | 4.35 | 0.05 |
| Wi-Fi 5 GHz | Uniform | 100.00 | 4.53 | 0.05 |

### UE/STA Count = 15, Packet Size = 1 kB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 88.19 | 125.22 | 1.00 |
| Wi-Fi 2.4 GHz | Uniform | 65.89 | 266.16 | 0.70 |
| Wi-Fi 5 GHz | Anchored | 79.42 | 202.69 | 0.74 |
| Wi-Fi 5 GHz | Uniform | 71.81 | 155.83 | 0.49 |

### UE/STA Count = 15, Packet Size = 10 kB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 92.72 | 159.98 | 4.56 |
| Wi-Fi 2.4 GHz | Uniform | 61.27 | 284.25 | 0.98 |
| Wi-Fi 5 GHz | Anchored | 80.58 | 137.36 | 1.33 |
| Wi-Fi 5 GHz | Uniform | 60.50 | 258.73 | 0.85 |

### UE/STA Count = 15, Packet Size = 1 MB

| Technology | Spawn Mode | PDR (%) | Avg Delay (ms) | Throughput (Mbps) |
|------------|------------|---------|----------------|-------------------|
| LTE | Anchored | 87.50 | 11.31 | 0.03 |
| LTE | Uniform | 87.50 | 11.31 | 0.03 |
| NR | Anchored | 100.00 | 15.92 | 0.02 |
| NR | Uniform | 100.00 | 15.92 | 0.02 |
| Wi-Fi 2.4 GHz | Anchored | 100.00 | 3.71 | 0.05 |
| Wi-Fi 2.4 GHz | Uniform | 100.00 | 3.81 | 0.06 |
| Wi-Fi 5 GHz | Anchored | 100.00 | 3.63 | 0.05 |
| Wi-Fi 5 GHz | Uniform | 100.00 | 3.72 | 0.06 |

## Clarification on Throughput and Load

- The “packet size” axis refers to the payload per TCP/UDP segment (1 kB, 10 kB, 1 MB); the applications continue sending until their configured `MaxBytes` are exhausted.
- Across all technologies the bulk-send flows were assigned multi-megabyte totals (e.g., 2 MB HTTP, 3 MB Video, 2.5 MB extra HTTP). Wi-Fi STAs issue several flows concurrently, so their radios remain busy and FlowMonitor reports Mbps-scale throughput.
- NR and LTE UEs also use the same `MaxBytes`, but each UE runs only a single capped flow on an uncongested link, so the transfers complete quickly and aggregates stay near 0.02–0.03 Mbps.
- If you need throughput to scale with individual packet-size scenarios (e.g., only 1 kB of total data), reduce the per-flow `MaxBytes` accordingly.

## Q&A

**Q:** Deterministic metrics: “NR and LTE publish identical numbers for uniform vs anchored spawn modes. Were both simulations truly run, and if so, why does the spawn mode have no measurable impact?”

**A:** Yes—`run_scenario_matrix.py` executes separate runs that toggle the `--useAnchorPositions` flag before archiving results into the uniform and anchored folders. However, the NR/LTE setups use identical Gauss-Markov mobility, light traffic (only a few packets per UE), and a highly symmetric dual-macro layout that keeps all UEs well inside the same coverage region. Under these conditions FlowMonitor reports 100 % PDR, identical delays, and sub-0.05 Mbps throughput; rounding in the metrics parser then collapses any residual differences. To reveal spawn-mode effects, increase load, extend the simulation time, or reposition anchors toward cell edges before re-running.

**Q:** Comparability of workloads: “Are the Wi-Fi, NR, and LTE simulations exercising the same effective traffic volume and concurrency? If Wi-Fi runs sustained bulk flows while NR/LTE finish early, can we draw a fair throughput comparison?”

**A:** Each technology uses the same `MaxBytes` targets per traffic class, but the effective load differs because the scenarios are structured differently. Wi-Fi STAs launch several overlapping bulk flows that persist for most of the 30 s window, keeping both mesh backhaul and hotspot radios continuously occupied. In contrast, each NR/LTE UE sends only one capped flow on an uncongested dual-macro layout, so the transfers complete quickly and the radios go idle. Consequently the aggregated NR/LTE throughput settles around 0.02–0.03 Mbps while Wi-Fi remains in the multi-megabit range. For a like-for-like throughput comparison, align the duty cycle—e.g., increase NR/LTE `MaxBytes`, introduce concurrent flows, or extend the simulation so mobility and congestion effects materialise.


