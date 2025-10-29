
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mesh-module.h"
#include "ns3/internet-module.h"
#include "ns3/csma-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/buildings-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/ipv4-flow-classifier.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/ipv4-list-routing-helper.h"

#include <set>
#include <fstream>
#include <sstream>
#include <iomanip>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TcpMeshBackhaulMode");

// ========== MESH AP CONFIGURATION STRUCTURE ==========
// Real-world mesh AP configurations based on actual hardware specs
struct MeshAPConfig {
    std::string name;                    // Device name
    std::string description;             // Use case description
    
    // Physical layer parameters
    double txPowerStart;                 // TX power start (dBm)
    double txPowerEnd;                   // TX power end (dBm)
    double rxSensitivity;                // RX sensitivity (dBm)
    double rxGain;                       // RX gain (dB)
    double txGain;                       // TX gain (dB)
    
    // WiFi configuration
    std::string wifiStandard;            // WiFi standard (e.g., "WIFI_STANDARD_80211ac")
    std::string dataMode;                // Data mode (e.g., "VhtMcs8")
    uint32_t numInterfaces;              // Number of mesh interfaces
    
    // Topology parameters
    double meshRange;                    // Expected mesh range (m)
    double apHeight;                     // AP height (m)
    double apSpacing;                    // Recommended AP spacing (m)
    uint32_t gridSize;                   // Calculated grid size for 400m field
    
    // Constructor for easy initialization
    MeshAPConfig(std::string n, std::string desc, double txStart, double txEnd,
                 double rxSens, double rxG, double txG, std::string standard,
                 std::string mode, uint32_t interfaces, double range, 
                 double height, double spacing, uint32_t grid)
        : name(n), description(desc), txPowerStart(txStart), txPowerEnd(txEnd),
          rxSensitivity(rxSens), rxGain(rxG), txGain(txG), 
          wifiStandard(standard), dataMode(mode), numInterfaces(interfaces),
          meshRange(range), apHeight(height), apSpacing(spacing), gridSize(grid) {}
};

// Helper function to convert string WiFi standard to enum
WifiStandard GetWifiStandardFromString(const std::string& standardStr) {
    if (standardStr == "WIFI_STANDARD_80211ac") return WIFI_STANDARD_80211ac;
    if (standardStr == "WIFI_STANDARD_80211ax") return WIFI_STANDARD_80211ax;
    if (standardStr == "WIFI_STANDARD_80211n") return WIFI_STANDARD_80211n;
    if (standardStr == "WIFI_STANDARD_80211a") return WIFI_STANDARD_80211a;
    if (standardStr == "WIFI_STANDARD_80211g") return WIFI_STANDARD_80211g;
    if (standardStr == "WIFI_STANDARD_80211b") return WIFI_STANDARD_80211b;
    return WIFI_STANDARD_80211n;  // Default fallback
}

// Factory function to get mesh configuration by ID
MeshAPConfig GetMeshConfig(uint32_t configId) {
    switch(configId) {
        case 1:
            // TP-Link EAP225-Outdoor: Long-range outdoor mesh
            // 802.11ac, high power, external antennas
            return MeshAPConfig(
                "TP-Link EAP225-Outdoor",
                "Long-range outdoor (FULL 400m 3D coverage)",
                27.0,                           // txPowerStart (dBm)
                27.0,                           // txPowerEnd (dBm)
                -96.0,                          // rxSensitivity (dBm)
                3.0,                            // rxGain (dB)
                3.0,                            // txGain (dB)
                "WIFI_STANDARD_80211ac",        // WiFi standard
                "VhtMcs8",                      // Data mode (802.11ac VHT MCS8)
                2,                              // numInterfaces
                200.0,                          // meshRange (m)
                15.0,                           // apHeight (m) - outdoor pole mount
                140.0,                          // apSpacing (m) - UPDATED for 400m coverage
                4                               // gridSize (4x4 = 16 APs) - UPDATED
            );
            // Coverage: (4-1) × 140 = 420m × 420m ✅
            // 3D distance: √(140² + 15²) = 140.8m < 200m ✅
        
        case 2:
            // Netgear Orbi 960: High-end indoor mesh (WiFi 6E)
            // 802.11ax, quad-band, optimized for home/indoor
            return MeshAPConfig(
                "Netgear Orbi 960 (WiFi 6E)",
                "High-end indoor mesh (FULL 400m 3D coverage)",
                20.0,                           // txPowerStart (dBm)
                20.0,                           // txPowerEnd (dBm)
                -85.0,                          // rxSensitivity (dBm)
                0.0,                            // rxGain (dB) - internal antennas
                0.0,                            // txGain (dB)
                "WIFI_STANDARD_80211ax",        // WiFi standard
                "HeMcs11",                      // Data mode (802.11ax HE MCS11)
                4,                              // numInterfaces (quad-band)
                50.0,                           // meshRange (m)
                15.0,                           // apHeight (m) - UPDATED for 3D coverage
                33.0,                           // apSpacing (m) - UPDATED for 400m coverage
                13                              // gridSize (13x13 = 169 APs) - UPDATED
            );
            // Coverage: (13-1) × 33 = 396m × 396m ≈ 400m ✅
            // 3D distance: √(33² + 15²) = 36.3m < 50m ✅
        
        case 3:
            // ASUS ZenWiFi AX (XT8): Premium indoor mesh (WiFi 6)
            // 802.11ax, tri-band, balanced performance
            return MeshAPConfig(
                "ASUS ZenWiFi AX (XT8)",
                "Premium indoor mesh (FULL 400m 3D coverage)",
                20.0,                           // txPowerStart (dBm)
                20.0,                           // txPowerEnd (dBm)
                -82.0,                          // rxSensitivity (dBm)
                0.0,                            // rxGain (dB) - internal antennas
                0.0,                            // txGain (dB)
                "WIFI_STANDARD_80211ax",        // WiFi standard
                "HeMcs9",                       // Data mode (802.11ax HE MCS9)
                3,                              // numInterfaces (tri-band)
                60.0,                           // meshRange (m)
                15.0,                           // apHeight (m) - UPDATED for 3D coverage
                40.0,                           // apSpacing (m) - UPDATED for 400m coverage
                11                              // gridSize (11x11 = 121 APs) - UPDATED
            );
            // Coverage: (11-1) × 40 = 400m × 400m ✅
            // 3D distance: √(40² + 15²) = 42.7m < 60m ✅
        
        case 0:
        default:
            // Default: HIGH POWER configuration with TP-Link power levels
            // 27 dBm TX power + 3 dB antenna gains for better mesh connectivity
            return MeshAPConfig(
                "Default High Power Config",
                "High-power deployment (FULL 400m 3D coverage)",
                27.0,                           // txPowerStart (dBm) - BOOSTED from 23
                27.0,                           // txPowerEnd (dBm) - BOOSTED from 23
                -96.0,                          // rxSensitivity (dBm)
                3.0,                            // rxGain (dB) - ADDED antenna gain previously 0.0
                3.0,                            // txGain (dB) - ADDED antenna gain previously 0.0
                "WIFI_STANDARD_80211n",         // WiFi standard
                "HtMcs7",                       // Data mode (802.11n HT MCS7)
                1,                              // numInterfaces (keep at 1 to avoid channel conflicts)
                100.0,                          // meshRange (m)
                15.0,                           // apHeight (m) - UPDATED for 3D coverage
                80.0,                           // apSpacing (m) - UPDATED for 400m coverage
                6                               // gridSize (6x6 = 36 APs) - UPDATED
            );
            // Coverage: (6-1) × 80 = 400m × 400m ✅
            // 3D distance: √(80² + 15²) = 81.4m < 100m ✅
    }
}

// Global trace counters
uint32_t g_txPackets = 0;
uint32_t g_rxPackets = 0;

// Per-hop statistics tracking
// Flow identifier structure (renamed to avoid ns-3's FlowId conflict)
struct FlowIdentifier {
    Ipv4Address source;
    Ipv4Address destination;
    
    bool operator<(const FlowIdentifier& other) const {
        if (source.Get() < other.source.Get()) return true;
        if (source.Get() == other.source.Get() && destination.Get() < other.destination.Get()) return true;
        return false;
    }
    
    std::string ToString() const {
        std::ostringstream oss;
        oss << source << " → " << destination;
        return oss.str();
    }
};

// Per-hop metrics with protocol separation
struct HopMetrics {
    uint32_t apIndex;
    std::string apName;
    
    // TCP metrics
    uint32_t tcpPacketsIn = 0;
    uint32_t tcpPacketsOut = 0;
    uint32_t tcpDropped = 0;
    
    // UDP metrics
    uint32_t udpPacketsIn = 0;
    uint32_t udpPacketsOut = 0;
    uint32_t udpDropped = 0;
};

// Flow tracking structure
struct FlowTracking {
    FlowIdentifier flowId;
    std::string flowName;
    std::vector<uint32_t> route;
    std::map<uint32_t, HopMetrics> hopMetrics;
};

// Global container for all tracked flows
std::map<FlowIdentifier, FlowTracking> g_trackedFlows;

// TX Trace callback (for application-level tracking)
void TxTrace(Ptr<const Packet> p)
{
    g_txPackets++;
    NS_LOG_INFO("Tx packet: " << p->GetSize() << " bytes at " << Simulator::Now().GetSeconds());
}

// RX Trace callback (for application-level tracking)
void RxTrace(Ptr<const Packet> p, const Address& addr)
{
    g_rxPackets++;
    NS_LOG_INFO("Rx packet: " << p->GetSize() << " bytes at " << Simulator::Now().GetSeconds());
}

// IP Forward trace - tracks packets forwarded by mesh APs (Tx trace)
void IpForwardTrace(uint32_t nodeId, Ptr<const Packet> packet, Ptr<Ipv4> ipv4, uint32_t interface)
{
    // Extract header from packet
    Ipv4Header header;
    packet->PeekHeader(header);
    
    FlowIdentifier fid;
    fid.source = header.GetSource();
    fid.destination = header.GetDestination();
    
    // Check if this flow is being tracked
    if (g_trackedFlows.find(fid) != g_trackedFlows.end()) {
        // Only track if this AP is in the route
        if (g_trackedFlows[fid].hopMetrics.find(nodeId) != g_trackedFlows[fid].hopMetrics.end()) {
            if (header.GetProtocol() == 6) {  // TCP
                g_trackedFlows[fid].hopMetrics[nodeId].tcpPacketsOut++;
            } else if (header.GetProtocol() == 17) {  // UDP
                g_trackedFlows[fid].hopMetrics[nodeId].udpPacketsOut++;
            }
        }
    }
}

// IP RX trace - tracks packets received by mesh APs (LocalDeliver trace)
void IpRxTrace(uint32_t nodeId, const Ipv4Header& header, Ptr<const Packet> packet, uint32_t interface)
{
    FlowIdentifier fid;
    fid.source = header.GetSource();
    fid.destination = header.GetDestination();
    
    if (g_trackedFlows.find(fid) != g_trackedFlows.end()) {
        // Only track if this AP is in the route
        if (g_trackedFlows[fid].hopMetrics.find(nodeId) != g_trackedFlows[fid].hopMetrics.end()) {
            if (header.GetProtocol() == 6) {
                g_trackedFlows[fid].hopMetrics[nodeId].tcpPacketsIn++;
            } else if (header.GetProtocol() == 17) {
                g_trackedFlows[fid].hopMetrics[nodeId].udpPacketsIn++;
            }
        }
    }
}

// IP Drop trace - tracks packets dropped by mesh APs
void IpDropTrace(uint32_t nodeId, const Ipv4Header& header, Ptr<const Packet> packet, 
                 Ipv4L3Protocol::DropReason reason, Ptr<Ipv4> ipv4, uint32_t interface)
{
    FlowIdentifier fid;
    fid.source = header.GetSource();
    fid.destination = header.GetDestination();
    
    if (g_trackedFlows.find(fid) != g_trackedFlows.end()) {
        // Only track if this AP is in the route
        if (g_trackedFlows[fid].hopMetrics.find(nodeId) != g_trackedFlows[fid].hopMetrics.end()) {
            if (header.GetProtocol() == 6) {
                g_trackedFlows[fid].hopMetrics[nodeId].tcpDropped++;
            } else if (header.GetProtocol() == 17) {
                g_trackedFlows[fid].hopMetrics[nodeId].udpDropped++;
            }
        }
    }
}

// Setup Sayed to External Server traffic flow
void SetupSayedToServerFlow(
    NodeContainer& staNodes,
    NodeContainer& externalServer, 
    Ipv4Address externalServerIP,
    ApplicationContainer& sayedServerTCP,
    ApplicationContainer& sayedServerUDP,
    bool useTCP, 
    bool useUDP,
    bool useBulkSend,
    uint32_t packetSize,
    uint16_t tcpPort,
    uint16_t udpPort,
    double simTime)
{
    std::cout << "\n=== Scenario 1: Sayed → External Server (via Internet) ===" << std::endl;
    
    // TCP Sink on External Server (receives from Sayed)
    if (useTCP) {
        PacketSinkHelper tcpSink("ns3::TcpSocketFactory",
                                InetSocketAddress(Ipv4Address::GetAny(), tcpPort));
        sayedServerTCP = tcpSink.Install(externalServer.Get(0));
        sayedServerTCP.Start(Seconds(0.5));
        sayedServerTCP.Stop(Seconds(simTime));
        sayedServerTCP.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&RxTrace));
        std::cout << "  External Server TCP Sink (for Sayed): Port " << tcpPort << std::endl;
    }
    
    // UDP Sink on External Server (receives from Sayed)
    if (useUDP) {
        PacketSinkHelper udpSink("ns3::UdpSocketFactory",
                                InetSocketAddress(Ipv4Address::GetAny(), udpPort));
        sayedServerUDP = udpSink.Install(externalServer.Get(0));
        sayedServerUDP.Start(Seconds(0.5));
        sayedServerUDP.Stop(Seconds(simTime));
        sayedServerUDP.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&RxTrace));
        std::cout << "  External Server UDP Sink (for Sayed): Port " << udpPort << std::endl;
    }
    
    // TCP Client on Sayed (sends to External Server)
    if (useTCP) {
        if (useBulkSend) {
            BulkSendHelper bulkSend("ns3::TcpSocketFactory",
                                   InetSocketAddress(externalServerIP, tcpPort));
            bulkSend.SetAttribute("MaxBytes", UintegerValue(packetSize * 100));
            ApplicationContainer tcpApp = bulkSend.Install(staNodes.Get(0));
            tcpApp.Start(Seconds(5.0));
            tcpApp.Stop(Seconds(simTime - 1.0));
            tcpApp.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
            std::cout << "  Sayed → External Server (TCP/BulkSend): 5.0s to " << (simTime-1.0) << "s, " 
                      << (packetSize * 100 / 1024 / 1024) << " MB total" << std::endl;
        } else {
            OnOffHelper tcpClient("ns3::TcpSocketFactory",
                                InetSocketAddress(externalServerIP, tcpPort));
            tcpClient.SetConstantRate(DataRate("1Mbps"), packetSize);
            tcpClient.SetAttribute("StartTime", TimeValue(Seconds(5.0)));
            tcpClient.SetAttribute("StopTime", TimeValue(Seconds(simTime - 1.0)));
            ApplicationContainer tcpApp = tcpClient.Install(staNodes.Get(0));
            tcpApp.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
            std::cout << "  Sayed → External Server (TCP/OnOff): 5.0s to " << (simTime-1.0) << "s @ 1Mbps" << std::endl;
        }
    }
    
    // UDP Client on Sayed (sends to External Server)
    if (useUDP) {
        OnOffHelper udpClient("ns3::UdpSocketFactory",
                            InetSocketAddress(externalServerIP, udpPort));
        udpClient.SetConstantRate(DataRate("500Kbps"), packetSize);
        udpClient.SetAttribute("StartTime", TimeValue(Seconds(5.5)));
        udpClient.SetAttribute("StopTime", TimeValue(Seconds(simTime - 1.0)));
        ApplicationContainer udpApp = udpClient.Install(staNodes.Get(0));
        udpApp.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
        std::cout << "  Sayed → External Server (UDP): 5.5s to " << (simTime-1.0) << "s @ 500Kbps" << std::endl;
    }
}

// Setup Sadia to External Server traffic flow
void SetupSadiaToServerFlow(
    NodeContainer& staNodes,
    NodeContainer& externalServer, 
    Ipv4Address externalServerIP,
    ApplicationContainer& sadiaServerTCP,
    ApplicationContainer& sadiaServerUDP,
    bool useTCP, 
    bool useUDP,
    bool useBulkSend,
    uint32_t packetSize,
    uint16_t tcpPort,
    uint16_t udpPort,
    double simTime)
{
    std::cout << "\n=== Scenario 2: Sadia → External Server (via Internet) ===" << std::endl;
    
    // TCP Sink on External Server (receives from Sadia)
    if (useTCP) {
        PacketSinkHelper tcpExtSink("ns3::TcpSocketFactory",
                                    InetSocketAddress(Ipv4Address::GetAny(), tcpPort + 100));
        sadiaServerTCP = tcpExtSink.Install(externalServer.Get(0));
        sadiaServerTCP.Start(Seconds(0.5));
        sadiaServerTCP.Stop(Seconds(simTime));
        sadiaServerTCP.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&RxTrace));
        std::cout << "  External Server TCP Sink: Port " << (tcpPort + 100) << std::endl;
    }
    
    // UDP Sink on External Server (receives from Sadia)
    if (useUDP) {
        PacketSinkHelper udpExtSink("ns3::UdpSocketFactory",
                                    InetSocketAddress(Ipv4Address::GetAny(), udpPort + 100));
        sadiaServerUDP = udpExtSink.Install(externalServer.Get(0));
        sadiaServerUDP.Start(Seconds(0.5));
        sadiaServerUDP.Stop(Seconds(simTime));
        sadiaServerUDP.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&RxTrace));
        std::cout << "  External Server UDP Sink: Port " << (udpPort + 100) << std::endl;
    }
    
    // TCP Client on Sadia (sends to External Server)
    if (useTCP) {
        if (useBulkSend) {
            BulkSendHelper bulkSend("ns3::TcpSocketFactory",
                                   InetSocketAddress(externalServerIP, tcpPort + 100));
            bulkSend.SetAttribute("MaxBytes", UintegerValue(packetSize * 100));
            ApplicationContainer tcpExtApp = bulkSend.Install(staNodes.Get(1));  // Sadia
            tcpExtApp.Start(Seconds(6.0));
            tcpExtApp.Stop(Seconds(simTime - 1.0));
            tcpExtApp.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
            std::cout << "  Sadia → External Server (TCP/BulkSend): 6.0s to " << (simTime-1.0) << "s, " 
                      << (packetSize * 100 / 1024 / 1024) << " MB total" << std::endl;
        } else {
            OnOffHelper tcpExtClient("ns3::TcpSocketFactory",
                                    InetSocketAddress(externalServerIP, tcpPort + 100));
            tcpExtClient.SetConstantRate(DataRate("1Mbps"), packetSize);
            tcpExtClient.SetAttribute("StartTime", TimeValue(Seconds(6.0)));
            tcpExtClient.SetAttribute("StopTime", TimeValue(Seconds(simTime - 1.0)));
            ApplicationContainer tcpExtApp = tcpExtClient.Install(staNodes.Get(1));  // Sadia
            tcpExtApp.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
            std::cout << "  Sadia → External Server (TCP/OnOff): 6.0s to " << (simTime-1.0) << "s @ 1Mbps" << std::endl;
        }
    }
    
    // UDP Client on Sadia (sends to External Server)
    if (useUDP) {
        OnOffHelper udpExtClient("ns3::UdpSocketFactory",
                                InetSocketAddress(externalServerIP, udpPort + 100));
        udpExtClient.SetConstantRate(DataRate("500Kbps"), packetSize);
        udpExtClient.SetAttribute("StartTime", TimeValue(Seconds(6.5)));
        udpExtClient.SetAttribute("StopTime", TimeValue(Seconds(simTime - 1.0)));
        ApplicationContainer udpExtApp = udpExtClient.Install(staNodes.Get(1));  // Sadia
        udpExtApp.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
        std::cout << "  Sadia → External Server (UDP): 6.5s to " << (simTime-1.0) << "s @ 500Kbps" << std::endl;
    }
}

// Analyze flow statistics for a specific scenario
void AnalyzeFlow(const std::string& scenarioName,
                 Ipv4Address sourceIP, 
                 Ipv4Address destIP,
                 const std::map<FlowId, FlowMonitor::FlowStats>& stats,
                 Ptr<Ipv4FlowClassifier> classifier,
                 uint16_t tcpPort,
                 uint16_t udpPort,
                 double simTime)
{
    std::cout << "\n[" << scenarioName << "]" << std::endl;
    
    for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin(); i != stats.end(); ++i) {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(i->first);
        if (t.sourceAddress == sourceIP && t.destinationAddress == destIP) {
            
            std::string proto = (t.destinationPort == tcpPort) ? "TCP" : "UDP";
            
            if (i->second.rxPackets > 0) {
                double pdr = (i->second.rxPackets * 100.0) / i->second.txPackets;
                double throughput = i->second.rxBytes * 8.0 / simTime / 1000000;
                double delay = (i->second.delaySum.GetSeconds() / i->second.rxPackets) * 1000;
                
                std::cout << "  " << proto << ": PDR=" << pdr << "%, Throughput=" 
                          << throughput << " Mbps, Delay=" << delay << " ms" << std::endl;
            } else {
                std::cout << "  " << proto << ": PDR=0% (No packets received)" << std::endl;
            }
        }
    }
}

// Discover mesh route from source AP to destination AP
std::vector<uint32_t> DiscoverMeshRoute(uint32_t srcAPIdx, uint32_t dstAPIdx, uint32_t gridSize)
{
    std::vector<uint32_t> route;
    
    // Calculate grid positions
    uint32_t srcRow = srcAPIdx / gridSize;
    uint32_t srcCol = srcAPIdx % gridSize;
    uint32_t dstRow = dstAPIdx / gridSize;
    uint32_t dstCol = dstAPIdx % gridSize;
    
    std::cout << "\n=== ROUTE DISCOVERY ===" << std::endl;
    std::cout << "Source: AP" << srcAPIdx << " at (" << srcRow << "," << srcCol << ")" << std::endl;
    std::cout << "Destination: AP" << dstAPIdx << " at (" << dstRow << "," << dstCol << ")" << std::endl;
    
    // Use simple grid routing: move horizontally first, then vertically
    uint32_t currentRow = srcRow;
    uint32_t currentCol = srcCol;
    
    route.push_back(srcRow * gridSize + srcCol);  // Starting AP
    
    // Move horizontally towards destination
    while (currentCol != dstCol) {
        if (currentCol < dstCol) {
            currentCol++;
        } else {
            currentCol--;
        }
        route.push_back(currentRow * gridSize + currentCol);
    }
    
    // Move vertically towards destination
    while (currentRow != dstRow) {
        if (currentRow < dstRow) {
            currentRow++;
        } else {
            currentRow--;
        }
        route.push_back(currentRow * gridSize + currentCol);
    }
    
    std::cout << "Expected Route (grid-based): ";
    for (size_t i = 0; i < route.size(); i++) {
        std::cout << "AP" << route[i];
        if (i < route.size() - 1) std::cout << " → ";
    }
    std::cout << std::endl;
    std::cout << "Total hops: " << (route.size() - 1) << std::endl;
    
    return route;
}

// Register a flow for tracking (scalable design)
void RegisterFlow(std::string flowName, 
                  Ipv4Address sourceIP, 
                  Ipv4Address destIP,
                  std::vector<uint32_t> route,
                  uint32_t numMeshAPs)
{
    FlowTracking ft;
    ft.flowId.source = sourceIP;
    ft.flowId.destination = destIP;
    ft.flowName = flowName;
    ft.route = route;
    
    // Initialize hop metrics for ALL mesh APs (to find actual HWMP path)
    for (uint32_t apIdx = 0; apIdx < numMeshAPs; apIdx++) {
        HopMetrics hm;
        hm.apIndex = apIdx;
        hm.apName = "AP" + std::to_string(apIdx);
        ft.hopMetrics[apIdx] = hm;
    }
    
    g_trackedFlows[ft.flowId] = ft;
    
    std::cout << "  Registered flow: " << flowName << " (" 
              << sourceIP << " → " << destIP << ")" << std::endl;
    std::cout << "    Tracing: ALL " << numMeshAPs << " mesh APs (to discover actual HWMP path)" << std::endl;
}

// Setup IP-level tracing for all mesh APs
void SetupIPLevelTracing(NodeContainer& meshAPs)
{
    std::cout << "\n=== SETTING UP IP-LEVEL FLOW TRACKING ===" << std::endl;
    
    for (uint32_t i = 0; i < meshAPs.GetN(); i++) {
        Ptr<Node> node = meshAPs.Get(i);
        uint32_t nodeId = node->GetId();
        
        // Connect IP-level traces using Config::Connect with node-specific paths and bound callbacks
        std::ostringstream ossTx, ossRx, ossUnicast, ossDrop;
        ossTx << "/NodeList/" << nodeId << "/$ns3::Ipv4L3Protocol/Tx";
        ossRx << "/NodeList/" << nodeId << "/$ns3::Ipv4L3Protocol/LocalDeliver";
        ossUnicast << "/NodeList/" << nodeId << "/$ns3::Ipv4L3Protocol/UnicastForward";
        ossDrop << "/NodeList/" << nodeId << "/$ns3::Ipv4L3Protocol/Drop";
        
        Config::ConnectWithoutContext(ossTx.str(), MakeBoundCallback(&IpForwardTrace, nodeId));
        Config::ConnectWithoutContext(ossRx.str(), MakeBoundCallback(&IpRxTrace, nodeId));
        Config::ConnectWithoutContext(ossUnicast.str(), MakeBoundCallback(&IpRxTrace, nodeId)); // Track forwarded packets as RX
        // TODO: Drop trace - can add later if needed
        // Config::ConnectWithoutContext(ossDrop.str(), MakeBoundCallback(&IpDropTrace, nodeId));
    }
    
    std::cout << "  IP-level tracing enabled on all " << meshAPs.GetN() << " mesh APs" << std::endl;
}

// Analyze and print per-hop statistics for all tracked flows
void AnalyzeAllFlows(uint32_t nMeshAPs, std::string traceFile)
{
    std::cout << "\n╔═══════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║         COMPLETE FLOW ANALYSIS (IP + Mesh Layers)        ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════════╝\n" << std::endl;
    
    for (auto& flowPair : g_trackedFlows) {
        FlowTracking& flow = flowPair.second;
        
        // Build list of APs with actual traffic (HWMP's actual path)
        std::vector<uint32_t> activeAPs;
        for (const auto& hopPair : flow.hopMetrics) {
            const HopMetrics& hm = hopPair.second;
            bool hasTraffic = (hm.tcpPacketsIn > 0 || hm.tcpPacketsOut > 0 ||
                               hm.udpPacketsIn > 0 || hm.udpPacketsOut > 0 ||
                               hm.tcpDropped > 0 || hm.udpDropped > 0);
            if (hasTraffic) {
                activeAPs.push_back(hopPair.first);
            }
        }
        
        // Sort by AP index for logical flow
        std::sort(activeAPs.begin(), activeAPs.end());
        
        // Print header with actual path
        std::cout << "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" << std::endl;
        std::cout << "FLOW: " << flow.flowName << std::endl;
        std::cout << "Source: " << flow.flowId.source << " → Destination: " << flow.flowId.destination << std::endl;
        std::cout << "Path: ";
        for (size_t i = 0; i < activeAPs.size(); i++) {
            std::cout << "AP" << activeAPs[i];
            if (i < activeAPs.size() - 1) std::cout << " → ";
        }
        std::cout << "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" << std::endl;
        
        uint32_t totalTcpSent = 0, totalTcpRecv = 0, totalTcpDrop = 0;
        uint32_t totalUdpSent = 0, totalUdpRecv = 0, totalUdpDrop = 0;
        
        // Print stats for active APs only
        for (size_t i = 0; i < activeAPs.size(); i++) {
            uint32_t apIdx = activeAPs[i];
            HopMetrics& hm = flow.hopMetrics[apIdx];
            
            std::cout << "Hop " << (i+1) << ": AP" << apIdx;
            if (i == 0) std::cout << " (Source AP)";
            else if (i == activeAPs.size() - 1) std::cout << " (Destination AP)";
            std::cout << std::endl;
            
            if (i == 0) {
                // Source AP
                std::cout << "  TCP OUT: " << hm.tcpPacketsOut << " packets" << std::endl;
                std::cout << "  UDP OUT: " << hm.udpPacketsOut << " packets" << std::endl;
                totalTcpSent = hm.tcpPacketsOut;
                totalUdpSent = hm.udpPacketsOut;
            } else {
                // Intermediate or destination AP
                std::cout << "  TCP: IN=" << hm.tcpPacketsIn << ", OUT=" << hm.tcpPacketsOut 
                          << ", DROP=" << hm.tcpDropped << std::endl;
                std::cout << "  UDP: IN=" << hm.udpPacketsIn << ", OUT=" << hm.udpPacketsOut 
                          << ", DROP=" << hm.udpDropped << std::endl;
                
                totalTcpDrop += hm.tcpDropped;
                totalUdpDrop += hm.udpDropped;
                
                if (i == activeAPs.size() - 1) {
                    totalTcpRecv = hm.tcpPacketsIn;
                    totalUdpRecv = hm.udpPacketsIn;
                }
                
                // Calculate hop PDR (packets received from previous hop)
                uint32_t prevApIdx = activeAPs[i-1];
                HopMetrics& prevHm = flow.hopMetrics[prevApIdx];
                
                if (prevHm.tcpPacketsOut > 0) {
                    double tcpPdr = (hm.tcpPacketsIn * 100.0) / prevHm.tcpPacketsOut;
                    std::cout << "  TCP Hop PDR: " << std::fixed << std::setprecision(2) << tcpPdr << "%";
                    if (tcpPdr < 95.0) std::cout << " ⚠️";
                    std::cout << std::endl;
                }
                if (prevHm.udpPacketsOut > 0) {
                    double udpPdr = (hm.udpPacketsIn * 100.0) / prevHm.udpPacketsOut;
                    std::cout << "  UDP Hop PDR: " << std::fixed << std::setprecision(2) << udpPdr << "%";
                    if (udpPdr < 95.0) std::cout << " ⚠️";
                    std::cout << std::endl;
                }
            }
            std::cout << std::endl;
        }
        
        // Summary for this flow
        std::cout << "─────────────────────────────────────────────────────────────" << std::endl;
        std::cout << "FLOW SUMMARY:" << std::endl;
        
        if (totalTcpSent > 0) {
            double tcpE2ePdr = (totalTcpRecv * 100.0) / totalTcpSent;
            std::cout << "  TCP E2E PDR: " << std::fixed << std::setprecision(2) << tcpE2ePdr << "% (" 
                      << totalTcpRecv << "/" << totalTcpSent << " packets)";
            if (tcpE2ePdr >= 95.0) std::cout << " ✅";
            else if (tcpE2ePdr >= 80.0) std::cout << " ⚠️";
            else std::cout << " ❌";
            std::cout << std::endl;
            std::cout << "  TCP Total Drops: " << totalTcpDrop << " packets" << std::endl;
        }
        
        if (totalUdpSent > 0) {
            double udpE2ePdr = (totalUdpRecv * 100.0) / totalUdpSent;
            std::cout << "  UDP E2E PDR: " << std::fixed << std::setprecision(2) << udpE2ePdr << "% (" 
                      << totalUdpRecv << "/" << totalUdpSent << " packets)";
            if (udpE2ePdr >= 95.0) std::cout << " ✅";
            else if (udpE2ePdr >= 80.0) std::cout << " ⚠️";
            else std::cout << " ❌";
            std::cout << std::endl;
            std::cout << "  UDP Total Drops: " << totalUdpDrop << " packets" << std::endl;
        }
        
        if (totalTcpSent + totalUdpSent > 0) {
            uint32_t totalSent = totalTcpSent + totalUdpSent;
            uint32_t totalRecv = totalTcpRecv + totalUdpRecv;
            double overallPdr = (totalRecv * 100.0) / totalSent;
            std::cout << "  Overall E2E PDR: " << std::fixed << std::setprecision(2) << overallPdr << "%" << std::endl;
        }
        
        std::cout << "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" << std::endl;
    }
}

// Hop count analysis helper - Actually parses trace file
void AnalyzeHopCount(std::string traceFile)
{
    std::cout << "\n=== HOP COUNT ANALYSIS ===" << std::endl;
    
    std::ifstream trace(traceFile);
    if (!trace.is_open()) {
        std::cout << "Warning: Could not open trace file " << traceFile << std::endl;
        return;
    }
    
    std::string line;
    int minTtl = 32;
    int maxTtl = 0;
    int packetCount = 0;
    std::set<int> ttlValues;
    
    while (std::getline(trace, line)) {
        // Look for mesh TTL in packets between 10.1.0.X addresses
        if (line.find("10.1.0.") != std::string::npos && 
            line.find("ttl=") != std::string::npos &&
            line.find("ns3::dot11s::MeshHeader") != std::string::npos) {
            
            size_t ttlPos = line.find("ttl=");
            if (ttlPos != std::string::npos) {
                int ttl = std::stoi(line.substr(ttlPos + 4, 2));
                ttlValues.insert(ttl);
                if (ttl < minTtl) minTtl = ttl;
                if (ttl > maxTtl) maxTtl = ttl;
                packetCount++;
            }
        }
    }
    trace.close();
    
    if (packetCount > 0) {
        int hopCount = maxTtl - minTtl;
        std::cout << "Mesh packets analyzed: " << packetCount << std::endl;
        std::cout << "Initial mesh TTL: " << maxTtl << std::endl;
        std::cout << "Final mesh TTL: " << minTtl << std::endl;
        std::cout << "Hop count (mesh backbone): " << hopCount << " hops" << std::endl;
        std::cout << "TTL values seen: ";
        for (int ttl : ttlValues) {
            std::cout << ttl << " ";
        }
        std::cout << std::endl;
    } else {
        std::cout << "No mesh packets found in trace file" << std::endl;
    }
}

// Helper function to setup 3D GaussMarkov mobility for a STA
void SetupSTAMobility(Ptr<Node> node, 
                      std::string staName,
                      double startX, double startY, double startZ,
                      double minX, double maxX,
                      double minY, double maxY, 
                      double minZ, double maxZ,
                      double meanVelocityMin = 0.3,
                      double meanVelocityMax = 0.8)
{
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
    posAlloc->Add(Vector(startX, startY, startZ));
    
    mobility.SetPositionAllocator(posAlloc);
    mobility.SetMobilityModel("ns3::GaussMarkovMobilityModel",
        "Bounds", BoxValue(Box(minX, maxX, minY, maxY, minZ, maxZ)),
        "TimeStep", TimeValue(Seconds(1.0)),
        "Alpha", DoubleValue(0.85),  // 85% memory (smoother movement)
        "MeanVelocity", StringValue("ns3::UniformRandomVariable[Min=" + 
                                    std::to_string(meanVelocityMin) + "|Max=" + 
                                    std::to_string(meanVelocityMax) + "]"),
        "MeanDirection", StringValue("ns3::UniformRandomVariable[Min=0|Max=6.283185307]"),
        "MeanPitch", StringValue("ns3::UniformRandomVariable[Min=-0.05|Max=0.05]"),
        "NormalVelocity", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.0|Bound=0.0]"),
        "NormalDirection", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.1|Bound=0.2]"),
        "NormalPitch", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.01|Bound=0.02]"));
    
    mobility.Install(node);
    
    std::cout << "  " << staName << ": Slow GaussMarkov 3D (" 
              << meanVelocityMin << "-" << meanVelocityMax << " m/s)" << std::endl;
    std::cout << "    Position: (" << startX << ", " << startY << ", " << startZ << ")" << std::endl;
    std::cout << "    Bounds: X[" << minX << "-" << maxX << "], Y[" 
              << minY << "-" << maxY << "], Z[" << minZ << "-" << maxZ << "]" << std::endl;
}

// Print simulation configuration
void PrintConfiguration(uint32_t nSTAs, uint32_t packetSizeKB, uint32_t packetSize, 
                        std::string trafficType, double simTime, bool useObstacles,
                        double fieldX, double fieldY, const MeshAPConfig& meshCfg, uint32_t nMeshAPs)
{
    std::cout << "=== WiFi Mesh Backhaul with Infrastructure Mode ===" << std::endl;
    
    std::cout << "\n[Mesh AP Configuration]" << std::endl;
    std::cout << "  Device: " << meshCfg.name << std::endl;
    std::cout << "  Description: " << meshCfg.description << std::endl;
    std::cout << "  WiFi Standard: " << meshCfg.wifiStandard << " (" << meshCfg.dataMode << ")" << std::endl;
    std::cout << "  TX Power: " << meshCfg.txPowerStart << " dBm" << std::endl;
    std::cout << "  RX Sensitivity: " << meshCfg.rxSensitivity << " dBm" << std::endl;
    std::cout << "  RX Gain: " << meshCfg.rxGain << " dB, TX Gain: " << meshCfg.txGain << " dB" << std::endl;
    std::cout << "  Number of Interfaces: " << meshCfg.numInterfaces << std::endl;
    std::cout << "  Expected Range: " << meshCfg.meshRange << " meters" << std::endl;
    
    std::cout << "\n[Traffic Configuration]" << std::endl;
    std::cout << "  Number of STAs: " << nSTAs << " (Sayed, Sadia, + " << (nSTAs - 2) << " more)" << std::endl;
    std::cout << "  Packet size: " << packetSizeKB << " KB (" << packetSize << " bytes)" << std::endl;
    std::cout << "  Traffic type: " << trafficType << std::endl;
    std::cout << "  Simulation time: " << simTime << " seconds" << std::endl;
    std::cout << "  Obstacles: " << (useObstacles ? "ENABLED" : "DISABLED") << std::endl;
    
    std::cout << "\n[Field & Topology Configuration]" << std::endl;
    std::cout << "  Field size: " << fieldX << "m x " << fieldY << "m" << std::endl;
    std::cout << "  AP Height: " << meshCfg.apHeight << " meters" << std::endl;
    std::cout << "  AP Spacing: " << meshCfg.apSpacing << " meters" << std::endl;
    std::cout << "  Grid: " << meshCfg.gridSize << " x " << meshCfg.gridSize << " = " << nMeshAPs << " APs" << std::endl;
    std::cout << "  Coverage: ~" << (meshCfg.gridSize - 1) * meshCfg.apSpacing << "m x " << (meshCfg.gridSize - 1) * meshCfg.apSpacing << "m" << std::endl;
    
}

int main(int argc, char *argv[])
{
    // Enable packet metadata
    PacketMetadata::Enable();

    // Enable logging
    LogComponentEnable("BulkSendApplication", LOG_LEVEL_INFO);
    LogComponentEnable("PacketSink", LOG_LEVEL_INFO);

    // Command-line configurable parameters
    uint32_t nSTAs = 3;              // Number of STAs (3 = Sayed+Sadia+STA20 for three scenarios)
    uint32_t packetSizeKB = 10;      // Packet size in KB (10, 100, 1024, etc.)
    std::string trafficType = "both"; // "tcp", "udp", or "both"
    double simTime = 15.0;
    bool useObstacles = false;       // Enable/disable obstacles (default: false)
    uint32_t meshConfig = 0;         // Mesh AP configuration (0=default, 1=TP-Link, 2=Orbi, 3=ZenWiFi)
    
    // Parse command line
    CommandLine cmd(__FILE__);
    cmd.AddValue("nSTAs", "Number of STAs (2-9, 2=Sayed+Sadia only)", nSTAs);
    cmd.AddValue("packetSize", "Packet size in KB (10=10KB, 100=100KB, 1024=1MB)", packetSizeKB);
    cmd.AddValue("trafficType", "Traffic type: tcp, udp, or both", trafficType);
    cmd.AddValue("simTime", "Simulation time in seconds", simTime);
    cmd.AddValue("obstacles", "Enable obstacles/buildings (0=no, 1=yes)", useObstacles);
    cmd.AddValue("meshConfig", "Mesh AP config (0=default 100m, 1=TP-Link 200m, 2=Orbi 50m, 3=ZenWiFi 60m)", meshConfig);
    cmd.Parse(argc, argv);
    
    // Validate inputs
    if (nSTAs < 2) nSTAs = 2;  // Minimum 2 (Sayed and Sadia for two scenarios)
    if (nSTAs >= 9) nSTAs = 9;
    if (packetSizeKB < 1) packetSizeKB = 1;
    if (meshConfig > 3) meshConfig = 0;  // Validate mesh config
    
    uint32_t packetSize = packetSizeKB * 1024;  // Convert KB to bytes
    const uint16_t tcpPort = 7000;
    const uint16_t udpPort = 8000;
    
    // Get mesh configuration from preset
    MeshAPConfig meshCfg = GetMeshConfig(meshConfig);
    
    // Field and mesh AP configuration (use values from selected config)
    const double fieldX = 400.0;         // Field width (X)
    const double fieldY = 400.0;         // Field length (Y)
    const double fieldZ = 30.0;          // Field height (Z)
    const double apHeight = meshCfg.apHeight;        // AP height from config
    const double meshRange = meshCfg.meshRange;      // Target mesh WiFi range from config
    const uint32_t gridSize = meshCfg.gridSize;      // Grid size from config
    const uint32_t nMeshAPs = gridSize * gridSize;   // Calculate total APs
    const double apSpacing = meshCfg.apSpacing;      // AP spacing from config
    
    std::string outputDir = "wifi_mesh_backhaul_outputs/";

    // Print configuration
    PrintConfiguration(nSTAs, packetSizeKB, packetSize, trafficType, simTime, useObstacles,
                      fieldX, fieldY, meshCfg, nMeshAPs);

    // Create nodes
    NodeContainer meshAPNodes;       // Mesh APs
    NodeContainer internetNode;      // Internet gateway/router
    NodeContainer externalServer;    // External server (outside mesh network)
    NodeContainer staNodes;           // STAs (Sayed, Sadia, + others)
    
    meshAPNodes.Create(nMeshAPs);
    internetNode.Create(1);
    externalServer.Create(1);
    staNodes.Create(nSTAs);  // Create requested number of STAs (minimum 3)

    std::cout << "\n[Nodes Created]" << std::endl;
    std::cout << "  Mesh APs: " << nMeshAPs << std::endl;
    std::cout << "  Internet gateway: 1" << std::endl;
    std::cout << "  External server: 1" << std::endl;
    std::cout << "  STAs: " << nSTAs << " (Index 0=Sayed, 1=Sadia";
    if (nSTAs > 2) {
        std::cout << ", 2-" << (nSTAs-1) << "=Additional STAs";
    }
    std::cout << ")" << std::endl;

    // Mobility setup for mesh APs (grid layout)
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> meshPositions = CreateObject<ListPositionAllocator>();
    
    uint32_t lastAPIdx = nMeshAPs - 1;
    
    std::cout << "\nMesh AP Grid (" << gridSize << "×" << gridSize << "):" << std::endl;
    for (uint32_t row = 0; row < gridSize; ++row) {
        for (uint32_t col = 0; col < gridSize; ++col) {
            uint32_t apIdx = row * gridSize + col;
            double x = col * apSpacing;
            double y = row * apSpacing;
            meshPositions->Add(Vector(x, y, apHeight));
            
            // Only print corner APs to avoid too much output
            if (apIdx == 0) {
                std::cout << "  AP" << apIdx << ": (" << x << ", " << y << ", " << apHeight << ") - Bottom-left (has Sayed, CSMA)" << std::endl;
            } else if (apIdx == lastAPIdx) {
                std::cout << "  AP" << apIdx << ": (" << x << ", " << y << ", " << apHeight << ") - Top-right (has Sadia)" << std::endl;
            }
        }
    }
    std::cout << "  ... (" << (nMeshAPs - 2) << " more APs between AP0 and AP" << lastAPIdx << ")" << std::endl;
    
    mobility.SetPositionAllocator(meshPositions);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(meshAPNodes);

    // Position internet gateway and external server (doesn't matter, wired connections)
    MobilityHelper internetMobility;
    internetMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    internetMobility.Install(internetNode);
    internetMobility.Install(externalServer);

    // Position STAs - STATIC for reliable measurements
    std::cout << "\n=== Positioning STAs ===" << std::endl;
    
    double lastAPX = (gridSize - 1) * apSpacing;
    double lastAPY = (gridSize - 1) * apSpacing;
    const double sayedHeight = 15.0;
    const double sadiaHeight = 25.0;
    
    // ========== SAYED & SADIA: Slow GaussMarkov 3D Mobility ==========
    
    // ========== SAYED: Slow 3D Movement near AP0 ==========
    SetupSTAMobility(
        staNodes.Get(0),        // Node
        "Sayed (STA 0)",        // Name
        10.0, 10.0, sayedHeight,  // Start position (x, y, z)
        5.0, 15.0,              // X bounds (min, max)
        5.0, 15.0,              // Y bounds (min, max)
        15.0, 30.0              // Z bounds (min, max)
    );
    std::cout << "    Near: AP0" << std::endl;
    
    // ========== SADIA: Slow 3D Movement near Last AP ==========
    SetupSTAMobility(
        staNodes.Get(1),              // Node
        "Sadia (STA 1)",              // Name
        lastAPX - 10.0, lastAPY - 10.0, sadiaHeight,  // Start position
        lastAPX - 15.0, lastAPX - 5.0,  // X bounds
        lastAPY - 15.0, lastAPY - 5.0,  // Y bounds
        15.0, 30.0                      // Z bounds
    );
    std::cout << "    Near: AP" << lastAPIdx << " (diagonal path, " 
              << ((gridSize - 1) * 2) << " hops worst case)" << std::endl;
    
    // ========== STA20: Slow 3D Movement near Center AP ==========
    if (nSTAs > 2) {
        // Use center AP (middle of grid) - SCALABLE for any grid size
        uint32_t centerAPIdx = (gridSize / 2) * gridSize + (gridSize / 2);
        uint32_t centerRow = centerAPIdx / gridSize;
        uint32_t centerCol = centerAPIdx % gridSize;
        double centerX = centerCol * apSpacing;
        double centerY = centerRow * apSpacing;
        
        // Random initial height between 0-30m
        Ptr<UniformRandomVariable> randHeight = CreateObject<UniformRandomVariable>();
        randHeight->SetAttribute("Min", DoubleValue(0.0));
        randHeight->SetAttribute("Max", DoubleValue(30.0));
        double sta20Height = randHeight->GetValue();
        
        SetupSTAMobility(
            staNodes.Get(2),              // Node
            "STA20 (STA 2)",              // Name
            centerX + 10.0, centerY - 10.0, sta20Height,  // Start position
            centerX + 5.0, centerX + 15.0,  // X bounds
            centerY - 15.0, centerY - 5.0,  // Y bounds
            0.0, 30.0                       // Z bounds
        );
        std::cout << "    Near: Center AP" << centerAPIdx << std::endl;
    }
    
    std::cout << "\n[Mobility Summary]" << std::endl;
    std::cout << "  Sayed & Sadia: SLOW GaussMarkov 3D mobility (0.3-0.8 m/s)" << std::endl;
    if (nSTAs > 2) {
        std::cout << "  STA20: SLOW GaussMarkov 3D mobility (0.3-0.8 m/s, height varies 0-30m)" << std::endl;
    }
    std::cout << "  Movement: Gentle, smooth 3D motion within 10m×10m area" << std::endl;

    // ========== MESH BACKHAUL NETWORK (Between APs) ==========
    std::cout << "\n=== Creating Mesh Backhaul Network ===" << std::endl;
    std::cout << "Using: " << meshCfg.name << std::endl;
    
    YansWifiChannelHelper meshChannel = YansWifiChannelHelper::Default();
    
    
    YansWifiPhyHelper meshPhy;
    meshPhy.SetChannel(meshChannel.Create());
    
    // Apply mesh configuration parameters from selected device
    meshPhy.Set("TxPowerStart", DoubleValue(meshCfg.txPowerStart));
    meshPhy.Set("TxPowerEnd", DoubleValue(meshCfg.txPowerEnd));
    meshPhy.Set("RxSensitivity", DoubleValue(meshCfg.rxSensitivity));
    meshPhy.Set("RxGain", DoubleValue(meshCfg.rxGain));
    meshPhy.Set("TxGain", DoubleValue(meshCfg.txGain));
    
    
    
    
    MeshHelper mesh = MeshHelper::Default();
    mesh.SetStackInstaller("ns3::Dot11sStack");
    mesh.SetSpreadInterfaceChannels(MeshHelper::SPREAD_CHANNELS);
    mesh.SetMacType("RandomStart", TimeValue(Seconds(0.1)));
    mesh.SetNumberOfInterfaces(meshCfg.numInterfaces);  // Use config value
    
    // Note: Using default WiFi standard (802.11a) and ArfWifiManager for mesh
    // Setting custom standards causes channel allocation issues
    std::cout << "  WiFi Standard: 802.11a (default for mesh)" << std::endl;
    std::cout << "  Rate Control: ArfWifiManager (adaptive)" << std::endl;

    NetDeviceContainer meshDevices = mesh.Install(meshPhy, meshAPNodes);
    std::cout << "Installed 802.11s mesh on " << nMeshAPs << " APs with " 
              << meshCfg.numInterfaces << " interface(s)" << std::endl;

    // ========== INFRASTRUCTURE WIFI (For All STAs) ==========
    std::cout << "\n=== Creating Infrastructure WiFi Networks ===" << std::endl;

    // Calculate AP indices dynamically based on grid size
    // Strategy: Spread STAs across grid - corners, edges, center
    std::vector<uint32_t> apIndices;
    uint32_t centerIdx = (gridSize / 2) * gridSize + (gridSize / 2);  // Center AP
    
    // Always assign first two STAs (Sayed & Sadia) to opposite corners
    apIndices.push_back(0);                    // STA 0 (Sayed) -> AP 0 (bottom-left corner)
    apIndices.push_back(lastAPIdx);            // STA 1 (Sadia) -> Last AP (top-right corner)
    
    // Additional STAs distributed across grid
    if (nSTAs > 2) {
        // STA 2 (STA20) -> Center AP (middle of grid) - SCALABLE for any grid size
        apIndices.push_back(centerIdx);                             // STA 2 (STA20) -> Center AP
        if (nSTAs > 3) apIndices.push_back(gridSize - 1);           // STA 3 -> Top-left corner
        if (nSTAs > 4) apIndices.push_back(lastAPIdx - gridSize + 1); // STA 4 -> Bottom-right corner
        if (nSTAs > 5) apIndices.push_back(gridSize / 2);           // STA 5 -> Bottom edge center
        if (nSTAs > 6) apIndices.push_back(lastAPIdx - gridSize / 2); // STA 6 -> Top edge center
        if (nSTAs > 7) apIndices.push_back((gridSize / 2) * gridSize); // STA 7 -> Left edge center
        if (nSTAs > 8) apIndices.push_back((gridSize / 2) * gridSize + gridSize - 1); // STA 8 -> Right edge center
    }
    
    std::vector<NetDeviceContainer> staDevices(nSTAs);
    std::vector<NetDeviceContainer> apInfraDevices(nSTAs);
    std::vector<Ipv4InterfaceContainer> infraAPInterfaces(nSTAs);
    std::vector<Ipv4InterfaceContainer> staInterfaces(nSTAs);
    
    for (uint32_t staIdx = 0; staIdx < nSTAs; ++staIdx) {
        uint32_t apIdx = apIndices[staIdx];
        
        YansWifiChannelHelper infraChannel = YansWifiChannelHelper::Default();
        YansWifiPhyHelper infraPhy;
        infraPhy.SetChannel(infraChannel.Create());
        
        WifiHelper infraWifi;
        WifiMacHelper infraMac;
        
        // Use default WiFi standard (802.11a) and adaptive rate control for infrastructure
        // infraWifi uses defaults which should work without channel conflicts
        
        std::stringstream ssidName;
        ssidName << "mesh-ap" << apIdx << "-net";
        Ssid ssid = Ssid(ssidName.str());
        
        // Configure STA
        infraMac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid));
        staDevices[staIdx] = infraWifi.Install(infraPhy, infraMac, staNodes.Get(staIdx));
        
        // Configure AP
        infraMac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(ssid));
        apInfraDevices[staIdx] = infraWifi.Install(infraPhy, infraMac, meshAPNodes.Get(apIdx));
        
        std::string staName = (staIdx == 0) ? "Sayed" : (staIdx == 1) ? "Sadia" : (staIdx == 2) ? "STA20" : ("STA" + std::to_string(staIdx));
        std::cout << "  " << staName << " (STA" << staIdx << ") <-> AP" << apIdx << std::endl;
    }
    
    std::cout << "Created " << nSTAs << " infrastructure WiFi networks (802.11a default)" << std::endl;

    // ========== ROUTE DISCOVERY & FLOW REGISTRATION ==========
    // Store routes for later registration (after IP assignment)
    std::vector<uint32_t> meshRoute_SadiaToSTA20;

    // ========== WIRED CSMA (Internet <-> AP0) ==========
    std::cout << "\n=== Creating Wired Connection (Internet Gateway <-> AP0) ===" << std::endl;
    
    CsmaHelper csma;
    csma.SetChannelAttribute("DataRate", StringValue("100Mbps"));
    csma.SetChannelAttribute("Delay", TimeValue(MilliSeconds(2)));
    
    NodeContainer csmaNodes(internetNode.Get(0), meshAPNodes.Get(0));
    NetDeviceContainer csmaDevices = csma.Install(csmaNodes);
    
    std::cout << "Connected Internet Gateway to AP0 via CSMA (100Mbps, 2ms delay)" << std::endl;

    // ========== EXTERNAL NETWORK (Internet <-> External Server) ==========
    std::cout << "\n=== Creating External Network (Internet Gateway <-> External Server) ===" << std::endl;
    
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
    p2p.SetChannelAttribute("Delay", StringValue("10ms"));  // Simulates internet latency
    
    NetDeviceContainer externalDevices = p2p.Install(internetNode.Get(0), externalServer.Get(0));
    
    std::cout << "Connected External Server to Internet Gateway via P2P (1Gbps, 10ms delay)" << std::endl;

    // ========== INSTALL INTERNET STACK ==========
    std::cout << "\n=== Installing Internet Stack ===" << std::endl;
    
    // For mesh nodes: Install internet stack WITHOUT routing helper
    // This preserves the HWMP routing already set up by mesh.Install()
    InternetStackHelper internetMesh;
    // Don't set routing helper - keeps default/existing routing (HWMP)
    internetMesh.Install(meshAPNodes);
    
    // For non-mesh nodes: Install with default routing
    InternetStackHelper internet;
    internet.Install(internetNode);
    internet.Install(externalServer);
    internet.Install(staNodes);
    
    std::cout << "Installed TCP/IP stack on all nodes" << std::endl;
    std::cout << "Mesh APs: Preserving HWMP routing from MeshHelper" << std::endl;

    // ========== IP ADDRESS ASSIGNMENT ==========
    std::cout << "\n=== Assigning IP Addresses ===" << std::endl;
    
    Ipv4AddressHelper ipv4;
    
    // Mesh backhaul network
    ipv4.SetBase("10.1.0.0", "255.255.255.0");
    Ipv4InterfaceContainer meshInterfaces = ipv4.Assign(meshDevices);
    std::cout << "Mesh backhaul: 10.1.0.1 - 10.1.0.9" << std::endl;
    
    // CSMA network (Internet Gateway <-> AP0)
    ipv4.SetBase("172.16.1.0", "255.255.255.0");
    Ipv4InterfaceContainer csmaInterfaces = ipv4.Assign(csmaDevices);
    std::cout << "CSMA network: " << csmaInterfaces.GetAddress(0) << " (Internet Gateway), " 
              << csmaInterfaces.GetAddress(1) << " (AP0)" << std::endl;
    
    // External network (Internet Gateway <-> External Server)
    ipv4.SetBase("200.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer externalInterfaces = ipv4.Assign(externalDevices);
    std::cout << "External network: " << externalInterfaces.GetAddress(0) << " (Internet Gateway), " 
              << externalInterfaces.GetAddress(1) << " (External Server)" << std::endl;
    
    // Infrastructure WiFi networks (one per STA)
    std::cout << "\nInfrastructure WiFi IP assignments:" << std::endl;
    for (uint32_t staIdx = 0; staIdx < nSTAs; ++staIdx) {
        std::stringstream base;
        base << "192.168." << (staIdx + 1) << ".0";
        ipv4.SetBase(base.str().c_str(), "255.255.255.0");
        
        infraAPInterfaces[staIdx] = ipv4.Assign(apInfraDevices[staIdx]);
        staInterfaces[staIdx] = ipv4.Assign(staDevices[staIdx]);
        
        std::string staName = (staIdx == 0) ? "Sayed" : (staIdx == 1) ? "Sadia" : (staIdx == 2) ? "STA20" : ("STA" + std::to_string(staIdx));
        std::cout << "  " << staName << ": " << staInterfaces[staIdx].GetAddress(0) 
                  << " <-> AP" << apIndices[staIdx] << ": " << infraAPInterfaces[staIdx].GetAddress(0) << std::endl;
    }

    // Configure routing: Connect all networks
    std::cout << "\n=== Configuring Static Routes ===" << std::endl;
    
    // Create static routing helper (for adding routes to all nodes)
    Ipv4StaticRoutingHelper staticRoutingHelper;
    
    // On Internet Gateway: Route to all infrastructure networks and mesh
    Ptr<Ipv4StaticRouting> internetStaticRouting = staticRoutingHelper.GetStaticRouting(internetNode.Get(0)->GetObject<Ipv4>());
    internetStaticRouting->AddNetworkRouteTo(Ipv4Address("192.168.0.0"), Ipv4Mask("255.255.0.0"), 
                                             csmaInterfaces.GetAddress(1), 1);  // All 192.168.x.x via AP0
    internetStaticRouting->AddNetworkRouteTo(Ipv4Address("10.1.0.0"), Ipv4Mask("255.255.255.0"), 
                                             csmaInterfaces.GetAddress(1), 1);  // Mesh network via AP0
    std::cout << "Internet Gateway: Routes to all internal networks (192.168.x.x, 10.1.0.x) via AP0" << std::endl;
    
    // On External Server: Route back to all internal networks
    Ptr<Ipv4StaticRouting> externalStaticRouting = staticRoutingHelper.GetStaticRouting(externalServer.Get(0)->GetObject<Ipv4>());
    externalStaticRouting->AddNetworkRouteTo(Ipv4Address("192.168.0.0"), Ipv4Mask("255.255.0.0"), 
                                             externalInterfaces.GetAddress(0), 1);  // All 192.168.x.x networks
    externalStaticRouting->AddNetworkRouteTo(Ipv4Address("10.1.0.0"), Ipv4Mask("255.255.255.0"), 
                                             externalInterfaces.GetAddress(0), 1);  // Mesh network
    std::cout << "External Server: Routes to internal networks via Internet Gateway" << std::endl;
    
    // Configure each AP's routing
    for (uint32_t staIdx = 0; staIdx < nSTAs; ++staIdx) {
        uint32_t apIdx = apIndices[staIdx];
        Ptr<Ipv4StaticRouting> apRouting = staticRoutingHelper.GetStaticRouting(meshAPNodes.Get(apIdx)->GetObject<Ipv4>());
        
        // Route to external network via mesh to AP0 (if not already AP0)
        if (apIdx != 0) {
            apRouting->AddNetworkRouteTo(Ipv4Address("200.1.1.0"), Ipv4Mask("255.255.255.0"), 
                                         meshInterfaces.GetAddress(0), 1);  // Via mesh to AP0
        } else {
            // AP0 routes to external via CSMA
            apRouting->AddNetworkRouteTo(Ipv4Address("200.1.1.0"), Ipv4Mask("255.255.255.0"), 
                                         csmaInterfaces.GetAddress(0), 2);  // Via CSMA
        }
        
        // **FIX**: Add routes to OTHER STAs' networks via mesh
        for (uint32_t otherStaIdx = 0; otherStaIdx < nSTAs; ++otherStaIdx) {
            if (otherStaIdx != staIdx) {  // Don't route to own STA
                uint32_t otherApIdx = apIndices[otherStaIdx];
                std::stringstream otherNetwork;
                otherNetwork << "192.168." << (otherStaIdx + 1) << ".0";
                
                // Route to other STA's network via mesh to their AP
                apRouting->AddNetworkRouteTo(Ipv4Address(otherNetwork.str().c_str()), 
                                             Ipv4Mask("255.255.255.0"),
                                             meshInterfaces.GetAddress(otherApIdx), 1);  // Via mesh
            }
        }
    }
    std::cout << "Mesh APs: Added static routes for external network (supplements HWMP for inter-mesh)" << std::endl;
    
    // Configure each STA's default route via their AP
    for (uint32_t staIdx = 0; staIdx < nSTAs; ++staIdx) {
        Ptr<Ipv4StaticRouting> staRouting = staticRoutingHelper.GetStaticRouting(staNodes.Get(staIdx)->GetObject<Ipv4>());
        staRouting->SetDefaultRoute(infraAPInterfaces[staIdx].GetAddress(0), 1);
    }
    std::cout << "All " << nSTAs << " STAs: Default route via their respective APs" << std::endl;
    
    std::cout << "\nRouting Summary:" << std::endl;
    std::cout << "  - Mesh APs: HWMP for inter-mesh + static for external" << std::endl;
    std::cout << "  - STAs: Static default routes" << std::endl;
    std::cout << "  - Gateway: Static routes to all networks" << std::endl;

    // ========== REGISTER FLOWS FOR TRACKING (Will be done after getting IP addresses) ==========
    std::vector<uint32_t> meshRoute_SayedToExternal;
    meshRoute_SayedToExternal.push_back(0);  // Only AP0 is in the mesh path for Sayed -> External
    
    // Discover routes for intra-mesh flows
    if (nSTAs > 2 && apIndices.size() > 2) {
        uint32_t sadiaAPIdx = apIndices[1];  // Sadia's AP (typically AP24)
        uint32_t sta20APIdx = apIndices[2];  // STA20's AP (AP20)
        
        if (sta20APIdx < nMeshAPs && sadiaAPIdx < nMeshAPs) {
            // Discover route for Sadia → STA20
            meshRoute_SadiaToSTA20 = DiscoverMeshRoute(sadiaAPIdx, sta20APIdx, gridSize);
        }
    }
    
    // Setup IP-level tracing on all mesh APs (one-time setup for all flows)
    SetupIPLevelTracing(meshAPNodes);

    // ========== BUILDINGS/OBSTACLES (Optional) ==========
    if (useObstacles) {
        std::cout << "\n=== Creating Strategic Obstacles ===" << std::endl;
        
        // STRATEGY: Very low buildings for minimal signal attenuation
        // APs at 20m height, buildings at 5m to add realistic ground clutter
        
        // Building 1: Small obstacle near AP6
        Ptr<Building> building1 = CreateObject<Building>();
        building1->SetBoundaries(Box(78.0, 92.0, 78.0, 92.0, 0.0, 5.0));  // 5m tall
        std::cout << "  Building 1: (78-92, 78-92, 0-5m) - near AP6" << std::endl;
        
        // Building 2: Small obstacle at center
        Ptr<Building> building2 = CreateObject<Building>();
        building2->SetBoundaries(Box(163.0, 177.0, 163.0, 177.0, 0.0, 6.0));  // 6m tall
        std::cout << "  Building 2: (163-177, 163-177, 0-6m) - center, near AP12" << std::endl;
        
        // Building 3: Small obstacle near AP18
        Ptr<Building> building3 = CreateObject<Building>();
        building3->SetBoundaries(Box(248.0, 262.0, 248.0, 262.0, 0.0, 5.0));  // 5m tall
        std::cout << "  Building 3: (248-262, 248-262, 0-5m) - near AP18" << std::endl;
        
        // Install buildings on all nodes to calculate propagation loss
        NodeContainer allNodes;
        allNodes.Add(meshAPNodes);
        allNodes.Add(staNodes);
        allNodes.Add(internetNode);
        allNodes.Add(externalServer);
        BuildingsHelper::Install(allNodes);
        
        std::cout << "Created 3 buildings (5-6m tall, APs at 20m)" << std::endl;
        std::cout << "Buildings: Visual markers only (for NetAnim visualization)" << std::endl;
        std::cout << "Propagation: Default LogDistance model (no additional attenuation)" << std::endl;
    } else {
        std::cout << "\n=== No Obstacles (Buildings disabled)" << std::endl;
    }

    // ========== APPLICATION SETUP ==========
    std::cout << "\n=== Setting Up Applications ===" << std::endl;
    
    Ipv4Address sayedIP = staInterfaces[0].GetAddress(0);
    Ipv4Address sadiaIP = staInterfaces[1].GetAddress(0);
    Ipv4Address externalServerIP = externalInterfaces.GetAddress(1);
    
    std::cout << "Sayed IP: " << sayedIP << std::endl;
    std::cout << "Sadia IP: " << sadiaIP << std::endl;
    std::cout << "External Server IP: " << externalServerIP << std::endl;

    // ========== REGISTER FLOWS FOR PER-HOP TRACKING ==========
    std::cout << "\n=== Registering Flows for Per-Hop Analysis ===" << std::endl;
    
    // Register Sayed → External Server flow
    RegisterFlow("Sayed → External Server", sayedIP, externalServerIP, meshRoute_SayedToExternal, nMeshAPs);
    
    // Register Sadia → External Server flow (goes through mesh to AP0)
    if (nSTAs > 1) {
        uint32_t sadiaAPIdx = apIndices[1];  // Dynamically get Sadia's AP (lastAPIdx)
        std::vector<uint32_t> meshRoute_SadiaToExternal = DiscoverMeshRoute(sadiaAPIdx, 0, gridSize);
        RegisterFlow("Sadia → External Server", sadiaIP, externalServerIP, meshRoute_SadiaToExternal, nMeshAPs);
    }
    
    // Register Sadia → STA20 flow (if route was discovered)
    if (!meshRoute_SadiaToSTA20.empty() && nSTAs > 2) {
        Ipv4Address sta20IP = staInterfaces[2].GetAddress(0);  // 192.168.3.2
        RegisterFlow("Sadia → STA20", sadiaIP, sta20IP, meshRoute_SadiaToSTA20, nMeshAPs);
    }

    bool useTCP = (trafficType == "tcp" || trafficType == "both");
    bool useUDP = (trafficType == "udp" || trafficType == "both");
    bool useBulkSend = (packetSizeKB >= 1024);  // Use BulkSend for packets >= 1 MB

    if (useBulkSend) {
        std::cout << "\nUsing BulkSendApplication (packet size >= 1 MB)" << std::endl;
    } else {
        std::cout << "\nUsing OnOffApplication (packet size < 1 MB)" << std::endl;
    }

    // ========== SCENARIO 1: SAYED → EXTERNAL SERVER ==========
    ApplicationContainer sayedServerTCP, sayedServerUDP;
    SetupSayedToServerFlow(staNodes, externalServer, externalServerIP,
                           sayedServerTCP, sayedServerUDP,
                           useTCP, useUDP, useBulkSend, packetSize,
                           tcpPort, udpPort, simTime);

    // ========== SCENARIO 2: SADIA → EXTERNAL SERVER ==========
    ApplicationContainer externalServerTCP, externalServerUDP;
    // Sadia → External Server flow (goes through mesh to AP0, then CSMA → External)
    SetupSadiaToServerFlow(staNodes, externalServer, externalServerIP,
                           externalServerTCP, externalServerUDP,
                           useTCP, useUDP, useBulkSend, packetSize,
                           tcpPort, udpPort, simTime);
    
    // ========== SCENARIO 3: SADIA → STA20 (Intra-mesh) ==========
    ApplicationContainer sta20ServerTCP, sta20ServerUDP;
    
    if (nSTAs > 2) {
        std::cout << "\n=== Scenario 3: Sadia → STA20 (Intra-mesh communication) ===" << std::endl;
        
        Ipv4Address sta20IP = staInterfaces[2].GetAddress(0);
        std::cout << "STA20 IP: " << sta20IP << std::endl;
        
        // TCP Sink on STA20 (receives from Sadia)
    if (useTCP) {
            PacketSinkHelper tcpSta20Sink("ns3::TcpSocketFactory",
                                        InetSocketAddress(Ipv4Address::GetAny(), tcpPort + 200));
            sta20ServerTCP = tcpSta20Sink.Install(staNodes.Get(2));  // STA20
            sta20ServerTCP.Start(Seconds(0.5));
            sta20ServerTCP.Stop(Seconds(simTime));
            sta20ServerTCP.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&RxTrace));
            std::cout << "  STA20 TCP Sink: Port " << (tcpPort + 200) << std::endl;
        }
        
        // UDP Sink on STA20 (receives from Sadia)
    if (useUDP) {
            PacketSinkHelper udpSta20Sink("ns3::UdpSocketFactory",
                                        InetSocketAddress(Ipv4Address::GetAny(), udpPort + 200));
            sta20ServerUDP = udpSta20Sink.Install(staNodes.Get(2));  // STA20
            sta20ServerUDP.Start(Seconds(0.5));
            sta20ServerUDP.Stop(Seconds(simTime));
            sta20ServerUDP.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&RxTrace));
            std::cout << "  STA20 UDP Sink: Port " << (udpPort + 200) << std::endl;
        }
        
        // TCP Client on Sadia (sends to STA20)
    if (useTCP) {
        if (useBulkSend) {
            BulkSendHelper bulkSend("ns3::TcpSocketFactory",
                                        InetSocketAddress(sta20IP, tcpPort + 200));
                bulkSend.SetAttribute("MaxBytes", UintegerValue(packetSize * 100));
                ApplicationContainer tcpSta20App = bulkSend.Install(staNodes.Get(1));  // Sadia
                tcpSta20App.Start(Seconds(7.0));
                tcpSta20App.Stop(Seconds(simTime - 1.0));
                tcpSta20App.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
                std::cout << "  Sadia → STA20 (TCP/BulkSend): 7.0s to " << (simTime-1.0) << "s, " 
                      << (packetSize * 100 / 1024 / 1024) << " MB total" << std::endl;
        } else {
                OnOffHelper tcpSta20Client("ns3::TcpSocketFactory",
                                          InetSocketAddress(sta20IP, tcpPort + 200));
                tcpSta20Client.SetConstantRate(DataRate("1Mbps"), packetSize);
                tcpSta20Client.SetAttribute("StartTime", TimeValue(Seconds(7.0)));
                tcpSta20Client.SetAttribute("StopTime", TimeValue(Seconds(simTime - 1.0)));
                ApplicationContainer tcpSta20App = tcpSta20Client.Install(staNodes.Get(1));  // Sadia
                tcpSta20App.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
                std::cout << "  Sadia → STA20 (TCP/OnOff): 7.0s to " << (simTime-1.0) << "s @ 1Mbps" << std::endl;
            }
        }
        
        // UDP Client on Sadia (sends to STA20)
    if (useUDP) {
            OnOffHelper udpSta20Client("ns3::UdpSocketFactory",
                                      InetSocketAddress(sta20IP, udpPort + 200));
            udpSta20Client.SetConstantRate(DataRate("500Kbps"), packetSize);
            udpSta20Client.SetAttribute("StartTime", TimeValue(Seconds(7.5)));
            udpSta20Client.SetAttribute("StopTime", TimeValue(Seconds(simTime - 1.0)));
            ApplicationContainer udpSta20App = udpSta20Client.Install(staNodes.Get(1));  // Sadia
            udpSta20App.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
            std::cout << "  Sadia → STA20 (UDP): 7.5s to " << (simTime-1.0) << "s @ 500Kbps" << std::endl;
        }
    }
    
    std::cout << "\n" << (nSTAs > 2 ? "Three" : "Two") << " scenarios configured:" << std::endl;
    std::cout << "  1. Sayed → External Server (via Internet)" << std::endl;
    std::cout << "  2. Sadia → External Server (via Internet)" << std::endl;
    if (nSTAs > 2) {
        std::cout << "  3. Sadia → STA20 (Intra-mesh, via mesh backhaul)" << std::endl;
    }

    // ========== ENABLE TRACING ==========
    std::cout << "\n=== Enabling Traces ===" << std::endl;
    
    AsciiTraceHelper ascii;
    meshPhy.EnableAsciiAll(ascii.CreateFileStream(outputDir + "mesh_backhaul.tr"));
    
    meshPhy.EnablePcapAll(outputDir + "mesh", true);
    csma.EnablePcapAll(outputDir + "csma", true);
    p2p.EnablePcapAll(outputDir + "external", true);
    
    std::cout << "Enabled PCAP and ASCII tracing" << std::endl;

    // ========== FLOW MONITOR ==========
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.InstallAll();

    // ========== RUN SIMULATION ==========
    std::cout << "\n=== Starting Simulation ===" << std::endl;
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    // ========== GENERATE MESH REPORTS ==========
    std::cout << "\nGenerating mesh point reports..." << std::endl;
    for (uint32_t n = 0; n < meshDevices.GetN(); ++n)
    {
        std::ostringstream os;
        os << outputDir << "mp-report-" << n << ".xml";
        std::ofstream of(os.str().c_str());
        if (of.is_open()) {
            mesh.Report(meshDevices.Get(n), of);
            of.close();
        }
    }
    std::cout << "Generated " << meshDevices.GetN() << " mesh point reports" << std::endl;

    // ========== PRINT STATISTICS ==========
    std::cout << "\n\n========== RESULTS ==========" << std::endl;
    
    // Get application-level data
    uint64_t s1_tcp = 0, s1_udp = 0, s2_tcp = 0, s2_udp = 0, s3_tcp = 0, s3_udp = 0;
    
    if (useTCP && sayedServerTCP.GetN() > 0) {
        s1_tcp = DynamicCast<PacketSink>(sayedServerTCP.Get(0))->GetTotalRx();
    }
    if (useUDP && sayedServerUDP.GetN() > 0) {
        s1_udp = DynamicCast<PacketSink>(sayedServerUDP.Get(0))->GetTotalRx();
    }
    if (useTCP && externalServerTCP.GetN() > 0) {
        s2_tcp = DynamicCast<PacketSink>(externalServerTCP.Get(0))->GetTotalRx();
    }
    if (useUDP && externalServerUDP.GetN() > 0) {
        s2_udp = DynamicCast<PacketSink>(externalServerUDP.Get(0))->GetTotalRx();
    }
    if (nSTAs > 2) {
        if (useTCP && sta20ServerTCP.GetN() > 0) {
            s3_tcp = DynamicCast<PacketSink>(sta20ServerTCP.Get(0))->GetTotalRx();
        }
        if (useUDP && sta20ServerUDP.GetN() > 0) {
            s3_udp = DynamicCast<PacketSink>(sta20ServerUDP.Get(0))->GetTotalRx();
        }
    }
    
    // std::cout << "\n[Scenario 1: Sayed → External Server]" << std::endl;
    // std::cout << "  TCP: " << (s1_tcp/1024.0) << " KB" << std::endl;
    // std::cout << "  UDP: " << (s1_udp/1024.0) << " KB" << std::endl;
    
    // std::cout << "\n[Scenario 2: Sadia → External Server]" << std::endl;
    // std::cout << "  TCP: " << (s2_tcp/1024.0) << " KB" << std::endl;
    // std::cout << "  UDP: " << (s2_udp/1024.0) << " KB" << std::endl;
    
    if (nSTAs > 2) {
        std::cout << "\n[Scenario 3: Sadia → STA20 (Intra-mesh)]" << std::endl;
        std::cout << "  TCP: " << (s3_tcp/1024.0) << " KB" << std::endl;
        std::cout << "  UDP: " << (s3_udp/1024.0) << " KB" << std::endl;
    }
    
    std::cout << "\n[Total]" << std::endl;
    std::cout << "  All Data: " << ((s1_tcp + s1_udp + s2_tcp + s2_udp + s3_tcp + s3_udp)/1024.0) << " KB" << std::endl;
    
    std::cout << "\n=== PACKET TRACE STATISTICS ===" << std::endl;
    std::cout << "Total TX packets (traced): " << g_txPackets << std::endl;
    std::cout << "Total RX packets (traced): " << g_rxPackets << std::endl;
    if (g_txPackets > 0) {
        std::cout << "Delivery ratio: " << (g_rxPackets * 100.0 / g_txPackets) << "%" << std::endl;
    }

    // ========== FLOW MONITOR RESULTS ==========
    monitor->CheckForLostPackets();
    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats();

    std::cout << "\n========== DETAILED METRICS ==========" << std::endl;

    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(flowmon.GetClassifier());
    
    // Analyze each scenario using encapsulated function
    AnalyzeFlow("Scenario 1: Sayed → External Server",
                Ipv4Address("192.168.1.2"), Ipv4Address("200.1.1.2"),
                stats, classifier, tcpPort, udpPort, simTime);
    
    AnalyzeFlow("Scenario 2: Sadia → External Server",
                Ipv4Address("192.168.2.2"), Ipv4Address("200.1.1.2"),
                stats, classifier, tcpPort + 100, udpPort + 100, simTime);
    
    if (nSTAs > 2) {
        AnalyzeFlow("Scenario 3: Sadia → STA20 (Intra-mesh)",
                    Ipv4Address("192.168.2.2"), Ipv4Address("192.168.3.2"),
                    stats, classifier, tcpPort + 200, udpPort + 200, simTime);
    }

    // Save FlowMonitor results
    monitor->SerializeToXmlFile(outputDir + "flowmonitor.xml", true, true);

    // Analyze hop count from mesh trace
    AnalyzeHopCount(outputDir + "mesh_backhaul.tr");
    
    // Analyze per-hop statistics for all tracked flows
    if (!g_trackedFlows.empty()) {
        std::string meshTraceFile = outputDir + "/mesh_backhaul.tr";
        AnalyzeAllFlows(nMeshAPs, meshTraceFile);
    }

    std::cout << "\n=== SIMULATION COMPLETED ===" << std::endl;
    std::cout << "\nResults saved to " << outputDir << ":" << std::endl;
    std::cout << "  - Mesh Reports: mp-report-*.xml (" << nMeshAPs << " files)" << std::endl;
    std::cout << "  - FlowMonitor: flowmonitor.xml" << std::endl;
    std::cout << "  - Mesh backhaul trace: mesh_backhaul.tr" << std::endl;
    std::cout << "  - PCAP traces: mesh-*.pcap, csma-*.pcap, external-*.pcap" << std::endl;
    
    std::cout << "\n=== TOPOLOGY SUMMARY ===" << std::endl;
    std::cout << "Device: " << meshCfg.name << std::endl;
    std::cout << "External Server (200.1.1.2)" << std::endl;
    std::cout << "        │" << std::endl;
    std::cout << "      P2P (1Gbps, 10ms)" << std::endl;
    std::cout << "        │" << std::endl;
    std::cout << "Internet Gateway (172.16.1.1 / 200.1.1.1)" << std::endl;
    std::cout << "        │" << std::endl;
    std::cout << "      CSMA (100Mbps, 2ms)" << std::endl;
    std::cout << "        │" << std::endl;
    std::cout << "AP0 ←mesh(" << apSpacing << "m)→ AP1...AP" << (lastAPIdx-1) << " ←mesh→ AP" << lastAPIdx << std::endl;
    std::cout << " ↓WiFi                                           ↓WiFi" << std::endl;
    std::cout << "Sayed(STA)                                    Sadia(STA)" << std::endl;
    std::cout << "\nGrid: " << gridSize << "x" << gridSize << " (" << nMeshAPs << " mesh APs)" << std::endl;
    std::cout << "Coverage: " << (gridSize - 1) * apSpacing << "m x " << (gridSize - 1) * apSpacing << "m" << std::endl;
    std::cout << "\n3D Layout:" << std::endl;
    std::cout << "  Height 25m: ─────────────────────────── Sadia (STA)" << std::endl;
    std::cout << "  Height " << apHeight << "m: AP0───AP1───...───AP" << lastAPIdx << " (Mesh APs)" << std::endl;
    std::cout << "  Height 15m: ─ Sayed (STA)" << std::endl;

    Simulator::Destroy();
    return 0;
}
