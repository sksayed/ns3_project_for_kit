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
#include <cstdlib>

using namespace ns3;

int main(int argc, char **argv) {
  PacketMetadata::Enable();
  Packet::EnablePrinting();

  const uint32_t nUes = 10; // nodes 0..9; 0 and 9 are endpoints
  const double field = 400.0;
  const double simStop = 10.0;

  // Create UE nodes and two eNB nodes (two towers)
  NodeContainer ueNodes;
  ueNodes.Create(nUes);
  NodeContainer enbNodes;
  enbNodes.Create(2);

  // Mobility: replicate layout for UEs
  MobilityHelper fixedMob;
  MobilityHelper midMob;
  Ptr<ListPositionAllocator> fixedPos = CreateObject<ListPositionAllocator>();
  fixedPos->Add(Vector(0.0, 0.0, 0.0));     // UE 0: Sayed
  fixedPos->Add(Vector(field, field, 0.0)); // UE 9: Sadia
  fixedMob.SetPositionAllocator(fixedPos);
  fixedMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  fixedMob.Install(ueNodes.Get(0));
  fixedMob.Install(ueNodes.Get(nUes - 1));

  Ptr<ListPositionAllocator> midPos = CreateObject<ListPositionAllocator>();
  for (uint32_t i = 1; i < nUes - 1; ++i) {
    double frac = static_cast<double>(i) / static_cast<double>(nUes - 1);
    double x = frac * field;
    double y = frac * field;
    midPos->Add(Vector(x, y, 0.0));
  }
  midMob.SetPositionAllocator(midPos);
  midMob.SetMobilityModel(
      "ns3::RandomWalk2dMobilityModel", "Bounds",
      RectangleValue(Rectangle(0, 400, 0, 400)), "Time",
      TimeValue(Seconds(0.5)), "Speed",
      StringValue("ns3::ConstantRandomVariable[Constant=1.0]"));
  NodeContainer mids;
  for (uint32_t i = 1; i < nUes - 1; ++i) {
    mids.Add(ueNodes.Get(i));
  }
  midMob.Install(mids);

  // eNB positions (left-center and right-center)
  MobilityHelper enbMob;
  Ptr<ListPositionAllocator> enbPos = CreateObject<ListPositionAllocator>();
  enbPos->Add(Vector(field * 0.25, field * 0.5, 15.0));
  enbPos->Add(Vector(field * 0.75, field * 0.5, 15.0));
  enbMob.SetPositionAllocator(enbPos);
  enbMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  enbMob.Install(enbNodes);

  // Buildings / obstacles (same as Wi-Fi scenario)
  Ptr<Building> leftBelow = CreateObject<Building>();
  leftBelow->SetBoundaries(Box(0.0, 60.0, 96.0, 104.0, 0.0, 10.0));
  Ptr<Building> rightBelow = CreateObject<Building>();
  rightBelow->SetBoundaries(Box(340.0, 400.0, 96.0, 104.0, 0.0, 10.0));
  Ptr<Building> leftAbove = CreateObject<Building>();
  leftAbove->SetBoundaries(Box(0.0, 60.0, 296.0, 304.0, 0.0, 10.0));
  Ptr<Building> rightAbove = CreateObject<Building>();
  rightAbove->SetBoundaries(Box(340.0, 400.0, 296.0, 304.0, 0.0, 10.0));
  Ptr<Building> cluster250a = CreateObject<Building>();
  cluster250a->SetBoundaries(Box(110.0, 170.0, 246.0, 254.0, 0.0, 10.0));
  Ptr<Building> cluster250b = CreateObject<Building>();
  cluster250b->SetBoundaries(Box(200.0, 280.0, 246.0, 254.0, 0.0, 10.0));
  Ptr<Building> cluster50 = CreateObject<Building>();
  cluster50->SetBoundaries(Box(300.0, 380.0, 46.0, 54.0, 0.0, 10.0));
  BuildingContainer buildings;
  buildings.Add(leftBelow);
  buildings.Add(rightBelow);
  buildings.Add(leftAbove);
  buildings.Add(rightAbove);
  buildings.Add(cluster250a);
  buildings.Add(cluster250b);
  buildings.Add(cluster50);

  BuildingsHelper::Install(ueNodes);
  BuildingsHelper::Install(enbNodes);

  // Lower transmit powers so coverage is just enough
  Config::SetDefault("ns3::LteEnbPhy::TxPower", DoubleValue(16.0)); // dBm
  Config::SetDefault("ns3::LteUePhy::TxPower", DoubleValue(10.0));  // dBm

  // LTE + EPC
  Ptr<PointToPointEpcHelper> epcHelper = CreateObject<PointToPointEpcHelper>();
  Ptr<LteHelper> lteHelper = CreateObject<LteHelper>();
  lteHelper->SetEpcHelper(epcHelper);

  NetDeviceContainer enbDevs = lteHelper->InstallEnbDevice(enbNodes);
  NetDeviceContainer ueDevs = lteHelper->InstallUeDevice(ueNodes);

  // Internet stack on UEs via EPC-assigned IPs
  InternetStackHelper internet;
  internet.Install(ueNodes);
  Ipv4InterfaceContainer ueIpIfaces =
      epcHelper->AssignUeIpv4Address(NetDeviceContainer(ueDevs));

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

  // Ensure outputs directory exists
  std::system("mkdir -p Lte_outputs");

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
  epcPos->Add(Vector(field * 0.5, field + 100.0, 0.0)); // Position PGW near remote host
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
  Ipv4InterfaceContainer internetIfaces = ipv4h.Assign(internetDevices);

  Ipv4StaticRoutingHelper ipv4RoutingHelper;
  Ptr<Ipv4StaticRouting> remoteHostStaticRouting =
      ipv4RoutingHelper.GetStaticRouting(remoteHost->GetObject<Ipv4>());
  remoteHostStaticRouting->SetDefaultRoute(
      epcHelper->GetUeDefaultGatewayAddress(), 1);

  // Enable pcap and ascii traces on EPC P2P link with requested prefix
  p2ph.EnablePcapAll("Lte_outputs/tr-epc");
  AsciiTraceHelper ascii;
  Ptr<OutputStreamWrapper> stream =
      ascii.CreateFileStream("Lte_outputs/tr-epc.tr");
  p2ph.EnableAsciiAll(stream);

  // Applications: replicate Wi-Fi case between UE 0 and UE 9
  const uint16_t udpPortA = 5000;
  const uint16_t udpPortB = 5001;
  const uint16_t tcpPortA = 6000;
  const uint16_t tcpPortB = 6001;

  // UDP sinks
  UdpServerHelper udpSinkA(udpPortA);
  UdpServerHelper udpSinkB(udpPortB);
  ApplicationContainer udpSinks;
  udpSinks.Add(udpSinkA.Install(ueNodes.Get(nUes - 1)));
  udpSinks.Add(udpSinkB.Install(ueNodes.Get(0)));
  udpSinks.Start(Seconds(1.0));
  udpSinks.Stop(Seconds(simStop));

  // UDP OnOff sources
  OnOffHelper udpClientA(
      "ns3::UdpSocketFactory",
      InetSocketAddress(ueIpIfaces.GetAddress(nUes - 1), udpPortA));
  udpClientA.SetConstantRate(DataRate("4Mbps"), 1200);
  udpClientA.SetAttribute("StartTime", TimeValue(Seconds(2.0)));
  udpClientA.SetAttribute("StopTime", TimeValue(Seconds(simStop)));
  udpClientA.Install(ueNodes.Get(0));

  OnOffHelper udpClientB("ns3::UdpSocketFactory",
                         InetSocketAddress(ueIpIfaces.GetAddress(0), udpPortB));
  udpClientB.SetConstantRate(DataRate("4Mbps"), 1200);
  udpClientB.SetAttribute("StartTime", TimeValue(Seconds(2.5)));
  udpClientB.SetAttribute("StopTime", TimeValue(Seconds(simStop)));
  udpClientB.Install(ueNodes.Get(nUes - 1));

  // TCP sinks
  PacketSinkHelper tcpSinkA("ns3::TcpSocketFactory",
                            InetSocketAddress(Ipv4Address::GetAny(), tcpPortA));
  PacketSinkHelper tcpSinkB("ns3::TcpSocketFactory",
                            InetSocketAddress(Ipv4Address::GetAny(), tcpPortB));
  ApplicationContainer tcpSinks;
  tcpSinks.Add(tcpSinkA.Install(ueNodes.Get(nUes - 1)));
  tcpSinks.Add(tcpSinkB.Install(ueNodes.Get(0)));
  tcpSinks.Start(Seconds(1.0));
  tcpSinks.Stop(Seconds(simStop));

  // TCP bulk senders
  BulkSendHelper tcpA(
      "ns3::TcpSocketFactory",
      InetSocketAddress(ueIpIfaces.GetAddress(nUes - 1), tcpPortA));
  tcpA.SetAttribute("MaxBytes", UintegerValue(0));
  ApplicationContainer tA = tcpA.Install(ueNodes.Get(0));
  tA.Start(Seconds(3.0));
  tA.Stop(Seconds(simStop));

  BulkSendHelper tcpB("ns3::TcpSocketFactory",
                      InetSocketAddress(ueIpIfaces.GetAddress(0), tcpPortB));
  tcpB.SetAttribute("MaxBytes", UintegerValue(0));
  ApplicationContainer tB = tcpB.Install(ueNodes.Get(nUes - 1));
  tB.Start(Seconds(3.5));
  tB.Stop(Seconds(simStop));

  // IoT-like bursts from middle UEs to UE 0
  for (uint32_t i = 1; i < nUes - 1; ++i) {
    UdpClientHelper iotToSayed(ueIpIfaces.GetAddress(0), 7000 + i);
    iotToSayed.SetAttribute("MaxPackets", UintegerValue(200));
    iotToSayed.SetAttribute("Interval", TimeValue(Seconds(2.0)));
    iotToSayed.SetAttribute("PacketSize", UintegerValue(100));
    ApplicationContainer c1 = iotToSayed.Install(ueNodes.Get(i));
    c1.Start(Seconds(5.0 + 0.1 * i));
    c1.Stop(Seconds(simStop));

    UdpServerHelper iotSinkSayed(7000 + i);
    ApplicationContainer s1 = iotSinkSayed.Install(ueNodes.Get(0));
    s1.Start(Seconds(1.0));
    s1.Stop(Seconds(simStop));
  }

  // FlowMonitor
  FlowMonitorHelper fm;
  Ptr<FlowMonitor> monitor = fm.InstallAll();

  // NetAnim
  AnimationInterface anim("Lte_outputs/tr-netanim-lte-playfield.xml");
  anim.SetMaxPktsPerTraceFile(
      500000); // Increase packet limit to avoid warnings
  anim.EnablePacketMetadata(true);
  anim.UpdateNodeDescription(ueNodes.Get(0), "Sayed");
  anim.UpdateNodeColor(ueNodes.Get(0), 0, 150, 255);
  anim.UpdateNodeDescription(ueNodes.Get(nUes - 1), "Sadia");
  anim.UpdateNodeColor(ueNodes.Get(nUes - 1), 255, 120, 0);
  // eNB visuals (grey)
  anim.UpdateNodeDescription(enbNodes.Get(0), "eNB-0");
  anim.UpdateNodeColor(enbNodes.Get(0), 128, 128, 128);
  anim.UpdateNodeDescription(enbNodes.Get(1), "eNB-1");
  anim.UpdateNodeColor(enbNodes.Get(1), 128, 128, 128);
  // Remote host visuals (green)
  anim.UpdateNodeDescription(remoteHost, "Remote Host");
  anim.UpdateNodeColor(remoteHost, 0, 255, 0);
  
  // EPC nodes visuals
  anim.UpdateNodeDescription(pgw, "PGW");
  anim.UpdateNodeColor(pgw, 128, 0, 128); // Purple
  anim.UpdateNodeDescription(sgw, "SGW");
  anim.UpdateNodeColor(sgw, 255, 0, 255); // Magenta

  Simulator::Stop(Seconds(simStop));
  Simulator::Run();
  monitor->SerializeToXmlFile("Lte_outputs/tr-flowmon-lte-playfield.xml", true,
                              true);
  Simulator::Destroy();
  return 0;
}
