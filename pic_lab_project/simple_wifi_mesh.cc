#include "ns3/applications-module.h"
#include "ns3/buildings-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mesh-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
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

static const std::string kOutDir = "wifi_mesh_backhaul_outputs";

// Function to update building position dynamically
void UpdateBuildingPosition(Ptr<Building> building, Vector newPosition, double width, double height) {
    Box newBounds(newPosition.x, newPosition.x + width, 
                  newPosition.y, newPosition.y + height, 0.0, 10.0);
    building->SetBoundaries(newBounds);
    std::cout << "Building moved to (" << newPosition.x << ", " << newPosition.y << ")" << std::endl;
}

// Output file name constants
static const std::string kPcapPrefix = "wifi_mesh_backhaul_pcap";
static const std::string kAsciiTracesPrefix = "wifi_mesh_backhaul_ascii_traces";
static const std::string kNetAnimFile = "netanim-wifi-mesh-backhaul.xml";
static const std::string kFlowmonFile = "flowmon-wifi-mesh-backhaul.xml";

// Write an ASCII grid of node and building positions
static void WriteAsciiPositionGrid(const NodeContainer &meshNodes,
                                   const NodeContainer &staNodes,
                                   const NodeContainer &backhaulNodes,
                                   const NodeContainer &sayedSadiaNodes,
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

  auto nodeChar = [&](char type, uint32_t i) -> char {
    switch (type) {
      case 'B': return 'B';  // Backhaul
      case 'M': return static_cast<char>('0' + static_cast<int>(i));  // Mesh nodes 0-9
      case 'S': return static_cast<char>('A' + static_cast<int>(i));  // STA nodes A-Z
      case 'Y': return 'Y';  // Sayed
      case 'D': return 'D';  // Sadia
      default: return '?';
    }
  };

  // Overlay node markers
  // Backhaul nodes (marked as 'B')
  for (uint32_t i = 0; i < backhaulNodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = backhaulNodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    int gx = static_cast<int>(std::round((p.x - fieldMin) / cellMeters));
    int gy = static_cast<int>(std::round((p.y - fieldMin) / cellMeters));
    if (gx < 0 || gx >= W || gy < 0 || gy >= H) continue;
    grid[H - 1 - gy][gx] = nodeChar('B', i);
  }
  
  // Mesh nodes (marked as digits)
  for (uint32_t i = 0; i < meshNodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = meshNodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    int gx = static_cast<int>(std::round((p.x - fieldMin) / cellMeters));
    int gy = static_cast<int>(std::round((p.y - fieldMin) / cellMeters));
    if (gx < 0 || gx >= W || gy < 0 || gy >= H) continue;
    grid[H - 1 - gy][gx] = nodeChar('M', i);
  }
  
  // STA nodes (marked as letters)
  for (uint32_t i = 0; i < staNodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = staNodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    int gx = static_cast<int>(std::round((p.x - fieldMin) / cellMeters));
    int gy = static_cast<int>(std::round((p.y - fieldMin) / cellMeters));
    if (gx < 0 || gx >= W || gy < 0 || gy >= H) continue;
    grid[H - 1 - gy][gx] = nodeChar('S', i);
  }
  
  // Sayed and Sadia
  for (uint32_t i = 0; i < sayedSadiaNodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = sayedSadiaNodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    int gx = static_cast<int>(std::round((p.x - fieldMin) / cellMeters));
    int gy = static_cast<int>(std::round((p.y - fieldMin) / cellMeters));
    if (gx < 0 || gx >= W || gy < 0 || gy >= H) continue;
    grid[H - 1 - gy][gx] = (i == 0) ? 'Y' : 'D';  // Sayed=Y, Sadia=D
  }

  std::system(("mkdir -p " + outDir).c_str());
  std::ofstream ofs(outDir + "/" + outName);
  ofs << "Grid " << W << "x" << H << " (cell=" << cellMeters << "m). Top=+Y, Right=+X\n";
  ofs << "Legend: '.'=free, '#'=building, 'B'=Backhaul, '0-9'=Mesh hops, 'A-Z'=STA/UE, 'Y'=Sayed, 'D'=Sadia\n\n";

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
  
  // List backhaul nodes
  for (uint32_t i = 0; i < backhaulNodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = backhaulNodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    ofs << " - Backhaul" << i << " (node " << backhaulNodes.Get(i)->GetId() << "): ("
        << std::fixed << std::setprecision(1) << p.x << ", " << p.y << ")\n";
  }
  
  // List mesh nodes
  for (uint32_t i = 0; i < meshNodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = meshNodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    ofs << " - Mesh" << i << " (node " << meshNodes.Get(i)->GetId() << "): ("
        << std::fixed << std::setprecision(1) << p.x << ", " << p.y << ")\n";
  }
  
  // List STA nodes
  for (uint32_t i = 0; i < staNodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = staNodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    ofs << " - STA" << i << " (node " << staNodes.Get(i)->GetId() << "): ("
        << std::fixed << std::setprecision(1) << p.x << ", " << p.y << ")\n";
  }
  
  // List Sayed and Sadia
  for (uint32_t i = 0; i < sayedSadiaNodes.GetN(); ++i) {
    Ptr<MobilityModel> mm = sayedSadiaNodes.Get(i)->GetObject<MobilityModel>();
    if (!mm) continue;
    Vector p = mm->GetPosition();
    std::string name = (i == 0) ? "Sayed" : "Sadia";
    ofs << " - " << name << " (node " << sayedSadiaNodes.Get(i)->GetId() << "): ("
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
  LogComponentEnable("OnOffApplication", LOG_LEVEL_DEBUG);
  LogComponentEnable("UdpServer", LOG_LEVEL_INFO);

  // Network topology parameters
  const uint32_t nMeshHops = 4;        // Number of mesh hop nodes (fixed APs)
  const uint32_t nStaPerMesh = 2;      // Number of STA nodes per mesh hop
  const uint32_t nTotalStas = nMeshHops * nStaPerMesh;  // Total STA nodes
  const double field = 400.0;           // Keep original field size
  const double simTime = 5.0;          // Reduced simulation time

  std::cout << "Creating backhaul-connected mesh network topology with Sayed & Sadia:" << std::endl;
  std::cout << "- " << nMeshHops << " mesh hop nodes" << std::endl;
  std::cout << "- " << nTotalStas << " STA nodes (" << nStaPerMesh << " per mesh hop)" << std::endl;
  std::cout << "- Sayed and Sadia as special communication endpoints" << std::endl;
  std::cout << "- Backhaul with internet connection" << std::endl;
  std::cout << "- Dynamic building movements preserved" << std::endl;

  // Create nodes
  NodeContainer backhaulNodes;     // Backhaul nodes (internet gateway)
  NodeContainer meshNodes;         // Mesh hop nodes
  NodeContainer staNodes;          // STA/UE nodes
  NodeContainer sayedSadiaNodes;   // Sayed and Sadia nodes
  NodeContainer allNodes;          // All nodes combined

  // Create backhaul node (internet gateway)
  backhaulNodes.Create(1);
  
  // Create mesh hop nodes
  meshNodes.Create(nMeshHops);
  
  // Create STA nodes
  staNodes.Create(nTotalStas);
  
  // Create Sayed and Sadia nodes
  sayedSadiaNodes.Create(2);
  
  // Combine all nodes
  allNodes.Add(backhaulNodes);
  allNodes.Add(meshNodes);
  allNodes.Add(staNodes);
  allNodes.Add(sayedSadiaNodes);

  std::cout << "Total nodes: " << allNodes.GetN() << " (1 backhaul + " 
            << nMeshHops << " mesh + " << nTotalStas << " STA + 2 Sayed/Sadia)" << std::endl;

  // Mobility setup
  MobilityHelper mobility;
  
  // Position backhaul node at the left edge (internet connection point)
  Ptr<ListPositionAllocator> positionAlloc = CreateObject<ListPositionAllocator>();
  positionAlloc->Add(Vector(30.0, field/2, 10.0));  // Backhaul at left edge, elevated
  
  // Position mesh hop nodes at fixed AP coordinates (within 200m range)
  // Mesh0: (50, 50), Mesh1: (150, 100), Mesh2: (250, 150), Mesh3: (350, 200)
  positionAlloc->Add(Vector(50.0, 50.0, 5.0));
  positionAlloc->Add(Vector(150.0, 100.0, 5.0));
  positionAlloc->Add(Vector(250.0, 150.0, 5.0));
  positionAlloc->Add(Vector(350.0, 200.0, 5.0));
  
  // Position STA nodes around their respective mesh hop nodes
  auto getMeshPos = [&](uint32_t idx) -> std::pair<double,double> {
    switch (idx) {
      case 0: return {50.0, 50.0};
      case 1: return {150.0, 100.0};
      case 2: return {250.0, 150.0};
      default: return {350.0, 200.0};
    }
  };

  for (uint32_t i = 0; i < nTotalStas; ++i) {
    uint32_t meshIdx = i / nStaPerMesh;  // two STAs per mesh AP
    uint32_t staIdx = i % nStaPerMesh;

    auto [meshX, meshY] = getMeshPos(meshIdx);

    // Position STA nodes around mesh AP with small radius
    double angle = (staIdx * 2 * M_PI) / nStaPerMesh;
    double distance = 35.0;
    double x = meshX + distance * cos(angle);
    double y = meshY + distance * sin(angle);

    // Keep within bounds
    x = std::max(10.0, std::min(field - 10.0, x));
    y = std::max(10.0, std::min(field - 10.0, y));

    positionAlloc->Add(Vector(x, y, 1.5));
  }
  
  // Position Sayed and Sadia close to mesh APs for connectivity
  positionAlloc->Add(Vector(55.0, 55.0, 1.5));   // Sayed - very close to Mesh0 (50,50)
  positionAlloc->Add(Vector(345.0, 195.0, 1.5)); // Sadia - very close to Mesh3 (350,200)
  
  mobility.SetPositionAllocator(positionAlloc);
  
  // Set mobility models
  // Backhaul: static
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(backhaulNodes);
  
  // Mesh nodes: static (they form the backbone)
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(meshNodes);
  
  // STA nodes: mobile with RandomWalk2d (preserve original mobility)
  mobility.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
    "Bounds", RectangleValue(Rectangle(0, field, 0, field)),
    "Time", TimeValue(Seconds(1.0)),
    "Speed", StringValue("ns3::ConstantRandomVariable[Constant=50.0]"));  // Keep original speed
  mobility.Install(staNodes);
  
  // Sayed and Sadia: static at their corners (preserve original behavior)
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(sayedSadiaNodes);

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

  BuildingsHelper::Install(allNodes);
  
  // Write position grid after all mobility models are installed
  WriteAsciiPositionGrid(meshNodes, staNodes, backhaulNodes, sayedSadiaNodes, buildings, field);
  
  // Schedule building movements during simulation
  std::cout << "Scheduling building movements..." << std::endl;
  
  // Helper to adjust a building's desired position to avoid overlapping mesh AP nodes
  auto scheduleMoveAvoidingMesh = [&](double at, Ptr<Building> b, Vector desired, double w, double h) {
    Simulator::Schedule(Seconds(at), [&, b, desired, w, h]() mutable {
      // Build initial box
      Box bx(desired.x, desired.x + w, desired.y, desired.y + h, 0.0, 10.0);
      auto overlapsMesh = [&]() -> bool {
        for (uint32_t i = 0; i < meshNodes.GetN(); ++i) {
          Ptr<MobilityModel> mm = meshNodes.Get(i)->GetObject<MobilityModel>();
          if (!mm) continue;
          Vector p = mm->GetPosition();
          if (p.x >= bx.xMin && p.x <= bx.xMax && p.y >= bx.yMin && p.y <= bx.yMax) {
            return true;
          }
        }
        return false;
      };
      // Nudge the box to the right until it no longer overlaps mesh nodes, with bounds checking
      int guard = 0;
      while (overlapsMesh() && guard < 50) {
        desired.x = std::min(field - w - 1.0, desired.x + 20.0);
        bx.xMin = desired.x;
        bx.xMax = desired.x + w;
        guard++;
      }
      b->SetBoundaries(bx);
      std::cout << "Building moved (safe) to (" << desired.x << ", " << desired.y << ")" << std::endl;
    });
  };

  // Move cluster250a building - adjusted and made safe
  scheduleMoveAvoidingMesh(2.0, cluster250a, Vector(150.0, 180.0, 0.0), 60.0, 8.0);
  scheduleMoveAvoidingMesh(4.0, cluster250a, Vector(250.0, 130.0, 0.0), 60.0, 8.0);
  scheduleMoveAvoidingMesh(7.0, cluster250a, Vector(100.0, 280.0, 0.0), 60.0, 8.0);

  // Move cluster250b building - adjusted and made safe
  scheduleMoveAvoidingMesh(2.5, cluster250b, Vector(200.0, 180.0, 0.0), 80.0, 8.0);
  scheduleMoveAvoidingMesh(5.0, cluster250b, Vector(130.0, 300.0, 0.0), 80.0, 8.0);

  // Move cluster50 building - adjusted and made safe
  scheduleMoveAvoidingMesh(3.0, cluster50, Vector(255.0, 80.0, 0.0), 80.0, 8.0);
  scheduleMoveAvoidingMesh(6.0, cluster50, Vector(215.0, 180.0, 0.0), 80.0, 8.0);
  
  // Write position grid will be called after mobility models are installed

  // WiFi channel setup for mesh network
  YansWifiChannelHelper meshChannel;
  meshChannel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
  meshChannel.AddPropagationLoss("ns3::HybridBuildingsPropagationLossModel");
  meshChannel.AddPropagationLoss("ns3::RangePropagationLossModel", "MaxRange", DoubleValue(200.0));

  YansWifiPhyHelper meshPhy;
  meshPhy.SetChannel(meshChannel.Create());
  meshPhy.Set("TxPowerStart", DoubleValue(20.0));
  meshPhy.Set("TxPowerEnd", DoubleValue(20.0));
  meshPhy.Set("RxNoiseFigure", DoubleValue(7.0));

  // WiFi channel setup for STA connections
  YansWifiChannelHelper staChannel;
  staChannel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
  staChannel.AddPropagationLoss("ns3::HybridBuildingsPropagationLossModel");
  staChannel.AddPropagationLoss("ns3::RangePropagationLossModel", "MaxRange", DoubleValue(100.0));

  YansWifiPhyHelper staPhy;
  staPhy.SetChannel(staChannel.Create());
  staPhy.Set("TxPowerStart", DoubleValue(15.0));
  staPhy.Set("TxPowerEnd", DoubleValue(15.0));
  staPhy.Set("RxNoiseFigure", DoubleValue(7.0));
  
  std::system(("mkdir -p " + kOutDir).c_str());

  // Create simplified mesh network - all nodes in one mesh network
  MeshHelper mesh = MeshHelper::Default();
  mesh.SetStackInstaller("ns3::Dot11sStack");
  mesh.SetSpreadInterfaceChannels(MeshHelper::SPREAD_CHANNELS);
  mesh.SetMacType("RandomStart", TimeValue(Seconds(0.1)));
  mesh.SetNumberOfInterfaces(1);

  // Install mesh on all nodes (backhaul + mesh + STA + Sayed & Sadia)
  NetDeviceContainer meshDevices = mesh.Install(meshPhy, allNodes);

  // Create point-to-point backhaul connection (simulating wired internet)
  PointToPointHelper p2p;
  p2p.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
  p2p.SetChannelAttribute("Delay", StringValue("5ms"));

  NodeContainer internetNodes;
  internetNodes.Create(1);
  NetDeviceContainer internetDevices = p2p.Install(backhaulNodes.Get(0), internetNodes.Get(0));

  // Enable tracing
  meshPhy.EnablePcapAll(kOutDir + "/" + kPcapPrefix + "_mesh", true);
  p2p.EnablePcapAll(kOutDir + "/" + kPcapPrefix + "_backhaul", true);

  AsciiTraceHelper ascii;
  Ptr<OutputStreamWrapper> meshStream = ascii.CreateFileStream(kOutDir + "/" + kAsciiTracesPrefix + "_mesh.tr");
  meshPhy.EnableAsciiAll(meshStream);

  // Internet stack setup with OLSR routing
  OlsrHelper olsr;
  InternetStackHelper internet;
  internet.SetRoutingHelper(olsr);
  
  internet.Install(allNodes);
  internet.Install(internetNodes);

  // IP address assignment - Use single network for simplicity
  Ipv4AddressHelper ipv4;
  
  // Assign IPs to mesh network (all nodes)
  ipv4.SetBase("10.1.0.0", "255.255.0.0");
  Ipv4InterfaceContainer meshInterfaces = ipv4.Assign(meshDevices);
  
  // Assign IPs to backhaul connection
  ipv4.SetBase("172.16.0.0", "255.255.255.0");
  Ipv4InterfaceContainer internetInterfaces = ipv4.Assign(internetDevices);
  
  // Populate routing tables after all IP assignments
  Ipv4GlobalRoutingHelper::PopulateRoutingTables();
  
  // Print IP assignments for debugging
  std::cout << "IP Address Assignments:" << std::endl;
  std::cout << "  Backhaul: " << meshInterfaces.GetAddress(0) << std::endl;
  for (uint32_t i = 0; i < nMeshHops; ++i) {
    std::cout << "  Mesh" << i << ": " << meshInterfaces.GetAddress(1 + i) << std::endl;
  }
  for (uint32_t i = 0; i < nTotalStas; ++i) {
    std::cout << "  STA" << i << ": " << meshInterfaces.GetAddress(1 + nMeshHops + i) << std::endl;
  }
  std::cout << "  Sayed: " << meshInterfaces.GetAddress(1 + nMeshHops + nTotalStas) << std::endl;
  std::cout << "  Sadia: " << meshInterfaces.GetAddress(1 + nMeshHops + nTotalStas + 1) << std::endl;

  // Applications: PRESERVE SAYED-SADIA COMMUNICATION + Add new traffic patterns
  const uint16_t udpPort = 5000;
  const uint16_t sayedSadiaPort = 8000;  // Special port for Sayed-Sadia communication

  // SAYED-SADIA UDP COMMUNICATION (PRESERVE ORIGINAL PATTERN)
  UdpServerHelper sayedSadiaUdpServer(sayedSadiaPort);
  ApplicationContainer sayedSadiaUdpApp = sayedSadiaUdpServer.Install(sayedSadiaNodes.Get(1)); // Sadia as server
  sayedSadiaUdpApp.Start(Seconds(1.0));
  sayedSadiaUdpApp.Stop(Seconds(simTime));

  OnOffHelper sayedSadiaUdpClient("ns3::UdpSocketFactory",
                                 InetSocketAddress(meshInterfaces.GetAddress(allNodes.GetN()-1), sayedSadiaPort)); // Sadia's mesh IP (last node)
  sayedSadiaUdpClient.SetConstantRate(DataRate("2Mbps"), 1200);
  sayedSadiaUdpClient.SetAttribute("StartTime", TimeValue(Seconds(1.5)));  // Start earlier for better connectivity
  sayedSadiaUdpClient.SetAttribute("StopTime", TimeValue(Seconds(simTime)));
  ApplicationContainer sayedClientApp = sayedSadiaUdpClient.Install(sayedSadiaNodes.Get(0)); // Sayed as client

  // Internet server (simulating remote server)
  UdpServerHelper internetUdpServer(udpPort);
  ApplicationContainer internetUdpApp = internetUdpServer.Install(internetNodes.Get(0));
  internetUdpApp.Start(Seconds(1.0));
  internetUdpApp.Stop(Seconds(simTime));

  // STA clients connecting to internet through mesh network
  for (uint32_t i = 0; i < nTotalStas; ++i) {
    // UDP client to internet server
    OnOffHelper udpClient("ns3::UdpSocketFactory",
                         InetSocketAddress(internetInterfaces.GetAddress(1), udpPort));
    udpClient.SetConstantRate(DataRate("1Mbps"), 1200);
    udpClient.SetAttribute("StartTime", TimeValue(Seconds(2.0 + i * 0.2)));
    udpClient.SetAttribute("StopTime", TimeValue(Seconds(simTime)));
    udpClient.Install(staNodes.Get(i));
  }

  // FlowMonitor for KPIs
  FlowMonitorHelper fm;
  Ptr<FlowMonitor> monitor = fm.InstallAll();

  // NetAnim setup with detailed node labeling and coloring
  AnimationInterface anim(kOutDir + "/" + kNetAnimFile);
  anim.EnablePacketMetadata(true);
  anim.SetMaxPktsPerTraceFile(500000);

  // Color and label all nodes
  // Backhaul node (blue)
  anim.UpdateNodeDescription(backhaulNodes.Get(0), "Backhaul");
  anim.UpdateNodeColor(backhaulNodes.Get(0), 0, 0, 255);
  
  // Internet node (green)
  anim.UpdateNodeDescription(internetNodes.Get(0), "Internet");
  anim.UpdateNodeColor(internetNodes.Get(0), 0, 255, 0);
  
  // Mesh hop nodes (red)
  for (uint32_t i = 0; i < nMeshHops; ++i) {
    std::string name = "Mesh" + std::to_string(i);
    anim.UpdateNodeDescription(meshNodes.Get(i), name);
    anim.UpdateNodeColor(meshNodes.Get(i), 255, 0, 0);
  }
  
  // STA nodes (yellow)
  for (uint32_t i = 0; i < nTotalStas; ++i) {
    std::string name = "STA" + std::to_string(i);
    anim.UpdateNodeDescription(staNodes.Get(i), name);
    anim.UpdateNodeColor(staNodes.Get(i), 255, 255, 0);
  }
  
  // Sayed and Sadia (PRESERVE ORIGINAL COLORS)
  anim.UpdateNodeDescription(sayedSadiaNodes.Get(0), "Sayed");
  anim.UpdateNodeColor(sayedSadiaNodes.Get(0), 0, 150, 255);  // Original blue
  
  anim.UpdateNodeDescription(sayedSadiaNodes.Get(1), "Sadia");
  anim.UpdateNodeColor(sayedSadiaNodes.Get(1), 255, 120, 0);  // Original orange

  // IPv4 L3 ASCII tracing
  {
    AsciiTraceHelper ascii;
    Ptr<OutputStreamWrapper> ipStream = ascii.CreateFileStream(kOutDir + "/ipv4-l3.tr");
    internet.EnableAsciiIpv4All(ipStream);
  }

  std::cout << "Starting backhaul-connected mesh simulation with Sayed & Sadia..." << std::endl;
  std::cout << "Simulation time: " << simTime << " seconds" << std::endl;
  std::cout << "Output directory: " << kOutDir << std::endl;
  std::cout << "Preserving all original building movements and Sayed-Sadia communication!" << std::endl;

  Simulator::Stop(Seconds(simTime));
  Simulator::Run();
  
  monitor->SerializeToXmlFile(kOutDir + "/" + kFlowmonFile, true, true);
  Simulator::Destroy();
  
  std::cout << "Backhaul mesh simulation completed!" << std::endl;
  std::cout << "Results saved to: " << kOutDir << std::endl;
  return 0;
}
