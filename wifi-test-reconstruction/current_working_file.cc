
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
#include "ns3/animation-interface.h"

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
            // Default: MEDIUM POWER configuration for 100m range
            // 20 dBm TX power + 3 dB antenna gains for realistic mesh connectivity
            return MeshAPConfig(
                "Default Medium Power Config",
                "Medium-power deployment (100m range coverage)",
                20.0,                           // txPowerStart (dBm) - Set for ~100m range
                20.0,                           // txPowerEnd (dBm) - Set for ~100m range
                -96.0,                          // rxSensitivity (dBm)
                3.0,                            // rxGain (dB) - Antenna gain
                3.0,                            // txGain (dB) - Antenna gain
                "WIFI_STANDARD_80211n",         // WiFi standard
                "HtMcs7",                       // Data mode (802.11n HT MCS7)
                1,                              // numInterfaces (keep at 1 to avoid channel conflicts)
                100.0,                          // meshRange (m)
                15.0,                           // apHeight (m) - 3D coverage consideration
                70.0,                           // apSpacing (m) - REDUCED for more hops
                6                               // gridSize (6x6 = 36 APs) - INCREASED for 70m spacing
            );
            // Coverage: (6-1) × 70 = 350m × 350m with multihop routing
            // 3D distance: √(70² + 15²) = 71.6m (requires routing for most paths)
    }
}

// Global trace counters (still tracked by callbacks but not displayed)
uint32_t g_txPackets = 0;
uint32_t g_rxPackets = 0;

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

// Write configuration to JSON file for parser integration
void WriteConfigJson(const std::string& jsonPath,
                     const std::string& scenario,
                     uint32_t gridSize, double apSpacing, double apHeight,
                     uint32_t nMeshAPs,
                     const std::string& wifiStandard, const std::string& dataMode,
                     double txPower, double rxSensitivity, double rxGain, double txGain,
                     uint32_t nSTAs, uint32_t packetSizeBytes,
                     const std::string& trafficType, double simTime,
                     const std::string& srcIp, const std::string& dstIp,
                     uint16_t tcpPort, uint16_t udpPort,
                     bool useTCP, bool useUDP,
                     const std::string& xmlFile, const std::string& trFile,
                     const std::string& flowmonFile, const std::string& routesFile)
{
    std::ofstream out(jsonPath.c_str());
    if (!out.is_open()) {
        std::cerr << "Warning: Could not write config.json to " << jsonPath << std::endl;
        return;
    }

    out << "{\n";
    out << "  \"network_topology\": {\n";
    out << "    \"grid_width\": " << gridSize << ",\n";
    out << "    \"num_nodes\": " << nMeshAPs << ",\n";
    out << "    \"node_spacing_meters\": " << apSpacing << ",\n";
    out << "    \"ap_height_meters\": " << apHeight << "\n";
    out << "  },\n";
    out << "  \"mesh_configuration\": {\n";
    out << "    \"wifi_standard\": \"" << wifiStandard << "\",\n";
    out << "    \"data_mode\": \"" << dataMode << "\",\n";
    out << "    \"tx_power_dbm\": " << txPower << ",\n";
    out << "    \"rx_sensitivity_dbm\": " << rxSensitivity << ",\n";
    out << "    \"rx_gain_db\": " << rxGain << ",\n";
    out << "    \"tx_gain_db\": " << txGain << "\n";
    out << "  },\n";
    out << "  \"traffic_configuration\": {\n";
    out << "    \"scenario\": \"" << scenario << "\",\n";
    out << "    \"n_stas\": " << nSTAs << ",\n";
    out << "    \"traffic_type\": \"" << trafficType << "\",\n";
    out << "    \"use_tcp\": " << (useTCP ? "true" : "false") << ",\n";
    out << "    \"use_udp\": " << (useUDP ? "true" : "false") << ",\n";
    out << "    \"packet_size_bytes\": " << packetSizeBytes << ",\n";
    out << "    \"sim_time_seconds\": " << simTime << "\n";
    out << "  },\n";
    out << "  \"ip_configuration\": {\n";
    out << "    \"source_ip\": \"" << srcIp << "\",\n";
    out << "    \"destination_ip\": \"" << dstIp << "\"\n";
    out << "  },\n";
    out << "  \"port_information\": {\n";
    out << "    \"tcp_port\": " << tcpPort << ",\n";
    out << "    \"udp_port\": " << udpPort << "\n";
    out << "  },\n";
    out << "  \"output_files\": {\n";
    out << "    \"xml_file\": \"" << xmlFile << "\",\n";
    out << "    \"tr_file\": \"" << trFile << "\",\n";
    out << "    \"flowmonitor_file\": \"" << flowmonFile << "\",\n";
    out << "    \"routes_file\": \"" << routesFile << "\"\n";
    out << "  }\n";
    out << "}\n";

    out.close();
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
    // TCP: Setup both server (receiver) and client (sender)
    if (useTCP) {
        // TCP Sink on External Server (receives from Sadia)
        PacketSinkHelper tcpExtSink("ns3::TcpSocketFactory",
                                    InetSocketAddress(Ipv4Address::GetAny(), tcpPort + 100));
        sadiaServerTCP = tcpExtSink.Install(externalServer.Get(0));
        sadiaServerTCP.Start(Seconds(0.5));
        sadiaServerTCP.Stop(Seconds(simTime));
        sadiaServerTCP.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&RxTrace));
        
        // TCP Client on Sadia (sends to External Server) - SINGLE PACKET
        BulkSendHelper bulkSend("ns3::TcpSocketFactory",
                               InetSocketAddress(externalServerIP, tcpPort + 100));
        bulkSend.SetAttribute("MaxBytes", UintegerValue(packetSize));  // SINGLE PACKET
        ApplicationContainer tcpExtApp = bulkSend.Install(staNodes.Get(1));  // Sadia
        tcpExtApp.Start(Seconds(6.0));
        tcpExtApp.Stop(Seconds(simTime - 1.0));
        tcpExtApp.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TxTrace));
    }
    
    // UDP: Setup both server (receiver) and client (sender)
    if (useUDP) {
        // UDP Server on External Server (receives from Sadia)
        UdpServerHelper udpServer(udpPort + 100);
        sadiaServerUDP = udpServer.Install(externalServer.Get(0));
        sadiaServerUDP.Start(Seconds(0.5));
        sadiaServerUDP.Stop(Seconds(simTime));
        
        // UDP Client on Sadia (sends to External Server) - SINGLE PACKET
        // UdpClient has max packet size limit (~65KB), cap it
        uint32_t udpPacketSize = std::min(packetSize, (uint32_t)65000);
        
        UdpClientHelper udpClient(externalServerIP, udpPort + 100);
        udpClient.SetAttribute("MaxPackets", UintegerValue(1));  // Only 1 packet
        udpClient.SetAttribute("Interval", TimeValue(Seconds(1.0)));
        udpClient.SetAttribute("PacketSize", UintegerValue(udpPacketSize));
        
        ApplicationContainer udpExtApp = udpClient.Install(staNodes.Get(1));  // Sadia
        udpExtApp.Start(Seconds(2.0));
        udpExtApp.Stop(Seconds(simTime - 1.0));
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

    // ========== NETANIM SETUP ==========
    std::cout << "\n=== Setting Up NetAnim Visualization ===" << std::endl;
    
    AnimationInterface anim(outputDir + "mesh_backhaul_anim.xml");
    
    // Enable packet metadata to track packet contents and headers
    anim.EnablePacketMetadata(true);
    
    // Enable IP routing tracking to see routing decisions
    anim.EnableIpv4RouteTracking(outputDir + "mesh_backhaul_routes.xml", 
                                  Seconds(0), Seconds(simTime), Seconds(1));
    
    // Enable WiFi counters for detailed MAC/PHY statistics
    anim.EnableWifiMacCounters(Seconds(0), Seconds(simTime));
    anim.EnableWifiPhyCounters(Seconds(0), Seconds(simTime));
    
    // Set node descriptions for better visualization
    anim.UpdateNodeDescription(internetNode.Get(0), "Internet-Gateway");
    anim.UpdateNodeDescription(externalServer.Get(0), "External-Server");
    for (uint32_t i = 0; i < nMeshAPs; i++) {
        anim.UpdateNodeDescription(meshAPNodes.Get(i), "AP" + std::to_string(i));
    }
    for (uint32_t i = 0; i < nSTAs; i++) {
        std::string staName = (i == 0) ? "Sayed" : (i == 1) ? "Sadia" : (i == 2) ? "STA20" : ("STA" + std::to_string(i));
        anim.UpdateNodeDescription(staNodes.Get(i), staName);
    }
    
   

    // ========== APPLICATION SETUP ==========
    std::cout << "\n=== Setting Up Applications ===" << std::endl;
    
    Ipv4Address sayedIP = staInterfaces[0].GetAddress(0);
    Ipv4Address sadiaIP = staInterfaces[1].GetAddress(0);
    Ipv4Address externalServerIP = externalInterfaces.GetAddress(1);
    
    std::cout << "Sayed IP: " << sayedIP << std::endl;
    std::cout << "Sadia IP: " << sadiaIP << std::endl;
    std::cout << "External Server IP: " << externalServerIP << std::endl;

  

    bool useTCP = (trafficType == "tcp" || trafficType == "both");
    bool useUDP = (trafficType == "udp" || trafficType == "both");
    bool useBulkSend = (packetSizeKB >= 1024);  // Use BulkSend for packets >= 1 MB

    if (useBulkSend) {
        std::cout << "\nUsing BulkSendApplication (packet size >= 1 MB)" << std::endl;
    } else {
        std::cout << "\nUsing OnOffApplication (packet size < 1 MB)" << std::endl;
    }

    // ========== SCENARIO 1: SAYED → EXTERNAL SERVER ==========
    // ApplicationContainer sayedServerTCP, sayedServerUDP;
    // SetupSayedToServerFlow(staNodes, externalServer, externalServerIP,
    //                        sayedServerTCP, sayedServerUDP,
    //                        useTCP, useUDP, useBulkSend, packetSize,
    //                        tcpPort, udpPort, simTime);

    // ========== SCENARIO 2: SADIA → EXTERNAL SERVER ==========
    ApplicationContainer externalServerTCP, externalServerUDP;
    // Sadia → External Server flow (goes through mesh to AP0, then CSMA → External)
    SetupSadiaToServerFlow(staNodes, externalServer, externalServerIP,
                           externalServerTCP, externalServerUDP,
                           useTCP, useUDP, useBulkSend, packetSize,
                           tcpPort, udpPort, simTime);
    
 
   
    // ========== WRITE CONFIG.JSON FOR PARSER ==========
    {
        std::string jsonPath = "wifi-test-reconstruction/config.json";
        std::string xmlFile = outputDir + "mesh_backhaul_anim.xml";
        std::string trFile = outputDir + "mesh_backhaul.tr";
        std::string flowmonFile = outputDir + "flowmonitor.xml";
        std::string routesFile = outputDir + "mesh_backhaul_routes.xml";
        
        // Convert IP addresses to strings
        std::ostringstream ossSource, ossDest;
        sadiaIP.Print(ossSource);
        externalServerIP.Print(ossDest);
        
        // Write config for Scenario 2 (Sadia -> External) which is currently active
        WriteConfigJson(
            jsonPath,
            "Sadia->External",
            gridSize, apSpacing, apHeight,
            nMeshAPs,
            meshCfg.wifiStandard, meshCfg.dataMode,
            meshCfg.txPowerStart, meshCfg.rxSensitivity, meshCfg.rxGain, meshCfg.txGain,
            nSTAs, packetSize,
            trafficType, simTime,
            ossSource.str(), ossDest.str(),
            tcpPort + 100, udpPort + 100,  // Scenario 2 port offsets
            useTCP, useUDP,
            xmlFile, trFile, flowmonFile, routesFile
        );
        std::cout << "\n✓ Wrote configuration to " << jsonPath << std::endl;
    }

    // ========== ENABLE TRACING ==========
    std::cout << "\n=== Enabling Traces ===" << std::endl;
    
    AsciiTraceHelper ascii;
    meshPhy.EnableAsciiAll(ascii.CreateFileStream(outputDir + "mesh_backhaul.tr"));


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
    

    // ========== FLOW MONITOR RESULTS ==========
    monitor->CheckForLostPackets();
    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats();

    std::cout << "\n========== FLOWMONITOR STATISTICS ==========" << std::endl;

    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(flowmon.GetClassifier());
    

    AnalyzeFlow("Scenario 2: Sadia → External Server",
                Ipv4Address("192.168.2.2"), Ipv4Address("200.1.1.2"),
                stats, classifier, tcpPort + 100, udpPort + 100, simTime);
 

    // Save FlowMonitor results
    monitor->SerializeToXmlFile(outputDir + "flowmonitor.xml", true, true);


    std::cout << "\n=== SIMULATION COMPLETED ===" << std::endl;
    std::cout << "\nResults saved to " << outputDir << ":" << std::endl;
    std::cout << "  - Mesh Reports: mp-report-*.xml (" << nMeshAPs << " files)" << std::endl;
    std::cout << "  - FlowMonitor: flowmonitor.xml" << std::endl;
    std::cout << "  - Mesh backhaul trace: mesh_backhaul.tr (ASCII)" << std::endl;
    std::cout << "  - NetAnim visualization: mesh_backhaul_anim.xml" << std::endl;
    std::cout << "  - IP route tracking: mesh_backhaul_routes.xml" << std::endl;
    
  

    Simulator::Destroy();
    return 0;
}
