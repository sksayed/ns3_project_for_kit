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
 * Author: NR Helper Functions
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

/**
 * @brief Create a basic NR network setup
 * @param gNbNum Number of gNBs
 * @param ueNumPergNb Number of UEs per gNB
 * @param centralFrequency Central frequency in Hz
 * @param bandwidth Bandwidth in Hz
 * @param numerology Numerology (0-4)
 * @return Tuple of (gNbNodes, ueNodes, gNbDevs, ueDevs, ueIpIface)
 */
std::tuple<NodeContainer, NodeContainer, NetDeviceContainer, NetDeviceContainer, Ipv4InterfaceContainer>
CreateBasicNrNetwork (uint16_t gNbNum, uint16_t ueNumPergNb, double centralFrequency, double bandwidth, uint16_t numerology)
{
  // Create nodes
  NodeContainer gNbNodes;
  NodeContainer ueNodes;
  gNbNodes.Create (gNbNum);
  ueNodes.Create (gNbNum * ueNumPergNb);

  // Create the NR helper
  Ptr<NrHelper> nrHelper = CreateObject<NrHelper> ();
  
  // Create EPC helper
  Ptr<NrPointToPointEpcHelper> epcHelper = CreateObject<NrPointToPointEpcHelper> ();
  nrHelper->SetEpcHelper (epcHelper);

  // Create and configure the spectrum
  BandwidthPartInfoPtrVector allBwps;
  CcBwpCreator ccBwpCreator;
  const uint8_t numCcPerBand = 1;

  CcBwpCreator::SimpleOperationBandConf bandConf (centralFrequency, bandwidth, numCcPerBand, BandwidthPartInfo::UMa_StreetCanyon);
  OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc (bandConf);

  // Initialize channel and pathloss
  nrHelper->InitializeOperationBand (&band);
  allBwps = CcBwpCreator::GetAllBwps ({band});

  // Configure antenna parameters
  nrHelper->SetGnbAntennaAttribute ("NumRows", UintegerValue (2));
  nrHelper->SetGnbAntennaAttribute ("NumColumns", UintegerValue (2));
  nrHelper->SetGnbAntennaAttribute ("AntennaElement", PointerValue (CreateObject<IsotropicAntennaModel> ()));

  nrHelper->SetUeAntennaAttribute ("NumRows", UintegerValue (1));
  nrHelper->SetUeAntennaAttribute ("NumColumns", UintegerValue (1));
  nrHelper->SetUeAntennaAttribute ("AntennaElement", PointerValue (CreateObject<IsotropicAntennaModel> ()));

  // Install NR devices
  NetDeviceContainer gNbDevs = nrHelper->InstallGnbDevice (gNbNodes, allBwps);
  NetDeviceContainer ueDevs = nrHelper->InstallUeDevice (ueNodes, allBwps);

  // Update device configurations
  for (auto it = gNbDevs.Begin (); it != gNbDevs.End (); ++it)
    {
      DynamicCast<NrGnbNetDevice> (*it)->UpdateConfig ();
    }

  for (auto it = ueDevs.Begin (); it != ueDevs.End (); ++it)
    {
      DynamicCast<NrUeNetDevice> (*it)->UpdateConfig ();
    }

  // Create the internet and install the IP stack on the UEs
  InternetStackHelper internet;
  internet.Install (ueNodes);
  Ipv4InterfaceContainer ueIpIface;
  ueIpIface = epcHelper->AssignUeIpv4Address (NetDeviceContainer (ueDevs));

  // Attach UEs to gNBs
  nrHelper->AttachToClosestEnb (ueDevs, gNbDevs);

  return std::make_tuple (gNbNodes, ueNodes, gNbDevs, ueDevs, ueIpIface);
}

/**
 * @brief Setup mobility for gNBs and UEs
 * @param gNbNodes gNB node container
 * @param ueNodes UE node container
 * @param gNbPositions Vector of gNB positions
 * @param uePositions Vector of UE positions
 */
void
SetupMobility (NodeContainer gNbNodes, NodeContainer ueNodes, 
               std::vector<Vector> gNbPositions, std::vector<Vector> uePositions)
{
  MobilityHelper mobility;
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobility.Install (gNbNodes);
  mobility.Install (ueNodes);

  // Set gNB positions
  for (uint32_t j = 0; j < gNbNodes.GetN () && j < gNbPositions.size (); ++j)
    {
      Ptr<MobilityModel> mm = gNbNodes.Get (j)->GetObject<MobilityModel> ();
      mm->SetPosition (gNbPositions[j]);
    }

  // Set UE positions
  for (uint32_t j = 0; j < ueNodes.GetN () && j < uePositions.size (); ++j)
    {
      Ptr<MobilityModel> mm = ueNodes.Get (j)->GetObject<MobilityModel> ();
      mm->SetPosition (uePositions[j]);
    }
}

/**
 * @brief Install UDP applications for data transfer
 * @param gNbNodes gNB node container
 * @param ueNodes UE node container
 * @param ueIpIface UE IP interface container
 * @param startTime Application start time
 * @param stopTime Application stop time
 * @param packetSize Packet size in bytes
 * @param interval Packet interval
 * @return Tuple of (clientApps, serverApps)
 */
std::tuple<ApplicationContainer, ApplicationContainer>
InstallUdpApplications (NodeContainer gNbNodes, NodeContainer ueNodes, 
                       Ipv4InterfaceContainer ueIpIface,
                       Time startTime, Time stopTime,
                       uint32_t packetSize, Time interval)
{
  uint16_t dlPort = 1234;
  ApplicationContainer clientApps;
  ApplicationContainer serverApps;

  for (uint32_t j = 0; j < ueNodes.GetN (); ++j)
    {
      // DL traffic - gNB sends to UE
      PacketSinkHelper dlPacketSinkHelper ("ns3::UdpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), dlPort));
      serverApps.Add (dlPacketSinkHelper.Install (ueNodes.Get (j)));

      UdpClientHelper dlClient (ueIpIface.GetAddress (j), dlPort);
      dlClient.SetAttribute ("Interval", TimeValue (interval));
      dlClient.SetAttribute ("MaxPackets", UintegerValue (1000000));
      dlClient.SetAttribute ("PacketSize", UintegerValue (packetSize));
      clientApps.Add (dlClient.Install (gNbNodes.Get (0)));

      dlPort++;
    }

  serverApps.Start (startTime);
  clientApps.Start (startTime + MilliSeconds (100));
  serverApps.Stop (stopTime);
  clientApps.Stop (stopTime);

  return std::make_tuple (clientApps, serverApps);
}

/**
 * @brief Print flow statistics
 * @param flowMonitor Flow monitor pointer
 * @param flowHelper Flow monitor helper
 */
void
PrintFlowStatistics (Ptr<FlowMonitor> flowMonitor, FlowMonitorHelper flowHelper)
{
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
}
