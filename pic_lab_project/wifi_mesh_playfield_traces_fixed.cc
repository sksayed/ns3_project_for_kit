#include "ns3/applications-module.h"
#include "ns3/buildings-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mesh-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/trace-helper.h"
#include "ns3/wifi-helper.h"
#include "ns3/yans-wifi-helper.h"
#include "ns3/olsr-helper.h"
#include "ns3/global-route-manager.h"
#include <iostream>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <iomanip>

using namespace ns3;

static const std::string kOutDir = "wifi_mesh_outputs";

// Function to update building position dynamically
void UpdateBuildingPosition(Ptr<Building> building, Vector newPosition, double width, double height) {
    Box newBounds(newPosition.x, newPosition.x + width, 
                  newPosition.y, newPosition.y + height, 0.0, 10.0);
    building->SetBoundaries(newBounds);
    std::cout << "Building moved to (" << newPosition.x << ", " << newPosition.y << ")" << std::endl;
}

// Output file name constants for easy configuration
static const std::string kPcapPrefix = "wifi_mesh_playfield_rw_pcap";
static const std::string kAsciiTracesPrefix = "wifi_mesh_playfield_ascii_traces";
static const std::string kNetAnimFile = "netanim-wifi-mesh-playfield-rw.xml";
static const std::string kFlowmonFile = "flowmon-wifi-mesh-playfield-rw.xml";

// Write an ASCII grid of node and building positions to wifi_mesh_outputs/position_grid.txt
static void WriteAsciiPositionGrid(const NodeContainer &nodes,
                                   const BuildingContainer &buildings,
                                   double fieldMeters,
                                   double cellMeters = 10.0,
                                   const std::string &outDir = kOutDir,
                                   const std::string &outName = "position_grid.txt") {
  const double fieldMin = 0.0;
  const double fieldMax = fieldMeters;
  const int W = static_cast<int>((fieldMax - fieldMin) / cellMeters) + 1;
  const int H = W;

  std::vector<std::string> grid(H, std::string(W, '.'));

  // Mark buildings as '#'
  for (uint32_t b = 0; b < buildings.GetN(); ++b) {
    Ptr<Building> bd = buildings.Get(b);
    Box bx = bd->GetBoundaries();
    int x0 = std::max(0, static_cast<int>(std::floor((bx.xMin - fieldMin) / cellMeters)));
    int x1 = std::min(W - 1, static_cast<int>(std::floor((bx.xMax - fieldMin) / cellMeters)));
    int y0 = std::max(0, static_cast<int>(std::floor((bx.yMin - fieldMin) / cellMeters)));
    int y1 = std::min(H - 1, static_cast<int>(std::floor((bx.yMax - fieldMin) / cellMeters)));
    for (int gy = y0; gy <= y1; ++gy) {
      for (int gx = x0; gx <= x1; ++gx) {
        grid[H - 1 - gy][gx] = '#';
      }
    }
  }

  auto nodeChar = [&](uint32_t i) -> char {
    if (i == 0) return 'S';
    if (i + 1 == nodes.GetN()) return 'D';
    if (i < 10) return static_cast<char>('0' + static_cast<int>(i));
    return static_cast<char>('a' + static_cast<int>(i - 10));
  };

  // Overlay node markers
  for (uint32_t i = 0; i < nodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = nodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    int gx = static_cast<int>(std::round((p.x - fieldMin) / cellMeters));
    int gy = static_cast<int>(std::round((p.y - fieldMin) / cellMeters));
    if (gx < 0 || gx >= W || gy < 0 || gy >= H) continue;
    grid[H - 1 - gy][gx] = nodeChar(i);
  }

  std::system(("mkdir -p " + outDir).c_str());
  std::ofstream ofs(outDir + "/" + outName);
  ofs << "Grid " << W << "x" << H << " (cell=" << cellMeters << "m). Top=+Y, Right=+X\n";
  ofs << "Legend: '.'=free, '#'=building, 'S'=Sayed(0), 'D'=Sadia(" << (nodes.GetN() - 1)
      << "), digits/letters=other UEs\n\n";

  // X-axis header every 5 cells (label in tens of meters modulo 100)
  ofs << "     ";
  for (int gx = 0; gx < W; ++gx) {
    if (gx % 5 == 0) {
      ofs << std::setw(2) << std::setfill(' ') << ((gx * static_cast<int>(cellMeters)) / 10 % 100);
    } else {
      ofs << " ";
    }
  }
  ofs << "\n";

  for (int gy = 0; gy < H; ++gy) {
    int yMeters = static_cast<int>((H - 1 - gy) * cellMeters);
    ofs << std::setw(4) << yMeters << " " << grid[gy] << "\n";
  }

  ofs << "\nNodes:\n";
  for (uint32_t i = 0; i < nodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = nodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    std::string name = (i == 0 ? "Sayed" : (i + 1 == nodes.GetN() ? "Sadia" : ("UE" + std::to_string(i))));
    ofs << " - " << std::setw(6) << name << " (node " << i << "): ("
        << std::fixed << std::setprecision(1) << p.x << ", " << p.y << ")\n";
  }

  ofs << "\nBuildings (xMin..xMax, yMin..yMax):\n";
  for (uint32_t b = 0; b < buildings.GetN(); ++b) {
    Box bx = buildings.Get(b)->GetBoundaries();
    ofs << " - B" << b << ": x[" << bx.xMin << "," << bx.xMax << "], y[" << bx.yMin << "," << bx.yMax << "]\n";
  }
  ofs.close();
}

int main(int argc, char **argv) {
  // Basics
  PacketMetadata::Enable();
  Packet::EnablePrinting();
  
  // Enable debugging for mesh and routing
  LogComponentEnable("MeshL2RoutingProtocol", LOG_LEVEL_DEBUG);
  LogComponentEnable("OlsrRoutingProtocol", LOG_LEVEL_DEBUG);
  LogComponentEnable("GlobalRouteManager", LOG_LEVEL_DEBUG);
  LogComponentEnable("Ipv4GlobalRouting", LOG_LEVEL_DEBUG);
  LogComponentEnable("TcpSocketBase", LOG_LEVEL_DEBUG);
  LogComponentEnable("UdpServer", LOG_LEVEL_INFO);

  const uint32_t nNodes = 10;
  const double field = 400.0;

  // Nodes: 10 mesh STAs; we'll pin index 0 as Sayed, last as Sadia
  NodeContainer nodes;
  nodes.Create(nNodes);

  // Mobility: Sayed and Sadia static at corners; middle nodes fixed along the diagonal
  MobilityHelper fixedMob;
  Ptr<ListPositionAllocator> fixedPos = CreateObject<ListPositionAllocator>();
  fixedPos->Add(Vector(0.0, 0.0, 1.5));     // node 0: Sayed
  fixedPos->Add(Vector(field, field, 1.5)); // node n-1: Sadia
  fixedMob.SetPositionAllocator(fixedPos);
  fixedMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  fixedMob.Install(nodes.Get(0));
  fixedMob.Install(nodes.Get(nNodes - 1));

  // Middle nodes placed evenly along the (0,0) -> (400,400) diagonal
  Ptr<ListPositionAllocator> midPos = CreateObject<ListPositionAllocator>();
  for (uint32_t i = 1; i < nNodes - 1; ++i) {
    double frac = static_cast<double>(i) / static_cast<double>(nNodes - 1);
    double x = frac * field;
    double y = frac * field;
    midPos->Add(Vector(x, y, 1.5));  // Set height to 1.5m for building propagation
  }
  
  // All middle nodes use RandomWalk2d with moderate speed
  MobilityHelper midMob;
  midMob.SetPositionAllocator(midPos);
  midMob.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
    "Bounds", RectangleValue(Rectangle(0, 400, 0, 400)),
    "Time", TimeValue(Seconds(1.0)),
    "Speed", StringValue("ns3::ConstantRandomVariable[Constant=50.0]"));
  
  NodeContainer middleNodes;
  for (uint32_t i = 1; i < nNodes - 1; ++i) {
    middleNodes.Add(nodes.Get(i));
  }
  midMob.Install(middleNodes);

  // Buildings / obstacles (same as original)
  Ptr<Building> leftBelow = CreateObject<Building>();
  leftBelow->SetBoundaries(Box(0.0, 60.0, 96.0, 104.0, 0.0, 10.0));

  Ptr<Building> rightBelow = CreateObject<Building>();
  rightBelow->SetBoundaries(Box(340.0, 400.0, 96.0, 104.0, 0.0, 10.0));

  Ptr<Building> leftAbove = CreateObject<Building>();
  leftAbove->SetBoundaries(Box(0.0, 60.0, 296.0, 304.0, 0.0, 10.0));

  Ptr<Building> rightAbove = CreateObject<Building>();
  rightAbove->SetBoundaries(Box(340.0, 400.0, 296.0, 304.0, 0.0, 10.0));

  Ptr<Building> cluster250a = CreateObject<Building>();
  cluster250a->SetBoundaries(Box(80.0, 140.0, 220.0, 228.0, 0.0, 15.0));  // Moved left, higher
  Ptr<Building> cluster250b = CreateObject<Building>();
  cluster250b->SetBoundaries(Box(170.0, 250.0, 220.0, 228.0, 0.0, 12.0));  // Moved left, different height

  Ptr<Building> cluster50 = CreateObject<Building>();
  cluster50->SetBoundaries(Box(255.0, 335.0, 20.0, 28.0, 0.0, 18.0));  // Moved 15m more left, tallest building

  BuildingContainer buildings;
  buildings.Add(leftBelow);
  buildings.Add(rightBelow);
  buildings.Add(leftAbove);
  buildings.Add(rightAbove);
  buildings.Add(cluster250a);
  buildings.Add(cluster250b);
  buildings.Add(cluster50);

  BuildingsHelper::Install(nodes);
  
  // Schedule building movements during simulation
  std::cout << "Scheduling building movements..." << std::endl;
  
  // Move cluster250a building at different times (moved left, higher)
  Simulator::Schedule(Seconds(5.0), &UpdateBuildingPosition, cluster250a, 
                     Vector(150.0, 180.0, 0.0), 60.0, 8.0);
  Simulator::Schedule(Seconds(8.0), &UpdateBuildingPosition, cluster250a, 
                     Vector(250.0, 130.0, 0.0), 60.0, 8.0);
  Simulator::Schedule(Seconds(12.0), &UpdateBuildingPosition, cluster250a, 
                     Vector(100.0, 280.0, 0.0), 60.0, 8.0);
  
  // Move cluster250b building (moved left)
  Simulator::Schedule(Seconds(6.0), &UpdateBuildingPosition, cluster250b, 
                     Vector(200.0, 180.0, 0.0), 80.0, 8.0);
  Simulator::Schedule(Seconds(10.0), &UpdateBuildingPosition, cluster250b, 
                     Vector(130.0, 300.0, 0.0), 80.0, 8.0);
  
  // Move cluster50 building (moved 15m more left)
  Simulator::Schedule(Seconds(7.0), &UpdateBuildingPosition, cluster50, 
                     Vector(255.0, 80.0, 0.0), 80.0, 8.0);
  Simulator::Schedule(Seconds(11.0), &UpdateBuildingPosition, cluster50, 
                     Vector(215.0, 180.0, 0.0), 80.0, 8.0);
  
  //WriteAsciiPositionGrid(nodes, buildings, field);

  // Wi‑Fi channel/PHY with increased range for better connectivity
  YansWifiChannelHelper chan;
  chan.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
  chan.AddPropagationLoss("ns3::HybridBuildingsPropagationLossModel");
  
  // INCREASED RANGE: Set MaxRange to 200m to ensure connectivity across diagonal
  chan.AddPropagationLoss("ns3::RangePropagationLossModel", "MaxRange", DoubleValue(200.0));

  YansWifiPhyHelper phy;
  phy.SetChannel(chan.Create());
  phy.Set("TxPowerStart", DoubleValue(20.0));  // Increased from 7.0 to 20.0 dBm
  phy.Set("TxPowerEnd", DoubleValue(20.0));
  phy.Set("RxNoiseFigure", DoubleValue(7.0));
  
  std::system(("mkdir -p " + kOutDir).c_str());

  // 802.11s mesh with proper configuration
  MeshHelper mesh = MeshHelper::Default();
  mesh.SetStackInstaller("ns3::Dot11sStack");
  mesh.SetSpreadInterfaceChannels(MeshHelper::SPREAD_CHANNELS);
  mesh.SetMacType("RandomStart", TimeValue(Seconds(0.1)));  // Faster startup
  
  // Configure mesh routing protocol
  mesh.SetNumberOfInterfaces(1);
  
  NetDeviceContainer devs = mesh.Install(phy, nodes);

  // Enable PCAP and ASCII traces
  phy.EnablePcapAll(kOutDir + "/" + kPcapPrefix, true);
  phy.EnableAsciiAll(kOutDir + "/" + kAsciiTracesPrefix);

  // Internet + IPs
  InternetStackHelper internet;
  
  // Add OLSR routing protocol for better mesh routing
  OlsrHelper olsr;
  Ipv4ListRoutingHelper list;
  list.Add(olsr, 10);
  internet.SetRoutingHelper(list);
  
  internet.Install(nodes);
  
  Ipv4AddressHelper ip;
  ip.SetBase("10.0.0.0", "255.255.255.0");
  Ipv4InterfaceContainer ifs = ip.Assign(devs);
  
  // CRITICAL: Enable global routing for mesh networks
  Ipv4GlobalRoutingHelper::PopulateRoutingTables();

  // Traffic: Simplified and focused on Sayed -> Sadia communication
  const uint16_t udpPort = 5000;
  const uint16_t tcpPort = 6000;
  
  // UDP Server on Sadia (node n-1)
  UdpServerHelper udpSink(udpPort);
  ApplicationContainer udpSinkApp = udpSink.Install(nodes.Get(nNodes - 1));
  udpSinkApp.Start(Seconds(1.0));
  udpSinkApp.Stop(Seconds(15.0));

  // UDP Client on Sayed (node 0) -> Sadia
  OnOffHelper udpClient("ns3::UdpSocketFactory", 
                       InetSocketAddress(ifs.GetAddress(nNodes - 1), udpPort));
  udpClient.SetConstantRate(DataRate("2Mbps"), 1200);
  udpClient.SetAttribute("StartTime", TimeValue(Seconds(3.0)));  // Start after mesh setup
  udpClient.SetAttribute("StopTime", TimeValue(Seconds(15.0)));
  ApplicationContainer udpClientApp = udpClient.Install(nodes.Get(0));

  // TCP Server on Sadia (node n-1)
  PacketSinkHelper tcpSink("ns3::TcpSocketFactory",
                          InetSocketAddress(Ipv4Address::GetAny(), tcpPort));
  ApplicationContainer tcpSinkApp = tcpSink.Install(nodes.Get(nNodes - 1));
  tcpSinkApp.Start(Seconds(1.0));
  tcpSinkApp.Stop(Seconds(15.0));

  // TCP Client on Sayed (node 0) -> Sadia
  BulkSendHelper tcpClient("ns3::TcpSocketFactory",
                          InetSocketAddress(ifs.GetAddress(nNodes - 1), tcpPort));
  tcpClient.SetAttribute("MaxBytes", UintegerValue(0)); // unlimited
  ApplicationContainer tcpClientApp = tcpClient.Install(nodes.Get(0));
  tcpClientApp.Start(Seconds(4.0));  // Start after UDP
  tcpClientApp.Stop(Seconds(15.0));

  // FlowMonitor for KPIs
  FlowMonitorHelper fm;
  Ptr<FlowMonitor> monitor = fm.InstallAll();

  // NetAnim: label ends
  AnimationInterface anim(kOutDir + "/" + kNetAnimFile);
  anim.EnablePacketMetadata(true);
  anim.UpdateNodeDescription(nodes.Get(0), "Sayed");
  anim.UpdateNodeColor(nodes.Get(0), 0, 150, 255);
  anim.UpdateNodeDescription(nodes.Get(nNodes - 1), "Sadia");
  anim.UpdateNodeColor(nodes.Get(nNodes - 1), 255, 120, 0);

  // IPv4 L3 ASCII tracing
  {
    AsciiTraceHelper ascii;
    Ptr<OutputStreamWrapper> ipStream = ascii.CreateFileStream(kOutDir + "/ipv4-l3.tr");
    internet.EnableAsciiIpv4All(ipStream);
  }

  // CRITICAL: Allow time for mesh formation and route discovery
  std::cout << "Starting simulation - allowing time for mesh formation..." << std::endl;
  
  Simulator::Stop(Seconds(15.0));
  Simulator::Run();
  
  monitor->SerializeToXmlFile(kOutDir + "/" + kFlowmonFile, true, true);
  Simulator::Destroy();
  
  std::cout << "Simulation completed!" << std::endl;
  return 0;
}
