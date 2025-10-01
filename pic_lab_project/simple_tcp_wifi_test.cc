/*
 * Simple TCP WiFi Mesh Test (Two Mesh APs)
 * 
 * Network topology:
 *   STA1 (Sayed) ---- Mesh AP1 <---> Mesh AP2 ---- STA2 (Sadia)
 * 
 * TCP communication: STA1 (Sayed) <-> STA2 (Sadia) via mesh network
 * Goal: Test TCP connectivity in a mesh WiFi environment
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mesh-helper.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-helper.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("SimpleTcpWifiTest");

int main(int argc, char *argv[])
{
    // Enable packet metadata early
    PacketMetadata::Enable();

    // Enable logging
    LogComponentEnable("OnOffApplication", LOG_LEVEL_INFO);
    LogComponentEnable("PacketSink", LOG_LEVEL_INFO);
    LogComponentEnable("TcpSocketBase", LOG_LEVEL_INFO);
    LogComponentEnable("BulkSendApplication", LOG_LEVEL_INFO);
    LogComponentEnable("Ipv4L3Protocol", LOG_LEVEL_INFO);
    LogComponentEnable("Ipv4GlobalRouting", LOG_LEVEL_INFO);

    // Simulation parameters
    const double simTime = 10.0;
    const uint16_t tcpPort = 7000;

    std::cout << "Starting Simple TCP WiFi Mesh Test..." << std::endl;
    std::cout << "Simulation time: " << simTime << " seconds" << std::endl;

    // Create nodes (mesh with two APs)
    NodeContainer meshNodes;
    NodeContainer staNodes;
    
    meshNodes.Create(2);      // Two mesh APs
    staNodes.Create(2);       // Sayed and Sadia

    // Create all nodes container for easy management
    NodeContainer allNodes;
    allNodes.Add(meshNodes);
    allNodes.Add(staNodes);

    std::cout << "Created nodes: " << allNodes.GetN() << " total" << std::endl;

    // Setup mobility
    MobilityHelper mobility;
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(allNodes);

    // Position nodes manually for mesh topology
    Ptr<MobilityModel> mesh1Mob = meshNodes.Get(0)->GetObject<MobilityModel>();
    Ptr<MobilityModel> mesh2Mob = meshNodes.Get(1)->GetObject<MobilityModel>();
    Ptr<MobilityModel> sta1Mob = staNodes.Get(0)->GetObject<MobilityModel>();
    Ptr<MobilityModel> sta2Mob = staNodes.Get(1)->GetObject<MobilityModel>();

    mesh1Mob->SetPosition(Vector(0.0, 0.0, 0.0));       // Mesh AP1 at origin
    mesh2Mob->SetPosition(Vector(100.0, 0.0, 0.0));      // Mesh AP2 50m away (closer)
    sta1Mob->SetPosition(Vector(10.0, 0.0, 0.0));        // Sayed very close to Mesh AP1
    sta2Mob->SetPosition(Vector(110.0, 0.0, 0.0));       // Sadia very close to Mesh AP2

    std::cout << "Positioned nodes:" << std::endl;
    std::cout << "  Mesh AP1: " << mesh1Mob->GetPosition() << std::endl;
    std::cout << "  Mesh AP2: " << mesh2Mob->GetPosition() << std::endl;
    std::cout << "  Sayed (STA1): " << sta1Mob->GetPosition() << std::endl;
    std::cout << "  Sadia (STA2): " << sta2Mob->GetPosition() << std::endl;

    // Simplified mesh topology (ad-hoc network)
    std::cout << "Mesh topology: Two mesh APs + STAs in ad-hoc network" << std::endl;

    // Create point-to-point link between mesh APs
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));
    NetDeviceContainer meshBackhaulDevices = p2p.Install(meshNodes);

    std::cout << "Created backhaul link between mesh APs" << std::endl;

    // Setup WiFi - Use 802.11g to avoid OFDM modulation issue
    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211g);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                "DataMode", StringValue("ErpOfdmRate54Mbps"),
                                "ControlMode", StringValue("ErpOfdmRate6Mbps"));

    YansWifiPhyHelper wifiPhy;
    YansWifiChannelHelper wifiChannel = YansWifiChannelHelper::Default();
    wifiPhy.SetChannel(wifiChannel.Create());

    // Create mesh APs as regular WiFi APs (simplified approach)
    WifiMacHelper mac;
    Ssid ssid = Ssid("mesh-network");
    
    mac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(ssid));
    NetDeviceContainer meshDevices = wifi.Install(wifiPhy, mac, meshNodes);

    // Create STA devices connected to mesh APs
    mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid), "ActiveProbing", BooleanValue(false));
    NetDeviceContainer staDevices = wifi.Install(wifiPhy, mac, staNodes);

    std::cout << "Created mesh network with 2 APs and 2 STA devices" << std::endl;

    // Install internet stack
    InternetStackHelper internet;
    internet.Install(allNodes);

    std::cout << "Installed internet stack" << std::endl;

    // Assign IP addresses
    Ipv4AddressHelper ipv4;

    // Backhaul network (Mesh AP1 <-> Mesh AP2)
    ipv4.SetBase("172.16.0.0", "255.255.255.0");
    Ipv4InterfaceContainer backhaulInterfaces = ipv4.Assign(meshBackhaulDevices);

    // WiFi network (Mesh APs + STAs)
    ipv4.SetBase("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer meshInterfaces = ipv4.Assign(meshDevices);
    Ipv4InterfaceContainer staInterfaces = ipv4.Assign(staDevices);

    std::cout << "Assigned IP addresses:" << std::endl;
    std::cout << "  Mesh AP1: " << meshInterfaces.GetAddress(0) << " (wifi), " << backhaulInterfaces.GetAddress(0) << " (backhaul)" << std::endl;
    std::cout << "  Mesh AP2: " << meshInterfaces.GetAddress(1) << " (wifi), " << backhaulInterfaces.GetAddress(1) << " (backhaul)" << std::endl;
    std::cout << "  Sayed (STA1): " << staInterfaces.GetAddress(0) << std::endl;
    std::cout << "  Sadia (STA2): " << staInterfaces.GetAddress(1) << std::endl;

    // Populate routing tables
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    std::cout << "Populated routing tables" << std::endl;

    // Enable tracing BEFORE applications
    wifiPhy.EnablePcapAll("simple_tcp_wifi_test");
    AsciiTraceHelper ascii;
    wifiPhy.EnableAsciiAll(ascii.CreateFileStream("simple_tcp_wifi_test.tr"));

    std::cout << "Enabled tracing" << std::endl;

    // Create applications (EXACTLY like working TCP example)
    std::cout << "Setting up applications..." << std::endl;

    // TCP Server (Sadia) - Start immediately like working example
    PacketSinkHelper tcpServer("ns3::TcpSocketFactory",
                               InetSocketAddress(Ipv4Address::GetAny(), tcpPort));
    ApplicationContainer tcpServerApp = tcpServer.Install(staNodes.Get(1)); // Sadia
    tcpServerApp.Start(Seconds(0.0)); // Start immediately like working example
    tcpServerApp.Stop(Seconds(simTime));

    // TCP Client (Sayed) - Start immediately like working example
    BulkSendHelper tcpClient("ns3::TcpSocketFactory",
                             InetSocketAddress(staInterfaces.GetAddress(1), tcpPort));
    tcpClient.SetAttribute("MaxBytes", UintegerValue(1000000)); // 1MB
    ApplicationContainer tcpClientApp = tcpClient.Install(staNodes.Get(0)); // Sayed
    tcpClientApp.Start(Seconds(0.0)); // Start immediately like working example
    tcpClientApp.Stop(Seconds(simTime));

    std::cout << "TCP Server (Sadia) starts at 0.0s on port " << tcpPort << std::endl;
    std::cout << "TCP Client (Sayed) starts at 0.0s, target: " << staInterfaces.GetAddress(1) << ":" << tcpPort << std::endl;

    // Enable FlowMonitor
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.Install(allNodes);

    std::cout << "Installed FlowMonitor" << std::endl;

    // Run simulation
    std::cout << "Starting simulation..." << std::endl;
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    // Print basic statistics (like working example)
    Ptr<PacketSink> sink1 = DynamicCast<PacketSink>(tcpServerApp.Get(0));
    std::cout << "\nTotal Bytes Received: " << sink1->GetTotalRx() << std::endl;

    monitor->CheckForLostPackets();
    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats();

    std::cout << "\n=== FLOWMONITOR RESULTS ===" << std::endl;
    std::cout << "Total flows: " << stats.size() << std::endl;

    for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin(); i != stats.end(); ++i)
    {
        std::cout << "\nFlow " << i->first << ":" << std::endl;
        std::cout << "  Tx Packets: " << i->second.txPackets << std::endl;
        std::cout << "  Rx Packets: " << i->second.rxPackets << std::endl;
        std::cout << "  Tx Bytes: " << i->second.txBytes << std::endl;
        std::cout << "  Rx Bytes: " << i->second.rxBytes << std::endl;
        if (i->second.rxPackets > 0) {
            std::cout << "  Throughput: " << i->second.rxBytes * 8.0 / (simTime - 2.0) / 1000 / 1000 << " Mbps" << std::endl;
        }
    }

    // Save FlowMonitor results
    monitor->SerializeToXmlFile("simple_tcp_wifi_test_flowmon.xml", true, true);

    std::cout << "\nSimulation completed!" << std::endl;
    std::cout << "Results saved to:" << std::endl;
    std::cout << "  - FlowMonitor: simple_tcp_wifi_test_flowmon.xml" << std::endl;
    std::cout << "  - ASCII traces: simple_tcp_wifi_test.tr" << std::endl;
    std::cout << "  - PCAP files: simple_tcp_wifi_test-*.pcap" << std::endl;

    Simulator::Destroy();
    return 0;
}
