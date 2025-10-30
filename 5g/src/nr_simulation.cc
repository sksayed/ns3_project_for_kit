/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2024
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Simple NR Simulation
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/applications-module.h"
#include "ns3/mobility-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/nr-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("SimpleNrSimulation");

int
main (int argc, char *argv[])
{
  // Simulation parameters
  double simTime = 1.0; // seconds
  uint16_t numerology = 0;
  double centralFrequency = 2.1e9; // 2.1 GHz
  double bandwidth = 100e6; // 100 MHz
  double txPower = 23; // dBm
  uint16_t gNbNum = 1;
  uint16_t ueNumPergNb = 2;
  bool enableLogging = false;

  // Command line arguments
  CommandLine cmd (__FILE__);
  cmd.AddValue ("simTime", "Simulation time in seconds", simTime);
  cmd.AddValue ("numerology", "Numerology (0-4)", numerology);
  cmd.AddValue ("centralFrequency", "Central frequency in Hz", centralFrequency);
  cmd.AddValue ("bandwidth", "Bandwidth in Hz", bandwidth);
  cmd.AddValue ("txPower", "TX power in dBm", txPower);
  cmd.AddValue ("gNbNum", "Number of gNBs", gNbNum);
  cmd.AddValue ("ueNumPergNb", "Number of UEs per gNB", ueNumPergNb);
  cmd.AddValue ("enableLogging", "Enable logging", enableLogging);
  cmd.Parse (argc, argv);

  if (enableLogging)
    {
      LogComponentEnable ("SimpleNrSimulation", LOG_LEVEL_INFO);
      LogComponentEnable ("NrHelper", LOG_LEVEL_INFO);
      LogComponentEnable ("NrGnbNetDevice", LOG_LEVEL_INFO);
      LogComponentEnable ("NrUeNetDevice", LOG_LEVEL_INFO);
    }

  // Create the simulation
  RngSeedManager::SetSeed (1);
  RngSeedManager::SetRun (1);

  // Create gNB and UE nodes
  NodeContainer gNbNodes;
  NodeContainer ueNodes;
  gNbNodes.Create (gNbNum);
  ueNodes.Create (gNbNum * ueNumPergNb);

  // Create the NR helper
  Ptr<NrHelper> nrHelper = CreateObject<NrHelper> ();
  
  // Create EPC helper
  Ptr<NrPointToPointEpcHelper> epcHelper = CreateObject<NrPointToPointEpcHelper> ();
  nrHelper->SetEpcHelper (epcHelper);

  // Create beamforming helper
  Ptr<IdealBeamformingHelper> idealBeamformingHelper = CreateObject<IdealBeamformingHelper> ();
  nrHelper->SetBeamformingHelper (idealBeamformingHelper);

  // Create and configure the spectrum
  BandwidthPartInfoPtrVector allBwps;
  CcBwpCreator ccBwpCreator;
  const uint8_t numCcPerBand = 1;

  CcBwpCreator::SimpleOperationBandConf bandConf (centralFrequency, bandwidth, numCcPerBand);
  OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc (bandConf);

  // Create channel helper
  Ptr<NrChannelHelper> channelHelper = CreateObject<NrChannelHelper> ();
  channelHelper->ConfigureFactories ("UMi", "Default", "ThreeGpp");
  channelHelper->SetChannelConditionModelAttribute ("UpdatePeriod", TimeValue (MilliSeconds (0)));
  channelHelper->SetPathlossAttribute ("ShadowingEnabled", BooleanValue (false));
  channelHelper->AssignChannelsToBands ({band});
  allBwps = CcBwpCreator::GetAllBwps ({band});

  // Install mobility model first
  MobilityHelper mobility;
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobility.Install (gNbNodes);
  mobility.Install (ueNodes);

  // Set positions
  for (uint32_t j = 0; j < gNbNodes.GetN (); ++j)
    {
      Ptr<MobilityModel> mm = gNbNodes.Get (j)->GetObject<MobilityModel> ();
      mm->SetPosition (Vector (0.0, 0.0, 10.0));
    }

  for (uint32_t j = 0; j < ueNodes.GetN (); ++j)
    {
      Ptr<MobilityModel> mm = ueNodes.Get (j)->GetObject<MobilityModel> ();
      mm->SetPosition (Vector (10.0, 0.0, 1.5));
    }

  // Configure antenna parameters
  nrHelper->SetGnbAntennaAttribute ("NumRows", UintegerValue (2));
  nrHelper->SetGnbAntennaAttribute ("NumColumns", UintegerValue (2));

  nrHelper->SetUeAntennaAttribute ("NumRows", UintegerValue (1));
  nrHelper->SetUeAntennaAttribute ("NumColumns", UintegerValue (1));

  // Install NR devices
  NetDeviceContainer gNbDevs = nrHelper->InstallGnbDevice (gNbNodes, allBwps);
  NetDeviceContainer ueDevs = nrHelper->InstallUeDevice (ueNodes, allBwps);

  // Create the internet and install the IP stack on the UEs
  InternetStackHelper internet;
  internet.Install (ueNodes);
  Ipv4InterfaceContainer ueIpIface;
  ueIpIface = epcHelper->AssignUeIpv4Address (NetDeviceContainer (ueDevs));

  // Attach UEs to gNBs
  nrHelper->AttachToClosestGnb (ueDevs, gNbDevs);

  // Install applications
  uint16_t dlPort = 1234;
  ApplicationContainer clientApps;
  ApplicationContainer serverApps;

  for (uint32_t j = 0; j < ueNodes.GetN (); ++j)
    {
      // DL traffic
      PacketSinkHelper dlPacketSinkHelper ("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), dlPort));
      serverApps.Add (dlPacketSinkHelper.Install (ueNodes.Get (j)));

      UdpClientHelper dlClient (ueIpIface.GetAddress (j), dlPort);
      dlClient.SetAttribute ("Interval", TimeValue (MicroSeconds (100)));
      dlClient.SetAttribute ("MaxPackets", UintegerValue (1000000));
      dlClient.SetAttribute ("PacketSize", UintegerValue (1000));
      clientApps.Add (dlClient.Install (gNbNodes.Get (0)));

      dlPort++;
    }

  serverApps.Start (Seconds (0.1));
  clientApps.Start (Seconds (0.2));
  serverApps.Stop (Seconds (simTime));
  clientApps.Stop (Seconds (simTime));

  // Enable traces
  nrHelper->EnableTraces ();

  // Flow monitor
  Ptr<FlowMonitor> flowMonitor;
  FlowMonitorHelper flowHelper;
  flowMonitor = flowHelper.InstallAll ();

  // Run simulation
  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();

  // Print statistics
  flowMonitor->CheckForLostPackets ();
  Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier> (flowHelper.GetClassifier ());
  FlowMonitor::FlowStatsContainer stats = flowMonitor->GetFlowStats ();

  double totalThroughput = 0.0;
  double totalDelay = 0.0;
  uint32_t totalPackets = 0;
  uint32_t flowCount = 0;

  for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin (); i != stats.end (); ++i)
    {
      Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow (i->first);
      std::cout << "Flow " << i->first << " (" << t.sourceAddress << " -> " << t.destinationAddress << ")\n";
      std::cout << "  Tx Packets: " << i->second.txPackets << "\n";
      std::cout << "  Tx Bytes:   " << i->second.txBytes << "\n";
      std::cout << "  Rx Packets: " << i->second.rxPackets << "\n";
      std::cout << "  Rx Bytes:   " << i->second.rxBytes << "\n";
      
      if (i->second.rxPackets > 0)
        {
          double throughput = i->second.rxBytes * 8.0 / (i->second.timeLastRxPacket.GetSeconds () - i->second.timeFirstTxPacket.GetSeconds ()) / 1e6;
          double delay = i->second.delaySum.GetSeconds () / i->second.rxPackets * 1000;
          std::cout << "  Throughput: " << throughput << " Mbps\n";
          std::cout << "  Mean delay: " << delay << " ms\n";
          totalThroughput += throughput;
          totalDelay += delay;
          totalPackets += i->second.rxPackets;
          flowCount++;
        }
      std::cout << "\n";
    }

  if (flowCount > 0)
    {
      std::cout << "=== Summary ===\n";
      std::cout << "Total flows: " << flowCount << "\n";
      std::cout << "Total throughput: " << totalThroughput << " Mbps\n";
      std::cout << "Average delay: " << totalDelay / flowCount << " ms\n";
      std::cout << "Total packets received: " << totalPackets << "\n";
    }

  Simulator::Destroy ();
  return 0;
}
