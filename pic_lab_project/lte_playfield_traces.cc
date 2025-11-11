#include "ns3/applications-module.h"
#include "ns3/buildings-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/lte-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/trace-helper.h"
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <cmath>

using namespace ns3;

static const std::string kOutDir = "Lte_outputs";

// ============================================================================
// HELPER FUNCTION DECLARATIONS
// ============================================================================
void ConfigureUeMobility(NodeContainer& ueNodes,
                         double field,
                         double minHeight,
                         double maxHeight);
void ConfigureEnbMobility(NodeContainer& enbNodes, double field);
BuildingContainer CreateBuildingObstacles(double field);
void SetupInternetApplications(NodeContainer ueNodes,
                               Ptr<Node> remoteHost,
                               Ipv4InterfaceContainer ueIpIfaces,
                               double simStop);

// RRC trace callbacks for better runtime visibility
static void NotifyConnectionEstablishedUe(std::string context, uint64_t imsi,
                                          uint16_t cellid, uint16_t rnti) {
  std::cout << Simulator::Now().GetSeconds() << " " << context
            << " UE IMSI " << imsi << ": connected to CellId " << cellid
            << " with RNTI " << rnti << std::endl;
}

static void NotifyHandoverStartUe(std::string context, uint64_t imsi,
                                  uint16_t cellid, uint16_t rnti,
                                  uint16_t targetCellId) {
  std::cout << Simulator::Now().GetSeconds() << " " << context
            << " UE IMSI " << imsi << ": previously connected to CellId "
            << cellid << " with RNTI " << rnti << ", doing handover to CellId "
            << targetCellId << std::endl;
}

static void NotifyHandoverEndOkUe(std::string context, uint64_t imsi,
                                  uint16_t cellid, uint16_t rnti) {
  std::cout << Simulator::Now().GetSeconds() << " " << context
            << " UE IMSI " << imsi << ": successful handover to CellId "
            << cellid << " with RNTI " << rnti << std::endl;
}

static void NotifyConnectionEstablishedEnb(std::string context, uint64_t imsi,
                                           uint16_t cellid, uint16_t rnti) {
  std::cout << Simulator::Now().GetSeconds() << " " << context
            << " eNB CellId " << cellid
            << ": successful connection of UE with IMSI " << imsi
            << " RNTI " << rnti << std::endl;
}

static void NotifyHandoverStartEnb(std::string context, uint64_t imsi,
                                   uint16_t cellid, uint16_t rnti,
                                   uint16_t targetCellId) {
  std::cout << Simulator::Now().GetSeconds() << " " << context
            << " eNB CellId " << cellid << ": start handover of UE with IMSI "
            << imsi << " RNTI " << rnti << " to CellId " << targetCellId
            << std::endl;
}

static void NotifyHandoverEndOkEnb(std::string context, uint64_t imsi,
                                   uint16_t cellid, uint16_t rnti) {
  std::cout << Simulator::Now().GetSeconds() << " " << context
            << " eNB CellId " << cellid << ": completed handover of UE with IMSI "
            << imsi << " RNTI " << rnti << std::endl;
}

// Output file name constants for easy configuration
static const std::string kPcapPrefix = "lte_playfield_rw_pcap";
static const std::string kAsciiTracesPrefix = "lte_playfield_ascii_traces";
static const std::string kNetAnimFile = "netanim-lte-playfield-rw.xml";
static const std::string kFlowmonFile = "flowmon-lte-playfield-rw.xml";

int main(int argc, char **argv) {
  // Basics
  PacketMetadata::Enable();
  Packet::EnablePrinting();
  // LogComponentEnable("OnOffApplication", LOG_LEVEL_DEBUG);
  //   LogComponentEnable("PacketSink", LOG_LEVEL_DEBUG);
  //   LogComponentEnable("UdpEchoClientApplication", LOG_LEVEL_DEBUG);
  //   LogComponentEnable("UdpEchoServerApplication", LOG_LEVEL_DEBUG);
  //   // TCP logging
  //   LogComponentEnable("BulkSendApplication", LOG_LEVEL_DEBUG);
  LogComponentEnable("TcpSocketBase", LOG_LEVEL_DEBUG);
  //   LogComponentEnable("TcpL4Protocol", LOG_LEVEL_DEBUG);
  // UDP logging (disabled when UDP traffic is commented out)
  LogComponentEnable("UdpServer", LOG_LEVEL_INFO);

  const uint32_t nUes = 10;
  const double field = 400.0;
  const double simStop = 10.0;
  const double minHeight = 0.0;
  const double maxHeight = 30.0;

  // Create UE nodes and macro eNB nodes (two towers outside the field)
  NodeContainer ueNodes;
  ueNodes.Create(nUes);
  NodeContainer enbNodes;
  enbNodes.Create(2);

  ConfigureUeMobility(ueNodes, field, minHeight, maxHeight);
  ConfigureEnbMobility(enbNodes, field);

  BuildingContainer buildings = CreateBuildingObstacles(field);
  BuildingsHelper::Install(ueNodes);
  BuildingsHelper::Install(enbNodes);

  // Macro-cell transmit power similar to NR configuration
  Config::SetDefault("ns3::LteEnbPhy::TxPower", DoubleValue(43.0)); // dBm
  Config::SetDefault("ns3::LteUePhy::TxPower", DoubleValue(23.0));  // dBm
  std::cout << "TxPower settings: eNB=43.00 dBm, UE=23.00 dBm" << std::endl;

  // LTE + EPC
  Ptr<LteHelper> lteHelper = CreateObject<LteHelper>();
  Ptr<PointToPointEpcHelper> epcHelperP2p =
      CreateObject<PointToPointEpcHelper>();
  lteHelper->SetEpcHelper(epcHelperP2p);
  Ptr<EpcHelper> epcHelper = epcHelperP2p;

  NetDeviceContainer enbDevs = lteHelper->InstallEnbDevice(enbNodes);
  NetDeviceContainer ueDevs = lteHelper->InstallUeDevice(ueNodes);

  // Enable X2 and LTE traces for better visualization
  lteHelper->AddX2Interface(enbNodes);
  lteHelper->EnablePhyTraces();
  lteHelper->EnableMacTraces();
  lteHelper->EnableRlcTraces();
  lteHelper->EnablePdcpTraces();

  // Connect RRC trace sinks
  Config::Connect("/NodeList/*/DeviceList/*/LteEnbRrc/ConnectionEstablished",
                  MakeCallback(&NotifyConnectionEstablishedEnb));
  Config::Connect("/NodeList/*/DeviceList/*/LteUeRrc/ConnectionEstablished",
                  MakeCallback(&NotifyConnectionEstablishedUe));
  Config::Connect("/NodeList/*/DeviceList/*/LteEnbRrc/HandoverStart",
                  MakeCallback(&NotifyHandoverStartEnb));
  Config::Connect("/NodeList/*/DeviceList/*/LteUeRrc/HandoverStart",
                  MakeCallback(&NotifyHandoverStartUe));
  Config::Connect("/NodeList/*/DeviceList/*/LteEnbRrc/HandoverEndOk",
                  MakeCallback(&NotifyHandoverEndOkEnb));
  Config::Connect("/NodeList/*/DeviceList/*/LteUeRrc/HandoverEndOk",
                  MakeCallback(&NotifyHandoverEndOkUe));

  // Internet stack on UEs via EPC-assigned IPs
  InternetStackHelper internet;
  internet.Install(ueNodes);
  Ipv4InterfaceContainer ueIpIfaces =
      epcHelper->AssignUeIpv4Address(NetDeviceContainer(ueDevs));

  Ipv4StaticRoutingHelper ipv4RoutingHelper;
  for (uint32_t i = 0; i < ueNodes.GetN(); ++i) {
    Ptr<Ipv4StaticRouting> ueStaticRouting =
        ipv4RoutingHelper.GetStaticRouting(ueNodes.Get(i)->GetObject<Ipv4>());
    ueStaticRouting->SetDefaultRoute(epcHelper->GetUeDefaultGatewayAddress(), 1);
  }

  // Attach each UE to the nearest eNB by distance
  for (uint32_t i = 0; i < ueNodes.GetN(); ++i) {
    Ptr<MobilityModel> ueMob = ueNodes.Get(i)->GetObject<MobilityModel>();
    Vector uePos = ueMob->GetPosition();
    double bestDist = std::numeric_limits<double>::max();
    uint32_t bestEnbIdx = 0;
    for (uint32_t e = 0; e < enbNodes.GetN(); ++e) {
      Ptr<MobilityModel> em = enbNodes.Get(e)->GetObject<MobilityModel>();
      Vector ep = em->GetPosition();
      double dx = uePos.x - ep.x;
      double dy = uePos.y - ep.y;
      double dist2 = dx * dx + dy * dy;
      if (dist2 < bestDist) {
        bestDist = dist2;
        bestEnbIdx = e;
      }
    }
    lteHelper->Attach(ueDevs.Get(i), enbDevs.Get(bestEnbIdx));
  }

  // Report eNB Macro layout
  {
    std::cout << "eNB positions:" << std::endl;
    std::vector<Vector> enbPositions;
    enbPositions.reserve(enbNodes.GetN());
    for (uint32_t e = 0; e < enbNodes.GetN(); ++e) {
      Ptr<MobilityModel> mm = enbNodes.Get(e)->GetObject<MobilityModel>();
      Vector p = mm->GetPosition();
      enbPositions.push_back(p);
      std::cout << "  eNB" << e << ": (" << p.x << ", " << p.y << ", " << p.z
                << ")" << std::endl;
    }
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "eNB pairwise distances (m):" << std::endl;
    for (uint32_t i = 0; i < enbPositions.size(); ++i) {
      for (uint32_t j = i + 1; j < enbPositions.size(); ++j) {
        double dx = enbPositions[i].x - enbPositions[j].x;
        double dy = enbPositions[i].y - enbPositions[j].y;
        double dz = enbPositions[i].z - enbPositions[j].z;
        double d = std::sqrt(dx * dx + dy * dy + dz * dz);
        std::cout << "  eNB" << i << "-eNB" << j << ": " << d << std::endl;
      }
    }
  }

  // Ensure outputs directory exists
  std::system(("mkdir -p " + kOutDir).c_str());

  // Create Remote Host to hook PGW and generate pcap/ascii on core link
  Ptr<Node> pgw = epcHelper->GetPgwNode();
  Ptr<Node> remoteHost = CreateObject<Node>();
  NodeContainer remoteHostContainer(remoteHost);
  internet.Install(remoteHostContainer);

  // Add mobility model to remoteHost to avoid AnimationInterface warnings
  MobilityHelper remoteHostMob;
  Ptr<ListPositionAllocator> remoteHostPos =
      CreateObject<ListPositionAllocator>();
  remoteHostPos->Add(Vector(field * 0.5, field + 50.0,
                            0.0)); // Position remote host outside the field
  remoteHostMob.SetPositionAllocator(remoteHostPos);
  remoteHostMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  remoteHostMob.Install(remoteHostContainer);

  // Add mobility models to EPC nodes to avoid AnimationInterface warnings
  Ptr<Node> sgw = epcHelper->GetSgwNode();
  NodeContainer epcNodes;
  epcNodes.Add(pgw);
  epcNodes.Add(sgw);
  MobilityHelper epcMob;
  Ptr<ListPositionAllocator> epcPos = CreateObject<ListPositionAllocator>();
  epcPos->Add(
      Vector(field * 0.5, field + 100.0, 0.0)); // Position PGW near remote host
  epcPos->Add(Vector(field * 0.3, field + 100.0, 0.0)); // Position SGW
  epcMob.SetPositionAllocator(epcPos);
  epcMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  epcMob.Install(epcNodes);

  PointToPointHelper p2ph;
  p2ph.SetDeviceAttribute("DataRate", StringValue("100Gbps"));
  p2ph.SetChannelAttribute("Delay", StringValue("1ms"));
  NetDeviceContainer internetDevices = p2ph.Install(pgw, remoteHost);

  Ipv4AddressHelper ipv4h;
  ipv4h.SetBase("1.0.0.0", "255.0.0.0");
  ipv4h.Assign(internetDevices); // Assign IP addresses to internet devices

  Ptr<Ipv4StaticRouting> remoteHostStaticRouting =
      ipv4RoutingHelper.GetStaticRouting(remoteHost->GetObject<Ipv4>());
  remoteHostStaticRouting->SetDefaultRoute(
      epcHelper->GetUeDefaultGatewayAddress(), 1);

  // Enable pcap and ascii traces on EPC P2P link with requested prefix
  p2ph.EnablePcapAll(kOutDir + "/" + kPcapPrefix, true);
  AsciiTraceHelper ascii;
  Ptr<OutputStreamWrapper> stream =
      ascii.CreateFileStream(kOutDir + "/" + kAsciiTracesPrefix + ".tr");
  p2ph.EnableAsciiAll(stream);

  SetupInternetApplications(ueNodes, remoteHost, ueIpIfaces, simStop);

  // FlowMonitor
  FlowMonitorHelper fm;
  Ptr<FlowMonitor> monitor = fm.InstallAll();

  // NetAnim
  AnimationInterface anim(kOutDir + "/" + kNetAnimFile);
  anim.SetMaxPktsPerTraceFile(
      500000); // Increase packet limit to avoid warnings
  anim.EnablePacketMetadata(true);
  const char* ueLabels[] = {"HTTP", "HTTP", "HTTPS", "HTTPS", "Video",
                            "Video", "VoIP", "VoIP", "HTTP",  "Mixed"};
  uint8_t ueColors[][3] = {
      {0, 150, 255}, {0, 150, 255}, {0, 200, 150}, {0, 200, 150}, {255, 0, 255},
      {255, 0, 255}, {255, 255, 0}, {255, 255, 0}, {255, 150, 0}, {200, 100, 200}};

  for (uint32_t i = 0; i < ueNodes.GetN(); ++i) {
    std::string label = "UE" + std::to_string(i) + "-" + ueLabels[i];
    anim.UpdateNodeDescription(ueNodes.Get(i), label);
    anim.UpdateNodeColor(ueNodes.Get(i), ueColors[i][0], ueColors[i][1], ueColors[i][2]);
  }
  // eNB visuals (grey)
  anim.UpdateNodeDescription(enbNodes.Get(0), "eNB-West");
  anim.UpdateNodeColor(enbNodes.Get(0), 128, 128, 128);
  anim.UpdateNodeDescription(enbNodes.Get(1), "eNB-East");
  anim.UpdateNodeColor(enbNodes.Get(1), 128, 128, 128);
  // Remote host visuals (green)
  anim.UpdateNodeDescription(remoteHost, "Internet-Server");
  anim.UpdateNodeColor(remoteHost, 0, 255, 0);

  // EPC nodes visuals
  anim.UpdateNodeDescription(pgw, "PGW");
  anim.UpdateNodeColor(pgw, 128, 0, 128); // Purple
  anim.UpdateNodeDescription(sgw, "SGW");
  anim.UpdateNodeColor(sgw, 255, 0, 255); // Magenta

  // IPv4 L3 ASCII tracing (emit packets at IP layer to ASCII file)
  {
    AsciiTraceHelper ascii;
    Ptr<OutputStreamWrapper> ipStream =
        ascii.CreateFileStream(kOutDir + "/ipv4-l3.tr");
    internet.EnableAsciiIpv4All(ipStream);
  }

  Simulator::Stop(Seconds(simStop));
  Simulator::Run();

  monitor->SerializeToXmlFile(kOutDir + "/" + kFlowmonFile, true, true);
  std::cout << "FlowMonitor XML saved to: " << kOutDir << "/" << kFlowmonFile << std::endl;
  std::cout << "All results saved to: " << kOutDir << "/" << std::endl;

  std::ostringstream parseCmd;
  parseCmd << "cd /home/sayed/pic_lab_project/ns3_project_for_kit && "
           << "python3 pic_lab_project/parse_lte_flowmon.py"
           << " --sim-time=" << simStop
           << " --md Lte_outputs/lte-playfield-metrics.md";

  std::cout << "Running FlowMonitor parser..." << std::endl;
  int parseStatus = std::system(parseCmd.str().c_str());
  if (parseStatus != 0) {
    std::cerr << "FlowMonitor parser exited with status " << parseStatus << std::endl;
  }

  Simulator::Destroy();
  return 0;
}

// ============================================================================
// HELPER FUNCTION IMPLEMENTATIONS
// ============================================================================

void ConfigureUeMobility(NodeContainer& ueNodes,
                         double field,
                         double minHeight,
                         double maxHeight) {
  std::cout << "\n=== Configuring UE Mobility (Gauss-Markov) ===" << std::endl;

  double minX = 0.0;
  double maxX = field;
  double minY = 0.0;
  double maxY = field;
  double minZ = minHeight;
  double maxZ = maxHeight;

  MobilityHelper mobility;
  Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();

  posAlloc->Add(Vector(50.0, 50.0, 5.0));
  posAlloc->Add(Vector(100.0, 80.0, 10.0));
  posAlloc->Add(Vector(150.0, 120.0, 15.0));
  posAlloc->Add(Vector(200.0, 180.0, 20.0));
  posAlloc->Add(Vector(250.0, 220.0, 25.0));
  posAlloc->Add(Vector(300.0, 280.0, 8.0));
  posAlloc->Add(Vector(350.0, 320.0, 12.0));
  posAlloc->Add(Vector(100.0, 300.0, 18.0));
  posAlloc->Add(Vector(200.0, 100.0, 3.0));
  posAlloc->Add(Vector(350.0, 350.0, 22.0));

  mobility.SetPositionAllocator(posAlloc);
  mobility.SetMobilityModel("ns3::GaussMarkovMobilityModel",
                            "Bounds", BoxValue(Box(minX, maxX, minY, maxY, minZ, maxZ)),
                            "TimeStep", TimeValue(Seconds(1.0)),
                            "Alpha", DoubleValue(0.85),
                            "MeanVelocity", StringValue("ns3::UniformRandomVariable[Min=0.3|Max=0.8]"),
                            "MeanDirection", StringValue("ns3::UniformRandomVariable[Min=0|Max=6.283185307]"),
                            "MeanPitch", StringValue("ns3::UniformRandomVariable[Min=-0.05|Max=0.05]"),
                            "NormalVelocity", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.0|Bound=0.0]"),
                            "NormalDirection", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.1|Bound=0.2]"),
                            "NormalPitch", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.01|Bound=0.02]"));

  mobility.Install(ueNodes);

  std::cout << "Movement Type: Smooth pedestrian (Gauss-Markov)" << std::endl;
  std::cout << "Bounds: (" << minX << "," << maxX << ") × (" << minY << "," << maxY
            << ") × (" << minZ << "," << maxZ << ")" << std::endl;
  std::cout << "====================================\n" << std::endl;
}

void ConfigureEnbMobility(NodeContainer& enbNodes, double field) {
  std::cout << "=== Configuring eNB Macro Positions ===" << std::endl;
  MobilityHelper enbMob;
  Ptr<ListPositionAllocator> enbPos = CreateObject<ListPositionAllocator>();
  enbPos->Add(Vector(-100.0, field * 0.5, 30.0));       // West macro site
  enbPos->Add(Vector(field + 100.0, field * 0.5, 30.0)); // East macro site
  enbMob.SetPositionAllocator(enbPos);
  enbMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  enbMob.Install(enbNodes);
  std::cout << "====================================\n" << std::endl;
}

BuildingContainer CreateBuildingObstacles(double field) {
  std::cout << "=== Creating Static Building Obstacles ===" << std::endl;
  std::cout << "Field size reference: " << field << " m × " << field << " m" << std::endl;
  BuildingContainer buildings;

  Ptr<Building> leftBelow = CreateObject<Building>();
  leftBelow->SetBoundaries(Box(0.0, 60.0, 96.0, 104.0, 0.0, 10.0));
  buildings.Add(leftBelow);

  Ptr<Building> rightBelow = CreateObject<Building>();
  rightBelow->SetBoundaries(Box(340.0, 400.0, 96.0, 104.0, 0.0, 10.0));
  buildings.Add(rightBelow);

  Ptr<Building> leftAbove = CreateObject<Building>();
  leftAbove->SetBoundaries(Box(0.0, 60.0, 296.0, 304.0, 0.0, 10.0));
  buildings.Add(leftAbove);

  Ptr<Building> rightAbove = CreateObject<Building>();
  rightAbove->SetBoundaries(Box(340.0, 400.0, 296.0, 304.0, 0.0, 10.0));
  buildings.Add(rightAbove);

  Ptr<Building> cluster250a = CreateObject<Building>();
  cluster250a->SetBoundaries(Box(80.0, 140.0, 220.0, 228.0, 0.0, 15.0));
  buildings.Add(cluster250a);

  Ptr<Building> cluster250b = CreateObject<Building>();
  cluster250b->SetBoundaries(Box(170.0, 250.0, 220.0, 228.0, 0.0, 12.0));
  buildings.Add(cluster250b);

  Ptr<Building> cluster50 = CreateObject<Building>();
  cluster50->SetBoundaries(Box(255.0, 335.0, 20.0, 28.0, 0.0, 18.0));
  buildings.Add(cluster50);

  std::cout << "Total buildings: " << buildings.GetN() << std::endl;
  std::cout << "Static obstacles configured (no movement events)" << std::endl;
  std::cout << "====================================\n" << std::endl;

  return buildings;
}

void SetupInternetApplications(NodeContainer ueNodes,
                               Ptr<Node> remoteHost,
                               Ipv4InterfaceContainer ueIpIfaces,
                               double simStop) {
  std::cout << "\n=== Setting Up Internet Applications ===" << std::endl;

  Ipv4Address remoteHostAddr =
      remoteHost->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
  std::cout << "Remote Host (Internet Server) IP: " << remoteHostAddr << std::endl;

  const uint16_t httpPort = 80;
  const uint16_t httpsPort = 443;
  const uint16_t videoPort = 8080;
  const uint16_t voipPort = 5060;

  ApplicationContainer serverApps;
  PacketSinkHelper httpServer("ns3::TcpSocketFactory",
                              InetSocketAddress(Ipv4Address::GetAny(), httpPort));
  serverApps.Add(httpServer.Install(remoteHost));

  PacketSinkHelper httpsServer("ns3::TcpSocketFactory",
                               InetSocketAddress(Ipv4Address::GetAny(), httpsPort));
  serverApps.Add(httpsServer.Install(remoteHost));

  PacketSinkHelper videoServer("ns3::TcpSocketFactory",
                               InetSocketAddress(Ipv4Address::GetAny(), videoPort));
  serverApps.Add(videoServer.Install(remoteHost));

  UdpServerHelper voipServer(voipPort);
  serverApps.Add(voipServer.Install(remoteHost));

  serverApps.Start(Seconds(0.5));
  serverApps.Stop(Seconds(simStop));

  const uint32_t packetSize = 1400;
  const uint32_t minTransferSize = 2 * 1024 * 1024;

  ApplicationContainer clientApps;

  for (uint32_t i = 0; i < 2; ++i) {
    BulkSendHelper httpClient("ns3::TcpSocketFactory",
                              InetSocketAddress(remoteHostAddr, httpPort));
    httpClient.SetAttribute("MaxBytes", UintegerValue(minTransferSize));
    httpClient.SetAttribute("SendSize", UintegerValue(packetSize));
    ApplicationContainer app = httpClient.Install(ueNodes.Get(i));
    app.Start(Seconds(1.0 + i * 0.1));
    app.Stop(Seconds(simStop));
    clientApps.Add(app);
  }

  for (uint32_t i = 2; i < 4; ++i) {
    BulkSendHelper httpsClient("ns3::TcpSocketFactory",
                               InetSocketAddress(remoteHostAddr, httpsPort));
    httpsClient.SetAttribute("MaxBytes", UintegerValue(minTransferSize));
    httpsClient.SetAttribute("SendSize", UintegerValue(packetSize));
    ApplicationContainer app = httpsClient.Install(ueNodes.Get(i));
    app.Start(Seconds(1.2 + (i - 2) * 0.1));
    app.Stop(Seconds(simStop));
    clientApps.Add(app);
  }

  for (uint32_t i = 4; i < 6; ++i) {
    BulkSendHelper videoClient("ns3::TcpSocketFactory",
                               InetSocketAddress(remoteHostAddr, videoPort));
    videoClient.SetAttribute("MaxBytes", UintegerValue(3 * 1024 * 1024));
    videoClient.SetAttribute("SendSize", UintegerValue(packetSize));
    ApplicationContainer app = videoClient.Install(ueNodes.Get(i));
    app.Start(Seconds(1.4 + (i - 4) * 0.1));
    app.Stop(Seconds(simStop));
    clientApps.Add(app);
  }

  for (uint32_t i = 6; i < 8; ++i) {
    OnOffHelper voipClient("ns3::UdpSocketFactory",
                           InetSocketAddress(remoteHostAddr, voipPort));
    voipClient.SetAttribute("DataRate", DataRateValue(DataRate("1.5Mbps")));
    voipClient.SetAttribute("PacketSize", UintegerValue(packetSize));
    voipClient.SetAttribute("OnTime",
                            StringValue("ns3::ConstantRandomVariable[Constant=1.0]"));
    voipClient.SetAttribute("OffTime",
                            StringValue("ns3::ConstantRandomVariable[Constant=0.0]"));
    ApplicationContainer app = voipClient.Install(ueNodes.Get(i));
    app.Start(Seconds(1.6 + (i - 6) * 0.1));
    app.Stop(Seconds(simStop));
    clientApps.Add(app);
  }

  BulkSendHelper httpExtraClient("ns3::TcpSocketFactory",
                                 InetSocketAddress(remoteHostAddr, httpPort));
  httpExtraClient.SetAttribute("MaxBytes", UintegerValue(2500000));
  httpExtraClient.SetAttribute("SendSize", UintegerValue(packetSize));
  ApplicationContainer httpExtraApp = httpExtraClient.Install(ueNodes.Get(8));
  httpExtraApp.Start(Seconds(1.8));
  httpExtraApp.Stop(Seconds(simStop));
  clientApps.Add(httpExtraApp);

  BulkSendHelper mixedClient("ns3::TcpSocketFactory",
                             InetSocketAddress(remoteHostAddr, httpPort));
  mixedClient.SetAttribute("MaxBytes", UintegerValue(minTransferSize));
  mixedClient.SetAttribute("SendSize", UintegerValue(packetSize));
  ApplicationContainer mixedApp = mixedClient.Install(ueNodes.Get(9));
  mixedApp.Start(Seconds(2.0));
  mixedApp.Stop(Seconds(simStop));
  clientApps.Add(mixedApp);

  std::cout << "HTTP/HTTPS/Video/VoIP/Mixed traffic configured for all UEs."
            << std::endl;
  std::cout << "====================================\n" << std::endl;
}