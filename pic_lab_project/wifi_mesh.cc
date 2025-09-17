#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/mesh-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/trace-helper.h"
#include "ns3/wifi-helper.h"
#include "ns3/yans-wifi-helper.h"
#include <fstream>
#include <iostream>

using namespace ns3;

int main(int argc, char **argv) {
  std::cout << "Hello " << std::endl;
  LogComponentEnable("UdpEchoClientApplication", LOG_LEVEL_INFO);
  LogComponentEnable("UdpEchoServerApplication", LOG_LEVEL_INFO);
  // Enable packet metadata early so NetAnim can visualize packets
  PacketMetadata::Enable();
  Packet::EnablePrinting();

  uint32_t number_of_nodes = 6;

  // at first we need to create nodes to simulate the wifi network
  // create three nodes
  NodeContainer nodes;
  nodes.Create(number_of_nodes);

  NodeContainer specialClientNode;
  specialClientNode.Create(1);

  // Combine all nodes for later installations (mesh, internet, etc.)
  NodeContainer allNodes;
  allNodes.Add(nodes);
  allNodes.Add(specialClientNode);

  // now i have nodes
  MobilityHelper mobilityHelper;
  // nodes will be in constant position and they will be in a line topology
  mobilityHelper.SetMobilityModel(
      "ns3::GaussMarkovMobilityModel", "Bounds",
      BoxValue(Box(0, 40, 0, 40, 0, 0)), "TimeStep", TimeValue(Seconds(0.5)),
      "Alpha", DoubleValue(0.85), // memory (0=random, 1=steady)
      "MeanVelocity", StringValue("ns3::ConstantRandomVariable[Constant=20.0]"),
      "MeanDirection", StringValue("ns3::ConstantRandomVariable[Constant=0.0]"),
      "MeanPitch", StringValue("ns3::ConstantRandomVariable[Constant=0.0]"),
      "NormalVelocity",
      StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0.5]"),
      "NormalDirection",
      StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0.5]"),
      "NormalPitch",
      StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0.0]"));
  /**
   * mobility model defines how the nodes will move
   * constant position mobility model means the nodes will be in a constant
   * position ConstantVelocityMobilityModel means the nodes will be in a
   * constant velocity ConstantAccelerationMobilityModel means the nodes will be
   * in a constant acceleration GaussMarkovMobilityModel means the nodes will be
   * in a gauss markov model HierarchicalMobilityModel means the nodes will be
   * in a hierarchical model RandomDirection2dMobilityModel means the nodes will
   * be in a random direction 2d model RandomWalk2dMobilityModel means the nodes
   * will be in a random walk 2d model RandomWaypointMobilityModel means the
   * nodes will be in a random waypoint model
   */

  mobilityHelper.SetPositionAllocator(
      "ns3::GridPositionAllocator", "MinX", ns3::DoubleValue(0.0), "MinY",
      ns3::DoubleValue(0.0), "DeltaX", ns3::DoubleValue(10.0), "DeltaY",
      ns3::DoubleValue(10.0), "GridWidth", ns3::UintegerValue(3), "LayoutType",
      ns3::StringValue("RowFirst"));
  /**
   * apart from that there are few more
   * like random box position allocator (3D) and random rectangle position
   * allocator (2D) random disc position allocator and random uniform disc
   * position allocator (Circle) random building position allocator and random
   * outdoor position allocator (Building)
   */

  mobilityHelper.Install(nodes);

  // Install a RandomDirection2dMobilityModel on the special node at corner
  MobilityHelper specialMob;
  Ptr<ListPositionAllocator> specialPos = CreateObject<ListPositionAllocator>();
  specialPos->Add(Vector(40.0, 40.0, 0.0));
  specialMob.SetPositionAllocator(specialPos);
  specialMob.SetMobilityModel(
      "ns3::RandomDirection2dMobilityModel", "Bounds",
      RectangleValue(Rectangle(0.0, 40.0, 0.0, 40.0)), "Speed",
      StringValue("ns3::ConstantRandomVariable[Constant=20.0]"), "Pause",
      StringValue("ns3::ConstantRandomVariable[Constant=0.0]"));
  specialMob.Install(specialClientNode);
  // (height clamping removed)

  // Wi-Fi PHY/Channel
  YansWifiChannelHelper channel;
  channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
  channel.AddPropagationLoss("ns3::LogDistancePropagationLossModel");

  YansWifiPhyHelper yans;
  yans.SetChannel(channel.Create());
  yans.EnablePcapAll("wifi_mesh_example", true);

  // 802.11s Mesh
  MeshHelper mesh = MeshHelper::Default();
  mesh.SetStackInstaller("ns3::Dot11sStack");
  mesh.SetSpreadInterfaceChannels(MeshHelper::SPREAD_CHANNELS);
  mesh.SetMacType("RandomStart", TimeValue(Seconds(0.1)));
  NetDeviceContainer meshDevs = mesh.Install(yans, allNodes);

  // Internet stack + IPs
  InternetStackHelper internet;
  internet.Install(allNodes);
  Ipv4AddressHelper ip;
  ip.SetBase("10.0.0.0", "255.255.255.0");
  Ipv4InterfaceContainer ifaces = ip.Assign(meshDevs);
  // Address index of the special node is the last one in allNodes
  uint32_t specialIndex = allNodes.GetN() - 1;

  // Simple connectivity test: UDP Echo (node 0 -> last node)
  uint16_t port = 950;
  UdpEchoServerHelper server(port);
  ApplicationContainer sobujApps = server.Install(specialClientNode.Get(0));
  sobujApps.Start(Seconds(1.0));
  sobujApps.Stop(Seconds(9.0));

  // Also run echo servers on node 3 and node 4
  ApplicationContainer serverNode3 = server.Install(nodes.Get(3));
  serverNode3.Start(Seconds(1.0));
  serverNode3.Stop(Seconds(9.0));
  ApplicationContainer serverNode4 = server.Install(nodes.Get(4));
  serverNode4.Start(Seconds(1.0));
  serverNode4.Stop(Seconds(9.0));

  UdpEchoClientHelper client(ifaces.GetAddress(specialIndex), port);
  client.SetAttribute("MaxPackets", UintegerValue(10));
  client.SetAttribute("Interval", TimeValue(Seconds(1.0)));
  client.SetAttribute("PacketSize", UintegerValue(64));
  ApplicationContainer sayedApps = client.Install(nodes.Get(0));
  sayedApps.Start(Seconds(2.0));
  sayedApps.Stop(Seconds(9.0));

  // Additional clients from Sayed to node 3 and node 4
  UdpEchoClientHelper clientTo3(ifaces.GetAddress(3), port);
  clientTo3.SetAttribute("MaxPackets", UintegerValue(10));
  clientTo3.SetAttribute("Interval", TimeValue(Seconds(1.0)));
  clientTo3.SetAttribute("PacketSize", UintegerValue(64));
  ApplicationContainer sayedTo3 = clientTo3.Install(nodes.Get(0));
  sayedTo3.Start(Seconds(2.0));
  sayedTo3.Stop(Seconds(9.0));

  UdpEchoClientHelper clientTo4(ifaces.GetAddress(4), port);
  clientTo4.SetAttribute("MaxPackets", UintegerValue(10));
  clientTo4.SetAttribute("Interval", TimeValue(Seconds(1.0)));
  clientTo4.SetAttribute("PacketSize", UintegerValue(64));
  ApplicationContainer sayedTo4 = clientTo4.Install(nodes.Get(0));
  sayedTo4.Start(Seconds(2.0));
  sayedTo4.Stop(Seconds(9.0));

  AsciiTraceHelper ascii;
  MobilityHelper::EnableAsciiAll(ascii.CreateFileStream("wifi_mesh_example.tr"));

  // Enable NetAnim output
  AnimationInterface anim("netanim-wifi-mesh.xml");
  anim.EnablePacketMetadata(true); // show packet flows
  anim.UpdateNodeDescription(nodes.Get(0), "Sayed");
  anim.UpdateNodeDescription(specialClientNode.Get(0), "Biplop");
  anim.UpdateNodeColor(nodes.Get(0), 0, 150, 255); // blue
  anim.UpdateNodeColor(specialClientNode.Get(0), 255, 120, 0);

  Simulator::Stop(Seconds(10));
  Simulator::Run();
  Simulator::Destroy();

  return 0;
}