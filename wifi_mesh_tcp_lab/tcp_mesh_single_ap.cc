/*
 * Simple TCP Mesh Test
 * 
 * Network topology:
 *   Internet Server (Backhaul) ---- Mesh AP ---- STA1 (Sayed)
 *                                        |
 *                                     STA2 (Sadia)
 * 
 * TCP communication: STA1 (Sayed) <-> STA2 (Sadia)
 * Goal: Test TCP connectivity in a simple mesh environment
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
#include "ns3/olsr-helper.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("SimpleTcpMeshTest");

int main(int argc, char *argv[])
{
    // Enable packet metadata early
    PacketMetadata::Enable();

    // Enable logging
    LogComponentEnable("OnOffApplication", LOG_LEVEL_INFO);
    LogComponentEnable("PacketSink", LOG_LEVEL_INFO);
    LogComponentEnable("TcpSocketBase", LOG_LEVEL_INFO);
    LogComponentEnable("BulkSendApplication", LOG_LEVEL_INFO);

    // Simulation parameters
    const double simTime = 10.0;
    const uint16_t tcpPort = 7000;

    std::cout << "Starting Simple TCP Mesh Test..." << std::endl;
    std::cout << "Simulation time: " << simTime << " seconds" << std::endl;

    // Create nodes
    NodeContainer internetNodes;
    NodeContainer meshNodes;
    NodeContainer staNodes;
    
    internetNodes.Create(1);  // Internet server
    meshNodes.Create(1);      // One mesh AP
    staNodes.Create(2);       // Sayed and Sadia

    // Create all nodes container for easy management
    NodeContainer allNodes;
    allNodes.Add(internetNodes);
    allNodes.Add(meshNodes);
    allNodes.Add(staNodes);

    std::cout << "Created nodes: " << allNodes.GetN() << " total" << std::endl;

    // Setup mobility
    MobilityHelper mobility;
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(allNodes);

    // Position nodes manually for clarity
    Ptr<MobilityModel> internetMob = internetNodes.Get(0)->GetObject<MobilityModel>();
    Ptr<MobilityModel> meshMob = meshNodes.Get(0)->GetObject<MobilityModel>();
    Ptr<MobilityModel> sta1Mob = staNodes.Get(0)->GetObject<MobilityModel>();
    Ptr<MobilityModel> sta2Mob = staNodes.Get(1)->GetObject<MobilityModel>();

    internetMob->SetPosition(Vector(-50.0, 0.0, 0.0));  // Internet server to the left
    meshMob->SetPosition(Vector(0.0, 0.0, 0.0));        // Mesh AP in center
    sta1Mob->SetPosition(Vector(50.0, 0.0, 0.0));       // Sayed to the right
    sta2Mob->SetPosition(Vector(0.0, 50.0, 0.0));       // Sadia above mesh AP

    std::cout << "Positioned nodes:" << std::endl;
    std::cout << "  Internet Server: " << internetMob->GetPosition() << std::endl;
    std::cout << "  Mesh AP: " << meshMob->GetPosition() << std::endl;
    std::cout << "  Sayed (STA1): " << sta1Mob->GetPosition() << std::endl;
    std::cout << "  Sadia (STA2): " << sta2Mob->GetPosition() << std::endl;

    // Create point-to-point link between internet and mesh
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));

    NetDeviceContainer backhaulDevices;
    backhaulDevices = p2p.Install(internetNodes.Get(0), meshNodes.Get(0));

    std::cout << "Created backhaul link: Internet <-> Mesh AP" << std::endl;

    // Setup WiFi for mesh and STA
    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211n);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                "DataMode", StringValue("OfdmRate54Mbps"),
                                "ControlMode", StringValue("OfdmRate54Mbps"));

    YansWifiPhyHelper wifiPhy;
    YansWifiChannelHelper wifiChannel = YansWifiChannelHelper::Default();
    wifiPhy.SetChannel(wifiChannel.Create());

    // Mesh configuration
    MeshHelper mesh = MeshHelper::Default();
    mesh.SetStackInstaller("ns3::Dot11sStack");
    mesh.SetMacType("RandomStart", TimeValue(Seconds(0.1)));
    mesh.SetNumberOfInterfaces(1);
    NetDeviceContainer meshDevices = mesh.Install(wifiPhy, meshNodes);

    std::cout << "Created mesh network with 1 AP" << std::endl;

    // STA configuration
    WifiMacHelper mac;
    mac.SetType("ns3::StaWifiMac",
                "Ssid", SsidValue(Ssid("mesh-network")),
                "ActiveProbing", BooleanValue(false));

    NetDeviceContainer staDevices;
    staDevices = wifi.Install(wifiPhy, mac, staNodes);

    std::cout << "Created 2 STA devices" << std::endl;

    // Install internet stack
    InternetStackHelper internet;
    OlsrHelper olsr;
    internet.SetRoutingHelper(olsr);
    internet.Install(allNodes);

    std::cout << "Installed internet stack with OLSR routing" << std::endl;

    // Assign IP addresses
    Ipv4AddressHelper ipv4;

    // Backhaul network (Internet <-> Mesh AP)
    ipv4.SetBase("172.16.0.0", "255.255.255.0");
    Ipv4InterfaceContainer backhaulInterfaces = ipv4.Assign(backhaulDevices);

    // FIXED: Put mesh and STA on the same subnet for direct communication
    ipv4.SetBase("10.1.0.0", "255.255.255.0");
    Ipv4InterfaceContainer meshInterfaces = ipv4.Assign(meshDevices);
    Ipv4InterfaceContainer staInterfaces = ipv4.Assign(staDevices);

    std::cout << "Assigned IP addresses:" << std::endl;
    std::cout << "  Internet Server: " << backhaulInterfaces.GetAddress(0) << std::endl;
    std::cout << "  Mesh AP: " << meshInterfaces.GetAddress(0) << " (mesh), " << backhaulInterfaces.GetAddress(1) << " (backhaul)" << std::endl;
    std::cout << "  Sayed (STA1): " << staInterfaces.GetAddress(0) << std::endl;
    std::cout << "  Sadia (STA2): " << staInterfaces.GetAddress(1) << std::endl;

    // Populate routing tables
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    std::cout << "Populated routing tables" << std::endl;

    // Enable tracing BEFORE applications
    wifiPhy.EnablePcapAll("simple_tcp_mesh_test");
    AsciiTraceHelper ascii;
    wifiPhy.EnableAsciiAll(ascii.CreateFileStream("simple_tcp_mesh_test.tr"));

    std::cout << "Enabled tracing" << std::endl;

    // Create applications
    std::cout << "Setting up applications..." << std::endl;

    // TCP Server (Sadia)
    PacketSinkHelper tcpServer("ns3::TcpSocketFactory",
                               InetSocketAddress(Ipv4Address::GetAny(), tcpPort));
    ApplicationContainer tcpServerApp = tcpServer.Install(staNodes.Get(1)); // Sadia
    tcpServerApp.Start(Seconds(1.0));
    tcpServerApp.Stop(Seconds(simTime));

    // TCP Client (Sayed)
    BulkSendHelper tcpClient("ns3::TcpSocketFactory",
                             InetSocketAddress(staInterfaces.GetAddress(1), tcpPort));
    tcpClient.SetAttribute("MaxBytes", UintegerValue(1000000)); // 1MB
    ApplicationContainer tcpClientApp = tcpClient.Install(staNodes.Get(0)); // Sayed
    tcpClientApp.Start(Seconds(2.0));
    tcpClientApp.Stop(Seconds(simTime));

    std::cout << "TCP Server (Sadia) starts at 1.0s on port " << tcpPort << std::endl;
    std::cout << "TCP Client (Sayed) starts at 2.0s, target: " << staInterfaces.GetAddress(1) << ":" << tcpPort << std::endl;

    // Enable FlowMonitor
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.Install(allNodes);

    std::cout << "Installed FlowMonitor" << std::endl;

    // Run simulation
    std::cout << "Starting simulation..." << std::endl;
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    // Print basic statistics
    monitor->CheckForLostPackets();
    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats();

    std::cout << "\n=== SIMULATION RESULTS ===" << std::endl;
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
    monitor->SerializeToXmlFile("simple_tcp_mesh_test_flowmon.xml", true, true);

    std::cout << "\nSimulation completed!" << std::endl;
    std::cout << "Results saved to:" << std::endl;
    std::cout << "  - FlowMonitor: simple_tcp_mesh_test_flowmon.xml" << std::endl;
    std::cout << "  - ASCII traces: simple_tcp_mesh_test.tr" << std::endl;
    std::cout << "  - PCAP files: simple_tcp_mesh_test-*.pcap" << std::endl;

    Simulator::Destroy();
    return 0;
}
