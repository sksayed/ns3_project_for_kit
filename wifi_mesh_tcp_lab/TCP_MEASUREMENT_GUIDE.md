# TCP Data Transfer Measurement in NS-3

This guide explains how TCP data transfer from one node to another is calculated and measured in ns-3 simulations.

---

## 📊 Overview: Three Measurement Layers

TCP data transfer is measured at three different layers:

1. **Application Layer** (PacketSink)
2. **Flow Layer** (FlowMonitor)
3. **Packet Layer** (PCAP/ASCII traces)

---

## 1️⃣ Application Layer Measurement

### Using PacketSink

```cpp
// Server side (receiver)
PacketSinkHelper tcpServer("ns3::TcpSocketFactory",
                          InetSocketAddress(Ipv4Address::GetAny(), tcpPort));
ApplicationContainer tcpServerApp = tcpServer.Install(receiverNode);

// After simulation
Ptr<PacketSink> sink = DynamicCast<PacketSink>(tcpServerApp.Get(0));
uint64_t totalRx = sink->GetTotalRx();  // Total bytes received at application
```

**What it measures:**
- **Total application-layer data received**
- Does NOT include TCP/IP headers
- Only counts successfully delivered data
- This is the "useful" data received

**Calculation:**
```
Total Received Bytes = sum(all TCP payload data successfully delivered to app)
```

---

## 2️⃣ Flow Layer Measurement (FlowMonitor)

### The Complete Picture

```cpp
FlowMonitorHelper flowmon;
Ptr<FlowMonitor> monitor = flowmon.Install(allNodes);

// After simulation
monitor->CheckForLostPackets();
std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats();

for (auto& flow : stats) {
    std::cout << "Tx Packets: " << flow.second.txPackets << std::endl;
    std::cout << "Rx Packets: " << flow.second.rxPackets << std::endl;
    std::cout << "Tx Bytes: " << flow.second.txBytes << std::endl;
    std::cout << "Rx Bytes: " << flow.second.rxBytes << std::endl;
    std::cout << "Lost Packets: " << flow.second.lostPackets << std::endl;
    
    // Calculate throughput
    double throughputMbps = flow.second.rxBytes * 8.0 / simTime / 1000000;
    std::cout << "Throughput: " << throughputMbps << " Mbps" << std::endl;
}
```

### Key FlowMonitor Metrics:

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **txBytes** | Bytes transmitted | Includes IP headers, TCP headers, and payload |
| **rxBytes** | Bytes received | Successfully received bytes at destination |
| **txPackets** | Packets transmitted | Total packets sent |
| **rxPackets** | Packets received | Successfully received packets |
| **lostPackets** | Lost packets | `txPackets - rxPackets` |
| **delaySum** | Total delay | Sum of all packet delays |
| **jitterSum** | Total jitter | Sum of delay variations |

### Throughput Calculation:

```cpp
// Formula 1: Average throughput
Throughput (bits/sec) = (rxBytes × 8) / simulationTime

// Formula 2: In Mbps
Throughput (Mbps) = (rxBytes × 8) / (simulationTime × 1,000,000)

// Formula 3: Goodput (application layer only)
Goodput (Mbps) = (PacketSink::GetTotalRx() × 8) / (simulationTime × 1,000,000)
```

**Example:**
```
rxBytes = 950,000 bytes
simTime = 10 seconds
Throughput = (950,000 × 8) / (10 × 1,000,000) = 0.76 Mbps
```

---

## 3️⃣ Packet Layer Measurement (Traces)

### ASCII Trace Analysis

Your `analyze_traces.py` script parses trace files to extract:

```python
# From ASCII trace files
record = {
    'event': 't' or 'r',        # transmit or receive
    'time_s': float,            # timestamp in seconds
    'rate': 'OfdmRate54Mbps',  # PHY rate
    'length': int,              # packet length in bytes
    'src': '10.1.1.1',         # source IP
    'dst': '10.1.1.2',         # destination IP
    'protocol': 'TCP',         # TCP/UDP/IP
    'src_port': 7000,          # source port
    'dst_port': 49153,         # destination port
}
```

### PCAP Analysis

PCAP files can be analyzed with Wireshark or `analyze_pcap_tcp_paths.py`:

```python
# From PCAP using Scapy
packet = rdpcap('trace.pcap')
for pkt in packet:
    if TCP in pkt:
        bytes_transferred = len(pkt[TCP].payload)
        seq_num = pkt[TCP].seq
        ack_num = pkt[TCP].ack
```

---

## 🎯 Complete TCP Data Transfer Calculation

### Step-by-Step Process:

#### 1. **Sender Side (BulkSend Application)**

```cpp
BulkSendHelper tcpClient("ns3::TcpSocketFactory", remoteAddress);
tcpClient.SetAttribute("MaxBytes", UintegerValue(1000000)); // Send 1MB
```

**What happens:**
- Application tries to send 1,000,000 bytes
- TCP breaks it into segments (typically 1448 bytes per segment = MTU 1500 - IP header 20 - TCP header 32)
- Each segment gets TCP header (20-32 bytes) + IP header (20 bytes)

#### 2. **Network Transmission**

```
Segments needed = 1,000,000 / 1,448 ≈ 691 segments

Per segment overhead:
- TCP header: ~32 bytes (with options)
- IP header: 20 bytes
- WiFi header: ~24-30 bytes
- Total overhead per segment: ~76-82 bytes

Total bytes on wire = (1,448 + 82) × 691 ≈ 1,057,330 bytes
```

#### 3. **Receiver Side Calculation**

```cpp
// Application layer
Ptr<PacketSink> sink = DynamicCast<PacketSink>(serverApp.Get(0));
uint64_t appBytes = sink->GetTotalRx();  // ≈ 1,000,000 bytes (payload only)

// Network layer (FlowMonitor)
FlowMonitor::FlowStats stats = monitor->GetFlowStats()[flowId];
uint64_t networkBytes = stats.rxBytes;   // ≈ 1,057,330 bytes (with headers)
```

#### 4. **Efficiency Calculation**

```cpp
// Protocol efficiency
double efficiency = (double)appBytes / networkBytes;
// efficiency ≈ 1,000,000 / 1,057,330 ≈ 94.6%

// Throughput
double throughput = (networkBytes * 8.0) / simTime / 1e6;  // Mbps
double goodput = (appBytes * 8.0) / simTime / 1e6;         // Mbps (payload only)
```

---

## 📈 Key Formulas Summary

### Basic Metrics:

```
Packet Delivery Ratio (PDR) = rxPackets / txPackets × 100%

Packet Loss Rate = lostPackets / txPackets × 100%

Average Delay = delaySum / rxPackets (seconds)

Average Throughput = rxBytes × 8 / simulationTime (bits/sec)

Goodput = ApplicationBytes × 8 / simulationTime (bits/sec)

Protocol Overhead = (networkBytes - appBytes) / networkBytes × 100%
```

### Advanced Metrics:

```
Retransmission Rate = (txPackets - uniquePackets) / txPackets × 100%

Bandwidth Utilization = actualThroughput / channelCapacity × 100%

End-to-End Delay = receiveTime - sendTime

Jitter = |delay[i] - delay[i-1]|
```

---

## 🔍 Example from Your Simulation

### Scenario: Sayed sends 1MB to Sadia

```
Configuration:
- BulkSend: MaxBytes = 1,000,000
- Simulation time: 10 seconds
- Network: WiFi 802.11g (54 Mbps)

Expected Results:
┌─────────────────────────────────────────────┐
│ Application Layer (PacketSink)              │
│   Total Received: ~1,000,000 bytes          │
│   Goodput: 0.8 Mbps                         │
├─────────────────────────────────────────────┤
│ Network Layer (FlowMonitor)                 │
│   Tx Packets: ~700 packets                  │
│   Rx Packets: ~700 packets                  │
│   Tx Bytes: ~1,057,000 bytes (with headers) │
│   Rx Bytes: ~1,057,000 bytes                │
│   Throughput: 0.85 Mbps                     │
│   Packet Loss: 0-2%                         │
├─────────────────────────────────────────────┤
│ Link Layer (Traces)                         │
│   Total transmissions: ~750 (with retries)  │
│   WiFi retransmissions: ~50 packets         │
│   Average rate: OfdmRate54Mbps              │
└─────────────────────────────────────────────┘
```

---

## 🛠️ Practical Tips

### 1. Use Multiple Measurement Methods

```cpp
// Always combine these three:
Ptr<PacketSink> sink;           // Application-level
FlowMonitor monitor;            // Network-level
EnableAsciiAll() / EnablePcap() // Packet-level
```

### 2. Check Consistency

```cpp
// Sanity check
assert(sink->GetTotalRx() <= flowStats.rxBytes);  // App bytes < network bytes
assert(flowStats.rxPackets <= flowStats.txPackets); // Received ≤ transmitted
```

### 3. Account for TCP Overhead

```cpp
// Expected overhead
double expectedOverhead = appBytes * 0.05;  // ~5% for TCP/IP headers
double actualOverhead = flowStats.rxBytes - sink->GetTotalRx();
```

---

## 📚 References

- **ns-3 FlowMonitor Documentation**: https://www.nsnam.org/docs/models/html/flow-monitor.html
- **TCP in ns-3**: https://www.nsnam.org/docs/models/html/tcp.html
- **Trace System**: https://www.nsnam.org/docs/tutorial/html/tracing.html

---

## 🎓 Summary

**How TCP data is calculated:**

1. **Application sends** X bytes → BulkSendApplication
2. **TCP segments** data → adds headers, creates packets
3. **IP routes** packets → adds IP headers
4. **WiFi transmits** → adds WiFi headers + possible retransmissions
5. **Receiver gets** Y bytes (Y ≥ X due to overhead)
6. **FlowMonitor tracks** all bytes on the wire
7. **PacketSink reports** application payload only

**Key equation:**
```
Network Bytes (FlowMonitor) = Application Bytes (PacketSink) + Protocol Overhead
```

