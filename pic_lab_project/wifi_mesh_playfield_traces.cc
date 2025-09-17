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
#include <iostream>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <iomanip>

using namespace ns3;

static const std::string kOutDir = "wifi_mesh_outputs";

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

  const uint32_t nNodes = 10;
  const double field = 400.0;

  // Nodes: 10 mesh STAs; we’ll pin index 0 as Sayed, last as Sadia
  NodeContainer nodes;
  nodes.Create(nNodes);

  // Mobility: Sayed and Sadia static at corners; middle nodes fixed along the
  // diagonal to ensure multi-hop
  MobilityHelper fixedMob;
  MobilityHelper midMob;
  // Sayed at (0,0), Sadia at (400,400) - Set height to 1.5m for building propagation
  Ptr<ListPositionAllocator> fixedPos = CreateObject<ListPositionAllocator>();
  fixedPos->Add(Vector(0.0, 0.0, 1.5));     // node 0: Sayed
  fixedPos->Add(Vector(field, field, 1.5)); // node n-1: Sadia
  fixedMob.SetPositionAllocator(fixedPos);
  fixedMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  fixedMob.Install(nodes.Get(0));
  fixedMob.Install(nodes.Get(nNodes - 1));

  // Middle nodes placed evenly along the (0,0) -> (400,400) diagonal
  // Group 1: Nodes 1-3 (RandomWalk2d) - High speed, frequent direction changes
  // Group 2: Nodes 4-6 (Gauss-Markov) - Medium speed, smooth movement
  // Group 3: Nodes 7-8 (RandomDirection2d) - High speed, random direction changes
  
  Ptr<ListPositionAllocator> midPos = CreateObject<ListPositionAllocator>();
  for (uint32_t i = 1; i < nNodes - 1; ++i) {
    double frac = static_cast<double>(i) / static_cast<double>(nNodes - 1);
    double x = frac * field;
    double y = frac * field;
    midPos->Add(Vector(x, y, 1.5));  // Set height to 1.5m for building propagation
  }
  
  // Group 1: RandomWalk2d (nodes 1-3) - Increased speed to 200 m/s
  MobilityHelper group1Mob;
  group1Mob.SetPositionAllocator(midPos);
  group1Mob.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
    "Bounds", RectangleValue(Rectangle(0, 400, 0, 400)),
    "Time", TimeValue(Seconds(0.3)),  // More frequent direction changes
    "Speed", StringValue("ns3::ConstantRandomVariable[Constant=200.0]")); // Increased from 50 to 200 m/s
  NodeContainer group1;
  for (uint32_t i = 1; i <= 3; ++i) {
    group1.Add(nodes.Get(i));
  }
  group1Mob.Install(group1);
  
  // Group 2: RandomWalk2d (nodes 4-6) - Medium speed, less frequent direction changes
  MobilityHelper group2Mob;
  group2Mob.SetPositionAllocator(midPos);
  group2Mob.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
    "Bounds", RectangleValue(Rectangle(0, 400, 0, 400)),
    "Time", TimeValue(Seconds(1.0)),  // Less frequent direction changes
    "Speed", StringValue("ns3::ConstantRandomVariable[Constant=150.0]")); // 150 m/s
  NodeContainer group2;
  for (uint32_t i = 4; i <= 6; ++i) {
    group2.Add(nodes.Get(i));
  }
  group2Mob.Install(group2);
  
  // Group 3: RandomWalk2d (nodes 7-8) - High speed, very frequent direction changes
  MobilityHelper group3Mob;
  group3Mob.SetPositionAllocator(midPos);
  group3Mob.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
    "Bounds", RectangleValue(Rectangle(0, 400, 0, 400)),
    "Time", TimeValue(Seconds(0.1)),  // Very frequent direction changes
    "Speed", StringValue("ns3::ConstantRandomVariable[Constant=200.0]")); // 200 m/s
  NodeContainer group3;
  for (uint32_t i = 7; i <= 8; ++i) {
    group3.Add(nodes.Get(i));
  }
  group3Mob.Install(group3);

  // Buildings / obstacles
  // Four horizontal wall segments: two below y=200 at y≈100, two above at y≈300
  // Left and right edge segments; thickness ~8 m, height 10 m
  Ptr<Building> leftBelow = CreateObject<Building>();
  leftBelow->SetBoundaries(Box(0.0, 60.0, 96.0, 104.0, 0.0, 10.0));

  Ptr<Building> rightBelow = CreateObject<Building>();
  rightBelow->SetBoundaries(Box(340.0, 400.0, 96.0, 104.0, 0.0, 10.0));

  Ptr<Building> leftAbove = CreateObject<Building>();
  leftAbove->SetBoundaries(Box(0.0, 60.0, 296.0, 304.0, 0.0, 10.0));

  Ptr<Building> rightAbove = CreateObject<Building>();
  rightAbove->SetBoundaries(Box(340.0, 400.0, 296.0, 304.0, 0.0, 10.0));

  // Additional mid-field clusters matching the requested layout
  // y ≈ 250: one 3-block segment (≈60 m) and one 4-block segment (≈80 m)
  Ptr<Building> cluster250a = CreateObject<Building>();
  cluster250a->SetBoundaries(Box(110.0, 170.0, 246.0, 254.0, 0.0, 10.0));
  Ptr<Building> cluster250b = CreateObject<Building>();
  cluster250b->SetBoundaries(Box(200.0, 280.0, 246.0, 254.0, 0.0, 10.0));

  // y ≈ 50: one 4-block segment near the right
  Ptr<Building> cluster50 = CreateObject<Building>();
  cluster50->SetBoundaries(Box(300.0, 380.0, 46.0, 54.0, 0.0, 10.0));

  // Combine all buildings into a single container
  BuildingContainer buildings;
  buildings.Add(leftBelow);
  buildings.Add(rightBelow);
  buildings.Add(leftAbove);
  buildings.Add(rightAbove);
  buildings.Add(cluster250a);
  buildings.Add(cluster250b);
  buildings.Add(cluster50);

  BuildingsHelper::Install(
      nodes); // classify nodes indoor/outdoor as they move (kept simple)

  // Emit an ASCII map of positions and obstacles before simulation starts
  WriteAsciiPositionGrid(nodes, buildings, field);

  // Wi‑Fi channel/PHY with low Tx power + limited range to force multi-hop
  YansWifiChannelHelper chan;
  chan.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
  
  // Add building-aware propagation loss model for realistic indoor/outdoor effects
  // BuildingsHelper must be installed before this to classify nodes as indoor/outdoor
  chan.AddPropagationLoss("ns3::HybridBuildingsPropagationLossModel");
  
  // Use range cap small enough to connect only adjacent diagonal neighbors
  // Diagonal spacing ≈ 62.8 m for 10 nodes; set MaxRange to ~85 m
  chan.AddPropagationLoss("ns3::RangePropagationLossModel", "MaxRange",
                          DoubleValue(65.0));

  YansWifiPhyHelper phy;
  phy.SetChannel(chan.Create());
  phy.Set("TxPowerStart", DoubleValue(7.0));
  phy.Set("TxPowerEnd", DoubleValue(7.0));
  phy.Set("RxNoiseFigure", DoubleValue(7.0));
  // Ensure outputs directory exists at project root
  std::system(("mkdir -p " + kOutDir).c_str());

  // 802.11s mesh
  MeshHelper mesh = MeshHelper::Default();
  mesh.SetStackInstaller("ns3::Dot11sStack");
  mesh.SetSpreadInterfaceChannels(MeshHelper::SPREAD_CHANNELS);
  mesh.SetMacType("RandomStart", TimeValue(Seconds(0.2)));
  NetDeviceContainer devs = mesh.Install(phy, nodes);

  // Enable PCAP after devices/PHY are created
  phy.EnablePcapAll(kOutDir + "/" + kPcapPrefix, true);

  // ASCII traces (.tr)
  phy.EnableAsciiAll(kOutDir + "/" + kAsciiTracesPrefix);
  

  // Internet + IPs
  InternetStackHelper internet;
  internet.Install(nodes);
  Ipv4AddressHelper ip;
  ip.SetBase("10.0.0.0", "255.255.255.0");
  Ipv4InterfaceContainer ifs = ip.Assign(devs);

  // Traffic: UDP both directions + TCP both directions + IoT traffic
  // Timing strategy: Stagger traffic types to create varied network conditions
  const uint16_t udpPortA = 5000;
  const uint16_t udpPortB = 5001;
  const uint16_t tcpPortA = 6000;
  const uint16_t tcpPortB = 6001;
  
  // UDP sinks and clients - Start early to establish baseline
  UdpServerHelper udpSinkA(udpPortA);
  UdpServerHelper udpSinkB(udpPortB);
  ApplicationContainer udpSinks;
  udpSinks.Add(udpSinkA.Install(nodes.Get(nNodes - 1)));
  udpSinks.Add(udpSinkB.Install(nodes.Get(0)));
  udpSinks.Start(Seconds(1.0));  // Start sinks early
  udpSinks.Stop(Seconds(10.0));

  // UDP Client A: Sayed -> Sadia (starts at 1.5s with random delay)
  OnOffHelper udpClientA("ns3::UdpSocketFactory", InetSocketAddress(ifs.GetAddress(nNodes - 1), udpPortA));
  udpClientA.SetConstantRate(DataRate("4Mbps"), 1200);
  udpClientA.SetAttribute("StartTime", TimeValue(Seconds(1.5)));  // Earlier start
  udpClientA.SetAttribute("StopTime", TimeValue(Seconds(10.0)));
  ApplicationContainer a1 = udpClientA.Install(nodes.Get(0));

  // UDP Client B: Sadia -> Sayed (starts at 2.0s with random delay)
  OnOffHelper udpClientB("ns3::UdpSocketFactory", InetSocketAddress(ifs.GetAddress(0), udpPortB));
  udpClientB.SetConstantRate(DataRate("4Mbps"), 1200);
  udpClientB.SetAttribute("StartTime", TimeValue(Seconds(2.0)));  // Earlier start
  udpClientB.SetAttribute("StopTime", TimeValue(Seconds(10.0)));
  ApplicationContainer a2 = udpClientB.Install(nodes.Get(nNodes - 1));

  // TCP sinks and clients - Start after UDP to create layered traffic
  PacketSinkHelper tcpSinkA("ns3::TcpSocketFactory",
                            InetSocketAddress(Ipv4Address::GetAny(), tcpPortA));
  PacketSinkHelper tcpSinkB("ns3::TcpSocketFactory",
                            InetSocketAddress(Ipv4Address::GetAny(), tcpPortB));
  ApplicationContainer tcpSinks;
  tcpSinks.Add(tcpSinkA.Install(nodes.Get(nNodes - 1)));
  tcpSinks.Add(tcpSinkB.Install(nodes.Get(0)));
  tcpSinks.Start(Seconds(1.0));  // Start sinks early
  tcpSinks.Stop(Seconds(10.0));

  // TCP bulk both ways - Start after UDP to create traffic layering
  // TCP A: Sayed -> Sadia (starts at 2.5s)
  BulkSendHelper tcpA("ns3::TcpSocketFactory",
                      InetSocketAddress(ifs.GetAddress(nNodes - 1), tcpPortA));
  tcpA.SetAttribute("MaxBytes", UintegerValue(0)); // unlimited
  ApplicationContainer tA = tcpA.Install(nodes.Get(0));
  tA.Start(Seconds(2.5));  // Earlier start, after UDP
  tA.Stop(Seconds(10.0));

  // TCP B: Sadia -> Sayed (starts at 3.0s)
  BulkSendHelper tcpB("ns3::TcpSocketFactory",
                      InetSocketAddress(ifs.GetAddress(0), tcpPortB));
  tcpB.SetAttribute("MaxBytes", UintegerValue(0));
  ApplicationContainer tB = tcpB.Install(nodes.Get(nNodes - 1));
  tB.Start(Seconds(3.0));  // Earlier start, after TCP A
  tB.Stop(Seconds(10.0));

  // IoT-like UDP bursts - Start much earlier with varied timing
  // Each IoT device (nodes 1-8) sends data to Sayed with different patterns
  for (uint32_t i = 1; i < nNodes - 1; ++i) {
    // IoT Client: Each device sends to Sayed with unique port (7001-7008)
    UdpClientHelper iotToSayed(ifs.GetAddress(0), 7000 + i);
    iotToSayed.SetAttribute("MaxPackets", UintegerValue(200));
    iotToSayed.SetAttribute("Interval", TimeValue(Seconds(1.5)));  // More frequent than before
    iotToSayed.SetAttribute("PacketSize", UintegerValue(100));
    ApplicationContainer c1 = iotToSayed.Install(nodes.Get(i));
    
    // Staggered start times: Group 1 (1-3) starts at 1.8s, Group 2 (4-6) at 2.2s, Group 3 (7-8) at 2.6s
    double startTime;
    if (i <= 3) {
      startTime = 1.8 + 0.1 * (i - 1);  // Group 1: 1.8s, 1.9s, 2.0s
    } else if (i <= 6) {
      startTime = 2.2 + 0.1 * (i - 4);  // Group 2: 2.2s, 2.3s, 2.4s
    } else {
      startTime = 2.6 + 0.1 * (i - 7);  // Group 3: 2.6s, 2.7s
    }
    
    c1.Start(Seconds(startTime));  // Much earlier start
    c1.Stop(Seconds(10.0));
    
    // IoT Server: Sayed receives from each IoT device
    UdpServerHelper iotSinkSayed(7000 + i);
    ApplicationContainer s1 = iotSinkSayed.Install(nodes.Get(0));
    s1.Start(Seconds(1.0));  // Start server early
    s1.Stop(Seconds(10.0));
  }

  // FlowMonitor for KPIs
  FlowMonitorHelper fm;
  Ptr<FlowMonitor> monitor = fm.InstallAll();

  // NetAnim: label ends
  AnimationInterface anim(
      kOutDir + "/" + kNetAnimFile);
  anim.EnablePacketMetadata(true);
  anim.UpdateNodeDescription(nodes.Get(0), "Sayed");
  anim.UpdateNodeColor(nodes.Get(0), 0, 150, 255);
  anim.UpdateNodeDescription(nodes.Get(nNodes - 1), "Sadia");
  anim.UpdateNodeColor(nodes.Get(nNodes - 1), 255, 120, 0);
  // anim.UpdateNodeImage(nodes.Get(nNodes - 1)->GetId(), 0);

  // IPv4 L3 ASCII tracing (emit packets at IP layer to ASCII file)
  {
    AsciiTraceHelper ascii;
    Ptr<OutputStreamWrapper> ipStream = ascii.CreateFileStream(kOutDir + "/ipv4-l3.tr");
    internet.EnableAsciiIpv4All(ipStream);
  }

  Simulator::Stop(Seconds(10.0));
  Simulator::Run();
  monitor->SerializeToXmlFile(
      kOutDir + "/" + kFlowmonFile, true, true);
  Simulator::Destroy();
  return 0;
}