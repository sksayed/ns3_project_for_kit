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
  NodeContainer nodes;
  nodes.Create(number_of_nodes);

  NodeContainer specialClientNode; // Biplob
  specialClientNode.Create(1);

  // Combine all nodes for later installations (mesh, internet, etc.)
  NodeContainer allNodes;
  allNodes.Add(nodes);
  allNodes.Add(specialClientNode);

  // --- Mobility: place nodes as a linear chain to force multi-hop ---
  // Use ConstantPosition and positions spaced near the radio range
  MobilityHelper mobilityHelper;
  mobilityHelper.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  Ptr<ListPositionAllocator> chainPos = CreateObject<ListPositionAllocator>();
  // Chain spacing ~18 m; with MaxRange=20 m below, nodes only see neighbors
  chainPos->Add(Vector(0.0, 0.0, 0.0));  // node 0 (Sayed)
  chainPos->Add(Vector(18.0, 0.0, 0.0)); // node 1
  chainPos->Add(Vector(36.0, 0.0, 0.0)); // node 2
  chainPos->Add(Vector(54.0, 0.0, 0.0)); // node 3
  chainPos->Add(Vector(72.0, 0.0, 0.0)); // node 4
  chainPos->Add(Vector(90.0, 0.0, 0.0)); // node 5
  mobilityHelper.SetPositionAllocator(chainPos);
  mobilityHelper.Install(nodes);

  // Biplob fixed at the end of the chain to require multiple hops
  MobilityHelper specialMob;
  Ptr<ListPositionAllocator> specialPos = CreateObject<ListPositionAllocator>();
  specialPos->Add(Vector(108.0, 0.0, 0.0)); // ~6 hops away from node 0
  specialMob.SetPositionAllocator(specialPos);
  specialMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  specialMob.Install(specialClientNode);

  // Wi-Fi PHY/Channel
  YansWifiChannelHelper channel;
  channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
  // Add a hard range cap so nodes only reach direct neighbors
  channel.AddPropagationLoss("ns3::RangePropagationLossModel", "MaxRange",
                             DoubleValue(18.0));

  YansWifiPhyHelper yans;
  yans.SetChannel(channel.Create());
  yans.EnablePcapAll("wifi_mesh_multi_hop", true);

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

  // UDP Echo: node 0 (Sayed) -> Biplob (multi-hop via mesh)
  uint16_t port = 950;
  UdpEchoServerHelper server(port);
  ApplicationContainer biplobServer = server.Install(specialClientNode.Get(0));
  biplobServer.Start(Seconds(1.0));
  biplobServer.Stop(Seconds(19.0));

  UdpEchoClientHelper client(ifaces.GetAddress(specialIndex), port);
  client.SetAttribute("MaxPackets", UintegerValue(30));
  client.SetAttribute("Interval", TimeValue(Seconds(0.5)));
  client.SetAttribute("PacketSize", UintegerValue(1024));
  ApplicationContainer sayedApps = client.Install(nodes.Get(0));
  sayedApps.Start(Seconds(2.0));
  sayedApps.Stop(Seconds(10.0));

  // ASCII mobility trace (optional)
  AsciiTraceHelper ascii;
  MobilityHelper::EnableAsciiAll(
      ascii.CreateFileStream("wifi_mesh_multi_hop.tr"));

  // Enable NetAnim output
  AnimationInterface anim("netanim-wifi-mesh-multi-hop.xml");
  anim.EnablePacketMetadata(true); // show packet flows

  // Label nodes for clarity
  anim.UpdateNodeDescription(nodes.Get(0), "Sayed(0)");
  anim.UpdateNodeColor(nodes.Get(0), 0, 150, 255); // blue
  for (uint32_t i = 1; i < nodes.GetN(); ++i) {
    std::ostringstream oss;
    oss << "Node " << i;
    anim.UpdateNodeDescription(nodes.Get(i), oss.str());
    anim.UpdateNodeColor(nodes.Get(i), 180, 180, 180);
  }
  anim.UpdateNodeDescription(specialClientNode.Get(0), "Biplob");
  anim.UpdateNodeColor(specialClientNode.Get(0), 255, 120, 0);
  // Set a custom image by resource index (NetAnim expects a uint32_t resource id)
  anim.UpdateNodeImage(specialClientNode.Get(0)->GetId(), 0);

  Simulator::Stop(Seconds(20));
  Simulator::Run();
  Simulator::Destroy();

  return 0;
}