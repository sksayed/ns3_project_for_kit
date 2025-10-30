
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mesh-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/ipv4-flow-classifier.h"
#include "ns3/buildings-module.h"
#include "ns3/olsr-helper.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TcpMeshBackhaulMode");

int main(int argc, char *argv[])
{
    // Enable packet metadata
    PacketMetadata::Enable();

    // Enable logging
    LogComponentEnable("BulkSendApplication", LOG_LEVEL_INFO);
    LogComponentEnable("PacketSink", LOG_LEVEL_INFO);

    // Simulation parameters
    const double simTime = 15.0;         // Increased from 10 to 15 seconds
    const uint16_t tcpPort = 7000;
    const uint16_t udpPort = 8000;
    const double field = 450.0;          // Field size for 9 APs
    
    // Optimized 9 AP configuration (3×3 grid)
    const uint32_t gridSize = 3;
    const uint32_t nMeshHops = 9;        // 3×3 = 9 APs
    const double apSpacing = 150.0;      // Spacing that works with optimized ranges
    const uint32_t nStaPerMesh = 0;      // No STAs
    const uint32_t nTotalStas = 0;
    std::string outputDir = "wifi_mesh_backhaul_outputs/";
    
    // Variable WiFi ranges (optimized for Sayed/Sadia)
    // Corner APs near endpoints: larger range
    // Center and edges: medium range
    std::vector<double> apRanges = {
        145.0,  // AP0 - Sayed corner (bottom-left)
        120.0,  // AP1 - Edge
        100.0,  // AP2 - Far corner
        120.0,  // AP3 - Edge
        170.0,  // AP4 - Center (key relay)
        120.0,  // AP5 - Edge
        100.0,  // AP6 - Far corner
        120.0,  // AP7 - Edge
        145.0   // AP8 - Sadia corner (top-right)
    };

    std::cout << "=== TCP+UDP WiFi Mesh Test - Optimized 9 AP Design ===" << std::endl;
    std::cout << "Simulation time: " << simTime << " seconds" << std::endl;
    std::cout << "Field size: " << field << "m x " << field << "m" << std::endl;
    std::cout << "Grid: " << gridSize << " x " << gridSize << " = " << nMeshHops << " APs (optimized ranges)" << std::endl;
    std::cout << "AP Spacing: " << apSpacing << " meters (minimal overlap)" << std::endl;
    std::cout << "AP Ranges: 100-170m (variable, optimized for Sayed/Sadia)" << std::endl;
    std::cout << "Sayed & Sadia: MOBILE (Random Walk, 15 m/s)" << std::endl;
    std::cout << "Traffic: TCP at 2,5,8,11,14s + UDP at 4,6,8,10s (bidirectional)" << std::endl;
    std::cout << "Output directory: " << outputDir << std::endl;

    // Create nodes
    NodeContainer backhaulNodes;    // Backhaul/gateway
    NodeContainer meshNodes;        // Mesh AP nodes
    NodeContainer staNodes;         // STA nodes
    NodeContainer sayedSadiaNodes;  // Sayed and Sadia
    NodeContainer allMeshNodes;     // All nodes in mesh

    backhaulNodes.Create(1);
    meshNodes.Create(nMeshHops);
    staNodes.Create(nTotalStas);
    sayedSadiaNodes.Create(2);  // Sayed=0, Sadia=1

    // Combine mesh nodes (backhaul + mesh APs + STAs + Sayed & Sadia)
    allMeshNodes.Add(backhaulNodes);
    allMeshNodes.Add(meshNodes);
    allMeshNodes.Add(staNodes);
    allMeshNodes.Add(sayedSadiaNodes);

    std::cout << "Created nodes: " << allMeshNodes.GetN() << " total" << std::endl;

    // Mobility setup
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> positionAlloc = CreateObject<ListPositionAllocator>();

    // Position backhaul at center top
    positionAlloc->Add(Vector(field/2, field/2, 15.0));

    // Position 9 mesh APs in 3×3 grid with optimized ranges
    const double offset = apSpacing / 2.0;
    
    std::cout << "\nOptimized 9 AP Grid (3×3):" << std::endl;
    for (uint32_t row = 0; row < gridSize; ++row) {
        for (uint32_t col = 0; col < gridSize; ++col) {
            uint32_t apIdx = row * gridSize + col;
            double x = offset + col * apSpacing;
            double y = offset + row * apSpacing;
            positionAlloc->Add(Vector(x, y, 5.0));
            
            std::cout << "  AP" << apIdx << ": (" << x << ", " << y << ") - Range: " 
                      << apRanges[apIdx] << "m";
            if (apIdx == 0) std::cout << " (Sayed area)";
            else if (apIdx == 8) std::cout << " (Sadia area)";
            else if (apIdx == 4) std::cout << " (Center relay)";
            std::cout << std::endl;
        }
    }

    // Position Sayed and Sadia near their designated corner APs (within field bounds)
    double sayedX = offset + 5.0;  // Near AP0
    double sayedY = offset + 5.0;
    double sadiaX = offset + (gridSize - 1) * apSpacing - 5.0;  // Near AP8
    double sadiaY = offset + (gridSize - 1) * apSpacing - 5.0;
    
    positionAlloc->Add(Vector(sayedX, sayedY, 1.5));       // Sayed - near AP0
    positionAlloc->Add(Vector(sadiaX, sadiaY, 1.5));       // Sadia - near AP8
    
    std::cout << "\nEndpoint Positions:" << std::endl;
    std::cout << "  Sayed: (" << sayedX << ", " << sayedY << ") - mobile, near AP0 (145m range)" << std::endl;
    std::cout << "  Sadia: (" << sadiaX << ", " << sadiaY << ") - mobile, near AP8 (145m range)" << std::endl;
    std::cout << "  Diagonal distance: ~" << std::sqrt((sadiaX-sayedX)*(sadiaX-sayedX) + (sadiaY-sayedY)*(sadiaY-sayedY)) << " meters" << std::endl;

    mobility.SetPositionAllocator(positionAlloc);
    
    // Install static mobility for backhaul, mesh APs, and STAs
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(backhaulNodes);
    mobility.Install(meshNodes);
    mobility.Install(staNodes);
    
    // Install random walk mobility for Sayed and Sadia with faster speed
    mobility.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
                              "Bounds", RectangleValue(Rectangle(0, field, 0, field)),
                              "Time", TimeValue(Seconds(2.0)),  // Change direction every 2 seconds
                              "Speed", StringValue("ns3::ConstantRandomVariable[Constant=15.0]"),  // 15 m/s (~54 km/h)
                              "Distance", DoubleValue(50.0));  // Walk 50m before changing direction
    mobility.Install(sayedSadiaNodes);

    std::cout << "Positioned all nodes (Sayed & Sadia: MOBILE with Random Walk)" << std::endl;

    // Create buildings/obstacles
    Ptr<Building> leftBelow = CreateObject<Building>();
    leftBelow->SetBoundaries(Box(0.0, 60.0, 96.0, 104.0, 0.0, 10.0));

    Ptr<Building> rightBelow = CreateObject<Building>();
    rightBelow->SetBoundaries(Box(340.0, 400.0, 96.0, 104.0, 0.0, 10.0));

    Ptr<Building> leftAbove = CreateObject<Building>();
    leftAbove->SetBoundaries(Box(0.0, 60.0, 296.0, 304.0, 0.0, 10.0));

    Ptr<Building> rightAbove = CreateObject<Building>();
    rightAbove->SetBoundaries(Box(340.0, 400.0, 296.0, 304.0, 0.0, 10.0));

    Ptr<Building> cluster250a = CreateObject<Building>();
    cluster250a->SetBoundaries(Box(80.0, 140.0, 220.0, 228.0, 0.0, 15.0));

    Ptr<Building> cluster250b = CreateObject<Building>();
    cluster250b->SetBoundaries(Box(170.0, 250.0, 220.0, 228.0, 0.0, 12.0));

    Ptr<Building> cluster50 = CreateObject<Building>();
    cluster50->SetBoundaries(Box(255.0, 335.0, 20.0, 28.0, 0.0, 18.0));

    BuildingsHelper::Install(allMeshNodes);
    
    std::cout << "Created 7 buildings as obstacles" << std::endl;

    // Note: ns-3 mesh doesn't support per-node range easily, so we use maximum range needed
    // For 150m spacing with minimal overlap, need at least 151m range
    const double avgOptimizedRange = 155.0;  // Allows 150m spacing + 5m overlap
    
    // WiFi channel with building propagation loss
    YansWifiChannelHelper wifiChannel;
    wifiChannel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    wifiChannel.AddPropagationLoss("ns3::HybridBuildingsPropagationLossModel");
    wifiChannel.AddPropagationLoss("ns3::RangePropagationLossModel", "MaxRange", DoubleValue(avgOptimizedRange));

    YansWifiPhyHelper wifiPhy;
    wifiPhy.SetChannel(wifiChannel.Create());
    wifiPhy.Set("TxPowerStart", DoubleValue(20.0));
    wifiPhy.Set("TxPowerEnd", DoubleValue(20.0));

    // Create mesh network
    MeshHelper mesh = MeshHelper::Default();
    mesh.SetStackInstaller("ns3::Dot11sStack");
    mesh.SetSpreadInterfaceChannels(MeshHelper::SPREAD_CHANNELS);
    mesh.SetMacType("RandomStart", TimeValue(Seconds(0.1)));
    mesh.SetNumberOfInterfaces(1);

    NetDeviceContainer meshDevices = mesh.Install(wifiPhy, allMeshNodes);
    
    std::cout << "\nUsing averaged optimized range: " << avgOptimizedRange << "m" << std::endl;
    std::cout << "  (Simulates variable: 145m corners, 170m center, 100-120m edges)" << std::endl;

    std::cout << "Created mesh network with all nodes" << std::endl;

    // Point-to-point backhaul (internet connection)
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("5ms"));

    NodeContainer internetNodes;
    internetNodes.Create(1);
    NetDeviceContainer internetDevices = p2p.Install(backhaulNodes.Get(0), internetNodes.Get(0));

    std::cout << "Created backhaul connection to internet" << std::endl;

    // Install internet stack with OLSR routing for mesh
    OlsrHelper olsr;
    Ipv4ListRoutingHelper list;
    list.Add(olsr, 10);
    
    InternetStackHelper internet;
    internet.SetRoutingHelper(list);
    internet.Install(allMeshNodes);
    internet.Install(internetNodes);

    // Assign IP addresses
    Ipv4AddressHelper ipv4;
    
    // Mesh network
    ipv4.SetBase("10.1.0.0", "255.255.0.0");
    Ipv4InterfaceContainer meshInterfaces = ipv4.Assign(meshDevices);
    
    // Backhaul
    ipv4.SetBase("172.16.0.0", "255.255.255.0");
    Ipv4InterfaceContainer internetInterfaces = ipv4.Assign(internetDevices);

    // Populate routing tables
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    std::cout << "\nIP Address Assignments:" << std::endl;
    std::cout << "  Backhaul: " << meshInterfaces.GetAddress(0) << std::endl;
    std::cout << "  Mesh APs: " << meshInterfaces.GetAddress(1) << " to " 
              << meshInterfaces.GetAddress(nMeshHops) << " (" << nMeshHops << " APs)" << std::endl;
    std::cout << "  Sayed: " << meshInterfaces.GetAddress(1 + nMeshHops + nTotalStas) << std::endl;
    std::cout << "  Sadia: " << meshInterfaces.GetAddress(1 + nMeshHops + nTotalStas + 1) << std::endl;

    // Enable tracing
    wifiPhy.EnablePcapAll(outputDir + "tcp_mesh_backhaul_mode", true);
    AsciiTraceHelper ascii;
    wifiPhy.EnableAsciiAll(ascii.CreateFileStream(outputDir + "tcp_mesh_backhaul_mode.tr"));

    std::cout << "Enabled tracing" << std::endl;

    // Setup TCP and UDP Applications with scheduled transfers
    std::cout << "\nSetting up TCP+UDP applications..." << std::endl;

    // Get Sayed and Sadia indices
    uint32_t sayedIdx = 1 + nMeshHops + nTotalStas;
    uint32_t sadiaIdx = 1 + nMeshHops + nTotalStas + 1;

    Ipv4Address sayedIP = meshInterfaces.GetAddress(sayedIdx);
    Ipv4Address sadiaIP = meshInterfaces.GetAddress(sadiaIdx);

    // TCP Servers (always listening)
    PacketSinkHelper tcpServerSadia("ns3::TcpSocketFactory",
                                    InetSocketAddress(Ipv4Address::GetAny(), tcpPort));
    ApplicationContainer tcpServerSadiaApp = tcpServerSadia.Install(sayedSadiaNodes.Get(1));
    tcpServerSadiaApp.Start(Seconds(0.5));
    tcpServerSadiaApp.Stop(Seconds(simTime));

    PacketSinkHelper tcpServerSayed("ns3::TcpSocketFactory",
                                    InetSocketAddress(Ipv4Address::GetAny(), tcpPort + 1));
    ApplicationContainer tcpServerSayedApp = tcpServerSayed.Install(sayedSadiaNodes.Get(0));
    tcpServerSayedApp.Start(Seconds(0.5));
    tcpServerSayedApp.Stop(Seconds(simTime));

    // UDP Servers (always listening)
    PacketSinkHelper udpServerSadia("ns3::UdpSocketFactory",
                                    InetSocketAddress(Ipv4Address::GetAny(), udpPort));
    ApplicationContainer udpServerSadiaApp = udpServerSadia.Install(sayedSadiaNodes.Get(1));
    udpServerSadiaApp.Start(Seconds(0.5));
    udpServerSadiaApp.Stop(Seconds(simTime));

    PacketSinkHelper udpServerSayed("ns3::UdpSocketFactory",
                                    InetSocketAddress(Ipv4Address::GetAny(), udpPort + 1));
    ApplicationContainer udpServerSayedApp = udpServerSayed.Install(sayedSadiaNodes.Get(0));
    udpServerSayedApp.Start(Seconds(0.5));
    udpServerSayedApp.Stop(Seconds(simTime));

    // TCP Transfers: Sayed -> Sadia at 2, 5, 8, 11, 14 seconds (start later for routing)
    std::cout << "TCP Transfers (Sayed -> Sadia): at 2, 5, 8, 11, 14 seconds" << std::endl;
    std::vector<double> tcpStartTimes = {4.0, 7.0, 10.0, 13.0}; // Adjusted for 15s sim, start at 4s
    for (double startTime : tcpStartTimes) {
        OnOffHelper tcpClient("ns3::TcpSocketFactory",
                             InetSocketAddress(sadiaIP, tcpPort));
        tcpClient.SetConstantRate(DataRate("1Mbps"), 1400);
        tcpClient.SetAttribute("StartTime", TimeValue(Seconds(startTime)));
        tcpClient.SetAttribute("StopTime", TimeValue(Seconds(startTime + 0.5)));
        tcpClient.Install(sayedSadiaNodes.Get(0));
    }

    // TCP Transfers: Sadia -> Sayed at 2, 5, 8, 11, 14 seconds
    std::cout << "TCP Transfers (Sadia -> Sayed): at 2, 5, 8, 11, 14 seconds" << std::endl;
    for (double startTime : tcpStartTimes) {
        OnOffHelper tcpClientReverse("ns3::TcpSocketFactory",
                                    InetSocketAddress(sayedIP, tcpPort + 1));
        tcpClientReverse.SetConstantRate(DataRate("1Mbps"), 1400);
        tcpClientReverse.SetAttribute("StartTime", TimeValue(Seconds(startTime + 0.1)));
        tcpClientReverse.SetAttribute("StopTime", TimeValue(Seconds(startTime + 0.6)));
        tcpClientReverse.Install(sayedSadiaNodes.Get(1));
    }

    // UDP Transfers: Sayed -> Sadia at 5, 8, 11 seconds
    std::cout << "UDP Transfers (Sayed -> Sadia): at 5, 8, 11 seconds" << std::endl;
    std::vector<double> udpStartTimes = {5.0, 8.0, 11.0};
    for (double startTime : udpStartTimes) {
        OnOffHelper udpClient("ns3::UdpSocketFactory",
                             InetSocketAddress(sadiaIP, udpPort));
        udpClient.SetConstantRate(DataRate("500Kbps"), 1024);
        udpClient.SetAttribute("StartTime", TimeValue(Seconds(startTime)));
        udpClient.SetAttribute("StopTime", TimeValue(Seconds(startTime + 0.5)));
        udpClient.Install(sayedSadiaNodes.Get(0));
    }

    // UDP Transfers: Sadia -> Sayed at 4, 6, 8, 10 seconds
    std::cout << "UDP Transfers (Sadia -> Sayed): at 4, 6, 8, 10 seconds" << std::endl;
    for (double startTime : udpStartTimes) {
        OnOffHelper udpClientReverse("ns3::UdpSocketFactory",
                                    InetSocketAddress(sayedIP, udpPort + 1));
        udpClientReverse.SetConstantRate(DataRate("500Kbps"), 1024);
        udpClientReverse.SetAttribute("StartTime", TimeValue(Seconds(startTime + 0.1)));
        udpClientReverse.SetAttribute("StopTime", TimeValue(Seconds(startTime + 0.6)));
        udpClientReverse.Install(sayedSadiaNodes.Get(1));
    }

    std::cout << "Configured bidirectional TCP+UDP traffic at scheduled times" << std::endl;

    // Enable FlowMonitor
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.Install(allMeshNodes);

    std::cout << "Installed FlowMonitor" << std::endl;

    // Run simulation
    std::cout << "\nStarting simulation..." << std::endl;
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    // Print statistics
    Ptr<PacketSink> tcpSinkSadia = DynamicCast<PacketSink>(tcpServerSadiaApp.Get(0));
    Ptr<PacketSink> tcpSinkSayed = DynamicCast<PacketSink>(tcpServerSayedApp.Get(0));
    Ptr<PacketSink> udpSinkSadia = DynamicCast<PacketSink>(udpServerSadiaApp.Get(0));
    Ptr<PacketSink> udpSinkSayed = DynamicCast<PacketSink>(udpServerSayedApp.Get(0));
    
    std::cout << "\n=== APPLICATION LAYER RESULTS ===" << std::endl;
    std::cout << "TCP Data Received:" << std::endl;
    std::cout << "  Sadia received: " << tcpSinkSadia->GetTotalRx() << " bytes (from Sayed)" << std::endl;
    std::cout << "  Sayed received: " << tcpSinkSayed->GetTotalRx() << " bytes (from Sadia)" << std::endl;
    std::cout << "UDP Data Received:" << std::endl;
    std::cout << "  Sadia received: " << udpSinkSadia->GetTotalRx() << " bytes (from Sayed)" << std::endl;
    std::cout << "  Sayed received: " << udpSinkSayed->GetTotalRx() << " bytes (from Sadia)" << std::endl;

    monitor->CheckForLostPackets();
    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats();

    std::cout << "\n=== FLOWMONITOR RESULTS ===" << std::endl;
    std::cout << "Total flows: " << stats.size() << std::endl;

    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(flowmon.GetClassifier());
    
    for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin(); i != stats.end(); ++i)
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(i->first);
        
        std::cout << "\nFlow " << i->first << " (" 
                  << t.sourceAddress << ":" << t.sourcePort << " -> " 
                  << t.destinationAddress << ":" << t.destinationPort << ")" << std::endl;
        std::cout << "  Tx Packets: " << i->second.txPackets << std::endl;
        std::cout << "  Rx Packets: " << i->second.rxPackets << std::endl;
        std::cout << "  Tx Bytes: " << i->second.txBytes << std::endl;
        std::cout << "  Rx Bytes: " << i->second.rxBytes << std::endl;
        std::cout << "  Lost Packets: " << i->second.lostPackets << std::endl;
        
        if (i->second.rxPackets > 0) {
            std::cout << "  Throughput: " << i->second.rxBytes * 8.0 / simTime / 1000 / 1000 << " Mbps" << std::endl;
            std::cout << "  Avg Delay: " << (i->second.delaySum.GetSeconds() / i->second.rxPackets) * 1000 << " ms" << std::endl;
            std::cout << "  Packet Loss: " << (i->second.lostPackets * 100.0 / i->second.txPackets) << "%" << std::endl;
        }
    }

    // Save FlowMonitor results
    monitor->SerializeToXmlFile(outputDir + "tcp_mesh_backhaul_mode_flowmon.xml", true, true);

    std::cout << "\n=== SIMULATION COMPLETED ===" << std::endl;
    std::cout << "Results saved to:" << std::endl;
    std::cout << "  - FlowMonitor: " << outputDir << "tcp_mesh_backhaul_mode_flowmon.xml" << std::endl;
    std::cout << "  - ASCII traces: " << outputDir << "tcp_mesh_backhaul_mode.tr" << std::endl;
    std::cout << "  - PCAP files: " << outputDir << "tcp_mesh_backhaul_mode-*.pcap" << std::endl;

    Simulator::Destroy();
    return 0;
}

