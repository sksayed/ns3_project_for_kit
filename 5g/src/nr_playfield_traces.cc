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
 * Author: 5G NR Playfield Simulation with Traces
 */

#include "ns3/applications-module.h"
#include "ns3/buildings-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/nr-helper.h"
#include "ns3/nr-module.h"
#include "ns3/nr-point-to-point-epc-helper.h"
#include "ns3/point-to-point-module.h"
#include "ns3/ideal-beamforming-algorithm.h"
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>

using namespace ns3;

static const std::string kOutDir = "5g_outputs";

// RRC trace callbacks for better runtime visibility
static void
NotifyConnectionEstablishedUe(std::string context,
                              uint64_t imsi,
                              uint16_t cellid,
                              uint16_t rnti)
{
    std::cout << Simulator::Now().GetSeconds() << " " << context << " UE IMSI " << imsi
              << ": connected to CellId " << cellid << " with RNTI " << rnti << std::endl;
}

static void
NotifyHandoverStartUe(std::string context,
                      uint64_t imsi,
                      uint16_t cellid,
                      uint16_t rnti,
                      uint16_t targetCellId)
{
    std::cout << Simulator::Now().GetSeconds() << " " << context << " UE IMSI " << imsi
              << ": previously connected to CellId " << cellid << " with RNTI " << rnti
              << ", doing handover to CellId " << targetCellId << std::endl;
}

static void
NotifyHandoverEndOkUe(std::string context, uint64_t imsi, uint16_t cellid, uint16_t rnti)
{
    std::cout << Simulator::Now().GetSeconds() << " " << context << " UE IMSI " << imsi
              << ": successful handover to CellId " << cellid << " with RNTI " << rnti << std::endl;
}

static void
NotifyConnectionEstablishedEnb(std::string context, uint64_t imsi, uint16_t cellid, uint16_t rnti)
{
    std::cout << Simulator::Now().GetSeconds() << " " << context << " gNB CellId " << cellid
              << ": successful connection of UE with IMSI " << imsi << " RNTI " << rnti << std::endl;
}

static void
NotifyHandoverStartEnb(std::string context,
                       uint64_t imsi,
                       uint16_t cellid,
                       uint16_t rnti,
                       uint16_t targetCellId)
{
    std::cout << Simulator::Now().GetSeconds() << " " << context << " gNB CellId " << cellid
              << ": start handover of UE with IMSI " << imsi << " RNTI " << rnti << " to CellId "
              << targetCellId << std::endl;
}

static void
NotifyHandoverEndOkEnb(std::string context, uint64_t imsi, uint16_t cellid, uint16_t rnti)
{
    std::cout << Simulator::Now().GetSeconds() << " " << context << " gNB CellId " << cellid
              << ": completed handover of UE with IMSI " << imsi << " RNTI " << rnti << std::endl;
}

// Function to update building position dynamically
void
UpdateBuildingPosition(Ptr<Building> building, Vector newPosition, double width, double height)
{
    Box newBounds(newPosition.x,
                  newPosition.x + width,
                  newPosition.y,
                  newPosition.y + height,
                  0.0,
                  10.0);
    building->SetBoundaries(newBounds);
    std::cout << "Building moved to (" << newPosition.x << ", " << newPosition.y << ")"
              << std::endl;
}

// Output file name constants for easy configuration
static const std::string kPcapPrefix = "nr_playfield_rw_pcap";
static const std::string kAsciiTracesPrefix = "nr_playfield_ascii_traces";
static const std::string kNetAnimFile = "netanim-nr-playfield-rw.xml";
static const std::string kFlowmonFile = "flowmon-nr-playfield-rw.xml";

int
main(int argc, char** argv)
{
    // Basics
    PacketMetadata::Enable();
    Packet::EnablePrinting();

    // Logging
    // LogComponentEnable("OnOffApplication", LOG_LEVEL_DEBUG);
    // LogComponentEnable("PacketSink", LOG_LEVEL_DEBUG);
    // LogComponentEnable("BulkSendApplication", LOG_LEVEL_DEBUG);
    // LogComponentEnable("TcpSocketBase", LOG_LEVEL_DEBUG);
    LogComponentEnable("UdpServer", LOG_LEVEL_INFO);

    const uint32_t nUes = 10; // nodes 0..9; 0 and 9 are endpoints
    const double field = 400.0;
    const double simStop = 10.0;

    // Create UE nodes and three gNB nodes
    NodeContainer ueNodes;
    ueNodes.Create(nUes);
    NodeContainer gnbNodes;
    gnbNodes.Create(3);

    // Mobility: replicate layout for UEs
    MobilityHelper fixedMob;
    MobilityHelper midMob;
    Ptr<ListPositionAllocator> fixedPos = CreateObject<ListPositionAllocator>();
    fixedPos->Add(Vector(0.0, 0.0, 1.5));     // UE 0: Sayed
    fixedPos->Add(Vector(field, field, 1.5)); // UE 9: Sadia
    fixedMob.SetPositionAllocator(fixedPos);
    fixedMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    fixedMob.Install(ueNodes.Get(0));
    fixedMob.Install(ueNodes.Get(nUes - 1));

    Ptr<ListPositionAllocator> midPos = CreateObject<ListPositionAllocator>();
    for (uint32_t i = 1; i < nUes - 1; ++i)
    {
        double frac = static_cast<double>(i) / static_cast<double>(nUes - 1);
        double x = frac * field;
        double y = frac * field;
        midPos->Add(Vector(x, y, 1.5));
    }
    midMob.SetPositionAllocator(midPos);
    midMob.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
                            "Bounds",
                            RectangleValue(Rectangle(0, 400, 0, 400)),
                            "Time",
                            TimeValue(Seconds(0.5)),
                            "Speed",
                            StringValue("ns3::ConstantRandomVariable[Constant=5.0]"));
    NodeContainer mids;
    for (uint32_t i = 1; i < nUes - 1; ++i)
    {
        mids.Add(ueNodes.Get(i));
    }
    midMob.Install(mids);

    // gNB positions (3 gNBs for better coverage)
    MobilityHelper gnbMob;
    Ptr<ListPositionAllocator> gnbPos = CreateObject<ListPositionAllocator>();
    gnbPos->Add(Vector(field * 0.25, field * 0.5, 15.0)); // gNB0 at (100, 200, 15)
    gnbPos->Add(Vector(100.0, 50.0, 15.0));               // gNB1 at (100, 50, 15)
    gnbPos->Add(Vector(300.0, 300.0, 15.0));              // gNB2 near UE9 to improve path
    gnbMob.SetPositionAllocator(gnbPos);
    gnbMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    gnbMob.Install(gnbNodes);

    // Report gNB positions and pairwise distances
    {
        std::cout << "gNB positions:" << std::endl;
        std::vector<Vector> gnbPositions;
        gnbPositions.reserve(gnbNodes.GetN());
        for (uint32_t e = 0; e < gnbNodes.GetN(); ++e)
        {
            Ptr<MobilityModel> mm = gnbNodes.Get(e)->GetObject<MobilityModel>();
            Vector p = mm->GetPosition();
            gnbPositions.push_back(p);
            std::cout << "  gNB" << e << ": (" << p.x << ", " << p.y << ", " << p.z << ")"
                      << std::endl;
        }
        std::cout << std::fixed << std::setprecision(2);
        std::cout << "gNB pairwise distances (m):" << std::endl;
        for (uint32_t i = 0; i < gnbPositions.size(); ++i)
        {
            for (uint32_t j = i + 1; j < gnbPositions.size(); ++j)
            {
                double dx = gnbPositions[i].x - gnbPositions[j].x;
                double dy = gnbPositions[i].y - gnbPositions[j].y;
                double dz = gnbPositions[i].z - gnbPositions[j].z;
                double d = std::sqrt(dx * dx + dy * dy + dz * dz);
                std::cout << "  gNB" << i << "-gNB" << j << ": " << d << std::endl;
            }
        }
    }

    // Buildings / obstacles (same as LTE/Wi-Fi scenario)
    Ptr<Building> leftBelow = CreateObject<Building>();
    leftBelow->SetBoundaries(Box(0.0, 60.0, 96.0, 104.0, 0.0, 10.0));
    Ptr<Building> rightBelow = CreateObject<Building>();
    rightBelow->SetBoundaries(Box(340.0, 400.0, 96.0, 104.0, 0.0, 10.0));
    Ptr<Building> leftAbove = CreateObject<Building>();
    leftAbove->SetBoundaries(Box(0.0, 60.0, 296.0, 304.0, 0.0, 10.0));
    Ptr<Building> rightAbove = CreateObject<Building>();
    rightAbove->SetBoundaries(Box(340.0, 400.0, 296.0, 304.0, 0.0, 10.0));
    Ptr<Building> cluster250a = CreateObject<Building>();
    cluster250a->SetBoundaries(Box(80.0, 140.0, 220.0, 228.0, 0.0, 15.0)); // Moved left, higher
    Ptr<Building> cluster250b = CreateObject<Building>();
    cluster250b->SetBoundaries(
        Box(170.0, 250.0, 220.0, 228.0, 0.0, 12.0)); // Moved left, different height
    Ptr<Building> cluster50 = CreateObject<Building>();
    cluster50->SetBoundaries(
        Box(255.0, 335.0, 20.0, 28.0, 0.0, 18.0)); // Moved 15m more left, tallest building
    BuildingContainer buildings;
    buildings.Add(leftBelow);
    buildings.Add(rightBelow);
    buildings.Add(leftAbove);
    buildings.Add(rightAbove);
    buildings.Add(cluster250a);
    buildings.Add(cluster250b);
    buildings.Add(cluster50);

    // NOTE: Dynamic building movements commented out for initial testing
    // Building movements can be enabled after successful static simulation
    std::cout << "Static buildings configured (dynamic movements disabled for now)..." << std::endl;

    // // Move cluster250a building at different times (moved left, higher)
    // Simulator::Schedule(Seconds(5.0),
    //                     &UpdateBuildingPosition,
    //                     cluster250a,
    //                     Vector(150.0, 180.0, 0.0),
    //                     60.0,
    //                     8.0);
    // Simulator::Schedule(Seconds(8.0),
    //                     &UpdateBuildingPosition,
    //                     cluster250a,
    //                     Vector(250.0, 130.0, 0.0),
    //                     60.0,
    //                     8.0);
    // Simulator::Schedule(Seconds(12.0),
    //                     &UpdateBuildingPosition,
    //                     cluster250a,
    //                     Vector(100.0, 280.0, 0.0),
    //                     60.0,
    //                     8.0);

    // // Move cluster250b building (moved left)
    // Simulator::Schedule(Seconds(6.0),
    //                     &UpdateBuildingPosition,
    //                     cluster250b,
    //                     Vector(200.0, 180.0, 0.0),
    //                     80.0,
    //                     8.0);
    // Simulator::Schedule(Seconds(10.0),
    //                     &UpdateBuildingPosition,
    //                     cluster250b,
    //                     Vector(130.0, 300.0, 0.0),
    //                     80.0,
    //                     8.0);

    // // Move cluster50 building (moved 15m more left)
    // Simulator::Schedule(Seconds(7.0),
    //                     &UpdateBuildingPosition,
    //                     cluster50,
    //                     Vector(255.0, 80.0, 0.0),
    //                     80.0,
    //                     8.0);
    // Simulator::Schedule(Seconds(11.0),
    //                     &UpdateBuildingPosition,
    //                     cluster50,
    //                     Vector(215.0, 180.0, 0.0),
    //                     80.0,
    //                     8.0);

    // 5G NR configuration
    // Create NR helper
    Ptr<NrHelper> nrHelper = CreateObject<NrHelper>();

    // Create EPC helper
    Ptr<NrPointToPointEpcHelper> epcHelper = CreateObject<NrPointToPointEpcHelper>();
    nrHelper->SetEpcHelper(epcHelper);

    // Create beamforming helper
    Ptr<IdealBeamformingHelper> idealBeamformingHelper = CreateObject<IdealBeamformingHelper>();
    nrHelper->SetBeamformingHelper(idealBeamformingHelper);

    // Configure spectrum
    double centralFrequency = 3.5e9; // 3.5 GHz (5G mid-band)
    double bandwidth = 100e6;        // 100 MHz
    uint16_t numerology = 1;         // SCS = 30 kHz

    BandwidthPartInfoPtrVector allBwps;
    CcBwpCreator ccBwpCreator;
    const uint8_t numCcPerBand = 1;

    CcBwpCreator::SimpleOperationBandConf bandConf(centralFrequency, bandwidth, numCcPerBand);
    bandConf.m_numBwp = 1;
    OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc(bandConf);

    // Create channel helper
    Ptr<NrChannelHelper> channelHelper = CreateObject<NrChannelHelper>();
    channelHelper->ConfigureFactories("UMi", "Default", "ThreeGpp");
    channelHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(0)));
    channelHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(true));
    
    // Set beamforming method
    idealBeamformingHelper->SetAttribute("BeamformingMethod",
                                         TypeIdValue(DirectPathBeamforming::GetTypeId()));
    
    channelHelper->AssignChannelsToBands({band});
    allBwps = CcBwpCreator::GetAllBwps({band});
    
    // Configure BWP manager
    nrHelper->SetGnbBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(0));
    nrHelper->SetUeBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(0));

    // Configure antenna parameters
    nrHelper->SetGnbAntennaAttribute("NumRows", UintegerValue(4));
    nrHelper->SetGnbAntennaAttribute("NumColumns", UintegerValue(4));
    nrHelper->SetUeAntennaAttribute("NumRows", UintegerValue(2));
    nrHelper->SetUeAntennaAttribute("NumColumns", UintegerValue(2));

    // Lower transmit powers so coverage is just enough
    nrHelper->SetGnbPhyAttribute("TxPower", DoubleValue(16.0)); // dBm
    nrHelper->SetUePhyAttribute("TxPower", DoubleValue(10.0));  // dBm
    std::cout << "TxPower settings: gNB=16.00 dBm, UE=10.00 dBm" << std::endl;

    // Install NR devices
    NetDeviceContainer gnbDevs = nrHelper->InstallGnbDevice(gnbNodes, allBwps);
    NetDeviceContainer ueDevs = nrHelper->InstallUeDevice(ueNodes, allBwps);
    
    // Install buildings after devices are installed
    BuildingsHelper::Install(ueNodes);
    BuildingsHelper::Install(gnbNodes);

    // Enable traces
    nrHelper->EnableTraces();

    // Internet stack on UEs via EPC-assigned IPs
    InternetStackHelper internet;
    internet.Install(ueNodes);
    Ipv4InterfaceContainer ueIpIfaces = epcHelper->AssignUeIpv4Address(NetDeviceContainer(ueDevs));

    // Attach each UE to the nearest gNB by distance
    for (uint32_t i = 0; i < ueNodes.GetN(); ++i)
    {
        Ptr<MobilityModel> ueMob = ueNodes.Get(i)->GetObject<MobilityModel>();
        Vector uePos = ueMob->GetPosition();
        double bestDist = std::numeric_limits<double>::max();
        uint32_t bestGnbIdx = 0;
        for (uint32_t e = 0; e < gnbNodes.GetN(); ++e)
        {
            Ptr<MobilityModel> em = gnbNodes.Get(e)->GetObject<MobilityModel>();
            Vector ep = em->GetPosition();
            double dx = uePos.x - ep.x;
            double dy = uePos.y - ep.y;
            double dist2 = dx * dx + dy * dy;
            if (dist2 < bestDist)
            {
                bestDist = dist2;
                bestGnbIdx = e;
            }
        }
        nrHelper->AttachToGnb(ueDevs.Get(i), gnbDevs.Get(bestGnbIdx));
    }

    // Report distances from UE0 (Sayed) and UE9 (Sadia) to each gNB
    {
        Ptr<MobilityModel> ue0m = ueNodes.Get(0)->GetObject<MobilityModel>();
        Ptr<MobilityModel> ue9m = ueNodes.Get(nUes - 1)->GetObject<MobilityModel>();
        Vector u0 = ue0m->GetPosition();
        Vector u9 = ue9m->GetPosition();
        std::cout << std::fixed << std::setprecision(2);
        for (uint32_t e = 0; e < gnbNodes.GetN(); ++e)
        {
            Ptr<MobilityModel> em = gnbNodes.Get(e)->GetObject<MobilityModel>();
            Vector ep = em->GetPosition();
            double d0 = std::sqrt((u0.x - ep.x) * (u0.x - ep.x) + (u0.y - ep.y) * (u0.y - ep.y) +
                                  (u0.z - ep.z) * (u0.z - ep.z));
            double d9 = std::sqrt((u9.x - ep.x) * (u9.x - ep.x) + (u9.y - ep.y) * (u9.y - ep.y) +
                                  (u9.z - ep.z) * (u9.z - ep.z));
            std::cout << "UE0→gNB" << e << ": " << d0 << " m, UE9→gNB" << e << ": " << d9 << " m"
                      << std::endl;
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
    Ptr<ListPositionAllocator> remoteHostPos = CreateObject<ListPositionAllocator>();
    remoteHostPos->Add(Vector(field * 0.5, field + 50.0, 0.0)); // Position remote host outside
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
    ipv4h.Assign(internetDevices); // Assign IP addresses to internet devices

    Ipv4StaticRoutingHelper ipv4RoutingHelper;
    Ptr<Ipv4StaticRouting> remoteHostStaticRouting =
        ipv4RoutingHelper.GetStaticRouting(remoteHost->GetObject<Ipv4>());
    remoteHostStaticRouting->SetDefaultRoute(epcHelper->GetUeDefaultGatewayAddress(), 1);

    // Enable pcap and ascii traces on EPC P2P link with requested prefix
    p2ph.EnablePcapAll(kOutDir + "/" + kPcapPrefix, true);
    AsciiTraceHelper ascii;
    Ptr<OutputStreamWrapper> stream =
        ascii.CreateFileStream(kOutDir + "/" + kAsciiTracesPrefix + ".tr");
    p2ph.EnableAsciiAll(stream);

    // Applications: replicate Wi-Fi/LTE case between UE 0 and UE 9
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
    OnOffHelper udpClientA("ns3::UdpSocketFactory",
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
    BulkSendHelper tcpA("ns3::TcpSocketFactory",
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
    for (uint32_t i = 1; i < nUes - 1; ++i)
    {
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
    AnimationInterface anim(kOutDir + "/" + kNetAnimFile);
    anim.SetMaxPktsPerTraceFile(500000); // Increase packet limit to avoid warnings
    anim.EnablePacketMetadata(true);
    anim.UpdateNodeDescription(ueNodes.Get(0), "Sayed");
    anim.UpdateNodeColor(ueNodes.Get(0), 0, 150, 255);
    anim.UpdateNodeDescription(ueNodes.Get(nUes - 1), "Sadia");
    anim.UpdateNodeColor(ueNodes.Get(nUes - 1), 255, 120, 0);
    // gNB visuals (grey)
    anim.UpdateNodeDescription(gnbNodes.Get(0), "gNB-0");
    anim.UpdateNodeColor(gnbNodes.Get(0), 128, 128, 128);
    anim.UpdateNodeDescription(gnbNodes.Get(1), "gNB-1");
    anim.UpdateNodeColor(gnbNodes.Get(1), 128, 128, 128);
    anim.UpdateNodeDescription(gnbNodes.Get(2), "gNB-2");
    anim.UpdateNodeColor(gnbNodes.Get(2), 128, 128, 128);
    // Remote host visuals (green)
    anim.UpdateNodeDescription(remoteHost, "Remote Host");
    anim.UpdateNodeColor(remoteHost, 0, 255, 0);

    // EPC nodes visuals
    anim.UpdateNodeDescription(pgw, "PGW");
    anim.UpdateNodeColor(pgw, 128, 0, 128); // Purple
    anim.UpdateNodeDescription(sgw, "SGW");
    anim.UpdateNodeColor(sgw, 255, 0, 255); // Magenta

    // IPv4 L3 ASCII tracing (emit packets at IP layer to ASCII file)
    {
        AsciiTraceHelper ascii;
        Ptr<OutputStreamWrapper> ipStream = ascii.CreateFileStream(kOutDir + "/ipv4-l3.tr");
        internet.EnableAsciiIpv4All(ipStream);
    }

    Simulator::Stop(Seconds(simStop));
    Simulator::Run();
    monitor->SerializeToXmlFile(kOutDir + "/" + kFlowmonFile, true, true);
    Simulator::Destroy();
    return 0;
}

