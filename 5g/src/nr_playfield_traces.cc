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

// ============================================================================
// HELPER FUNCTION DECLARATIONS
// ============================================================================

// Mobility configuration
void ConfigureUeMobility(NodeContainer& ueNodes, double field, double minHeight, double maxHeight);
void ConfigureGnbMobility(NodeContainer& gnbNodes, double field);

// Network infrastructure
BuildingContainer CreateBuildingObstacles(double field);

// Node setup
void AttachUesToGnbs(Ptr<NrHelper> nrHelper,
                     NodeContainer ueNodes,
                     NodeContainer gnbNodes,
                     NetDeviceContainer ueDevs,
                     NetDeviceContainer gnbDevs);

// Application configuration
void SetupInternetApplications(NodeContainer ueNodes,
                              Ptr<Node> remoteHost,
                              Ipv4InterfaceContainer ueIpIfaces,
                              double simStop);

// ============================================================================
// RRC trace callbacks for better runtime visibility
// ============================================================================
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
    // ========================================================================
    // INITIALIZATION
    // ========================================================================
    PacketMetadata::Enable();
    Packet::EnablePrinting();
    // LogComponentEnable("UdpServer", LOG_LEVEL_INFO); // Disabled for performance

    std::cout << "\n";
    std::cout << "============================================" << std::endl;
    std::cout << " 5G NR Internet Scenario Simulation" << std::endl;
    std::cout << "============================================\n" << std::endl;

    // ========================================================================
    // SIMULATION PARAMETERS
    // ========================================================================
    const uint32_t nUes = 10;
    const double field = 400.0;
    const double simStop = 10.0;  // 10 seconds for faster simulation
    const double minHeight = 0.0;
    const double maxHeight = 30.0;

    std::cout << "Simulation Parameters:" << std::endl;
    std::cout << "  Number of UEs: " << nUes << std::endl;
    std::cout << "  Field size: " << field << "m × " << field << "m" << std::endl;
    std::cout << "  Height range: " << minHeight << "m - " << maxHeight << "m" << std::endl;
    std::cout << "  Simulation time: " << simStop << " seconds\n" << std::endl;

    // ========================================================================
    // CREATE NODES
    // ========================================================================
    NodeContainer ueNodes;
    ueNodes.Create(nUes);
    NodeContainer gnbNodes;
    gnbNodes.Create(2);

    // ========================================================================
    // MOBILITY CONFIGURATION
    // ========================================================================
    ConfigureUeMobility(ueNodes, field, minHeight, maxHeight);
    ConfigureGnbMobility(gnbNodes, field);

    // ========================================================================
    // CREATE BUILDINGS
    // ========================================================================
    BuildingContainer buildings = CreateBuildingObstacles(field);

    // ========================================================================
    // CONFIGURE 5G NR NETWORK
    // ========================================================================
    std::cout << "=== Configuring 5G NR Network ===" << std::endl;
    
    // Create NR helper
    Ptr<NrHelper> nrHelper = CreateObject<NrHelper>();
    
    // Create EPC helper
    Ptr<NrPointToPointEpcHelper> epcHelper = CreateObject<NrPointToPointEpcHelper>();
    nrHelper->SetEpcHelper(epcHelper);
    
    // Create beamforming helper
    Ptr<IdealBeamformingHelper> idealBeamformingHelper = CreateObject<IdealBeamformingHelper>();
    nrHelper->SetBeamformingHelper(idealBeamformingHelper);
    
    // Configure spectrum
    double centralFrequency = 3.5e9;
    double bandwidth = 100e6;
    
    BandwidthPartInfoPtrVector allBwps;
    CcBwpCreator ccBwpCreator;
    const uint8_t numCcPerBand = 1;
    
    CcBwpCreator::SimpleOperationBandConf bandConf(centralFrequency, bandwidth, numCcPerBand);
    bandConf.m_numBwp = 1;
    OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc(bandConf);
    
    // Create channel helper with UMa model
    Ptr<NrChannelHelper> channelHelper = CreateObject<NrChannelHelper>();
    channelHelper->ConfigureFactories("UMa", "Default", "ThreeGpp");
    channelHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(0)));
    channelHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(true));
    std::cout << "Channel Model: UMa (Urban Macro) - for macro cell deployment" << std::endl;
    
    // Set beamforming method
    idealBeamformingHelper->SetAttribute("BeamformingMethod",
                                        TypeIdValue(DirectPathBeamforming::GetTypeId()));
    
    channelHelper->AssignChannelsToBands({band});
    allBwps = CcBwpCreator::GetAllBwps({band});
    
    // Configure BWP manager
    nrHelper->SetGnbBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(0));
    nrHelper->SetUeBwpManagerAlgorithmAttribute("NGBR_LOW_LAT_EMBB", UintegerValue(0));
    
    std::cout << "Using default TxPower settings: gNB=~43 dBm (macro cell), UE=~23 dBm" << std::endl;
    std::cout << "====================================\n" << std::endl;

    // ========================================================================
    // INSTALL DEVICES
    // ========================================================================
    std::cout << "=== Installing NR Devices ===" << std::endl;
    NetDeviceContainer gnbDevs = nrHelper->InstallGnbDevice(gnbNodes, allBwps);
    NetDeviceContainer ueDevs = nrHelper->InstallUeDevice(ueNodes, allBwps);
    
    BuildingsHelper::Install(ueNodes);
    BuildingsHelper::Install(gnbNodes);
    nrHelper->EnableTraces();
    std::cout << "NR devices installed and traces enabled" << std::endl;
    std::cout << "====================================\n" << std::endl;

    // ========================================================================
    // INTERNET STACK
    // ========================================================================
    std::cout << "=== Installing Internet Stack ===" << std::endl;
    
    // Configure TCP with larger buffer sizes for 1 MB packets
    Config::SetDefault("ns3::TcpSocket::SndBufSize", UintegerValue(10 * 1024 * 1024)); // 10 MB
    Config::SetDefault("ns3::TcpSocket::RcvBufSize", UintegerValue(10 * 1024 * 1024)); // 10 MB
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(1400)); // MTU size
    Config::SetDefault("ns3::TcpSocket::InitialCwnd", UintegerValue(10));
    
    InternetStackHelper internet;
    internet.Install(ueNodes);
    Ipv4InterfaceContainer ueIpIfaces = epcHelper->AssignUeIpv4Address(NetDeviceContainer(ueDevs));
    std::cout << "Internet stack installed on all UEs" << std::endl;
    std::cout << "TCP configured with large buffers for 1 MB packet transfers" << std::endl;
    std::cout << "====================================\n" << std::endl;

    // ========================================================================
    // ATTACH UEs TO gNBs
    // ========================================================================
    AttachUesToGnbs(nrHelper, ueNodes, gnbNodes, ueDevs, gnbDevs);

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

    
    // ASCII traces still enabled (smaller file size)
    AsciiTraceHelper ascii;
    Ptr<OutputStreamWrapper> stream =
        ascii.CreateFileStream(kOutDir + "/" + kAsciiTracesPrefix + ".tr");
    p2ph.EnableAsciiAll(stream);


    // ========================================================================
    // SETUP INTERNET APPLICATIONS
    // ========================================================================
    SetupInternetApplications(ueNodes, remoteHost, ueIpIfaces, simStop);

    // ========================================================================
    // MONITORING AND VISUALIZATION
    // ========================================================================
    
    // FlowMonitor for network statistics
    std::cout << "=== Setting Up Monitoring ===" << std::endl;
    FlowMonitorHelper fm;
    Ptr<FlowMonitor> monitor = fm.InstallAll();
    std::cout << "FlowMonitor installed" << std::endl;

    // NetAnim for visualization (must stay in scope for entire simulation)
    AnimationInterface anim(kOutDir + "/" + kNetAnimFile);
    anim.SetMaxPktsPerTraceFile(500000);
    anim.EnablePacketMetadata(true);
    
    // Configure UE colors and descriptions
    const char* ueLabels[] = {"HTTP", "HTTP", "HTTPS", "HTTPS", "Video", "Video", "VoIP", "VoIP", "FTP", "Mixed"};
    uint8_t ueColors[][3] = {
        {0, 150, 255}, {0, 150, 255}, {0, 200, 150}, {0, 200, 150}, {255, 0, 255},
        {255, 0, 255}, {255, 255, 0}, {255, 255, 0}, {255, 150, 0}, {200, 100, 200}
    };
    
    for (uint32_t i = 0; i < ueNodes.GetN(); ++i)
    {
        std::string label = "UE" + std::to_string(i) + "-" + ueLabels[i];
        anim.UpdateNodeDescription(ueNodes.Get(i), label);
        anim.UpdateNodeColor(ueNodes.Get(i), ueColors[i][0], ueColors[i][1], ueColors[i][2]);
    }
    
    // Configure gNB, server, and EPC nodes
    anim.UpdateNodeDescription(gnbNodes.Get(0), "gNB-0-West");
    anim.UpdateNodeColor(gnbNodes.Get(0), 128, 128, 128);
    anim.UpdateNodeDescription(gnbNodes.Get(1), "gNB-1-East");
    anim.UpdateNodeColor(gnbNodes.Get(1), 128, 128, 128);
    anim.UpdateNodeDescription(remoteHost, "Internet-Server");
    anim.UpdateNodeColor(remoteHost, 0, 255, 0);
    anim.UpdateNodeDescription(pgw, "PGW");
    anim.UpdateNodeColor(pgw, 128, 0, 128);
    anim.UpdateNodeDescription(sgw, "SGW");
    anim.UpdateNodeColor(sgw, 255, 0, 255);
    
    std::cout << "NetAnim configured successfully" << std::endl;

    // IPv4 L3 ASCII tracing
    AsciiTraceHelper asciiL3;
    Ptr<OutputStreamWrapper> ipStream = asciiL3.CreateFileStream(kOutDir + "/ipv4-l3.tr");
    internet.EnableAsciiIpv4All(ipStream);
    std::cout << "IPv4 L3 traces enabled" << std::endl;
    std::cout << "====================================\n" << std::endl;

    // ========================================================================
    // RUN SIMULATION
    // ========================================================================
    std::cout << "\n*** Starting simulation for " << simStop << " seconds ***\n" << std::endl;
    
    Simulator::Stop(Seconds(simStop));
    Simulator::Run();
    
    std::cout << "\n*** Simulation completed! ***\n" << std::endl;
    
    // Save FlowMonitor results
    monitor->SerializeToXmlFile(kOutDir + "/" + kFlowmonFile, true, true);
    
    // ========================================================================
    // GENERATE DETAILED REPORT
    // ========================================================================
    std::cout << "\n=== Generating Detailed Report ===" << std::endl;
    
    // Define traffic types for each UE
    std::map<uint32_t, std::string> ueTrafficType;
    ueTrafficType[0] = "HTTP (TCP)";
    ueTrafficType[1] = "HTTP (TCP)";
    ueTrafficType[2] = "HTTPS (TCP)";
    ueTrafficType[3] = "HTTPS (TCP)";
    ueTrafficType[4] = "Video (TCP)";
    ueTrafficType[5] = "Video (TCP)";
    ueTrafficType[6] = "VoIP (UDP)";
    ueTrafficType[7] = "VoIP (UDP)";
    ueTrafficType[8] = "FTP (TCP)";
    ueTrafficType[9] = "Mixed (TCP)";
    
    // Store metrics for each UE
    struct UeMetrics {
        std::string trafficType;
        uint64_t txPackets = 0;
        uint64_t rxPackets = 0;
        uint64_t txBytes = 0;
        uint64_t rxBytes = 0;
        double delaySum = 0.0;
        uint32_t delayCount = 0;
        double throughput = 0.0;
        double pdr = 0.0;
        double avgDelay = 0.0;
    };
    
    std::map<uint32_t, UeMetrics> ueMetrics;
    
    // Initialize metrics for all UEs
    for (uint32_t i = 0; i < nUes; ++i)
    {
        ueMetrics[i].trafficType = ueTrafficType[i];
    }
    
    // Get FlowMonitor statistics
    monitor->CheckForLostPackets();
    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(fm.GetClassifier());
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();
    
    // Process each flow
    for (auto const& flow : stats)
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(flow.first);
        
        // Match flow to UE based on source IP
        for (uint32_t i = 0; i < nUes; ++i)
        {
            Ipv4Address ueAddr = ueIpIfaces.GetAddress(i);
            if (t.sourceAddress == ueAddr)
            {
                ueMetrics[i].txPackets += flow.second.txPackets;
                ueMetrics[i].rxPackets += flow.second.rxPackets;
                ueMetrics[i].txBytes += flow.second.txBytes;
                ueMetrics[i].rxBytes += flow.second.rxBytes;
                
                if (flow.second.rxPackets > 0)
                {
                    ueMetrics[i].delaySum += flow.second.delaySum.GetSeconds();
                    ueMetrics[i].delayCount += flow.second.rxPackets;
                }
                break;
            }
        }
    }
    
    // Calculate final metrics for each UE
    double effectiveSimTime = simStop - 0.5; // Exclude startup time
    for (uint32_t i = 0; i < nUes; ++i)
    {
        if (ueMetrics[i].txPackets > 0)
        {
            ueMetrics[i].pdr = (double)ueMetrics[i].rxPackets / (double)ueMetrics[i].txPackets * 100.0;
        }
        
        if (ueMetrics[i].delayCount > 0)
        {
            ueMetrics[i].avgDelay = (ueMetrics[i].delaySum / ueMetrics[i].delayCount) * 1000.0; // Convert to ms
        }
        
        if (ueMetrics[i].rxBytes > 0)
        {
            ueMetrics[i].throughput = (ueMetrics[i].rxBytes * 8.0) / effectiveSimTime / 1e6; // Mbps
        }
    }
    
    // Generate report file
    std::ofstream reportFile(kOutDir + "/ue_metrics_report.txt");
    
    // Console and file output
    std::string separator = "=================================================================================";
    std::string line;
    
    // Title
    line = "\n5G NR SIMULATION - UE METRICS REPORT";
    std::cout << line << std::endl;
    reportFile << line << std::endl;
    
    line = "Packet Size: 1400 bytes (realistic MTU) | Total Data >= 1 MB per UE";
    std::cout << line << std::endl;
    reportFile << line << std::endl;
    
    line = "Simulation Time: " + std::to_string(simStop) + " seconds";
    std::cout << line << std::endl;
    reportFile << line << std::endl;
    
    std::cout << separator << std::endl;
    reportFile << separator << std::endl;
    
    // Table header
    std::cout << std::left << std::setw(8) << "UE ID" 
              << std::setw(18) << "Traffic Type"
              << std::right << std::setw(12) << "PDR (%)"
              << std::setw(15) << "Delay (ms)"
              << std::setw(18) << "Throughput (Mbps)"
              << std::setw(12) << "TX Pkts"
              << std::setw(12) << "RX Pkts"
              << std::setw(15) << "RX Bytes" << std::endl;
    
    reportFile << std::left << std::setw(8) << "UE ID" 
               << std::setw(18) << "Traffic Type"
               << std::right << std::setw(12) << "PDR (%)"
               << std::setw(15) << "Delay (ms)"
               << std::setw(18) << "Throughput (Mbps)"
               << std::setw(12) << "TX Pkts"
               << std::setw(12) << "RX Pkts"
               << std::setw(15) << "RX Bytes" << std::endl;
    
    std::cout << separator << std::endl;
    reportFile << separator << std::endl;
    
    // Table data
    for (uint32_t i = 0; i < nUes; ++i)
    {
        std::cout << std::left << std::setw(8) << i
                  << std::setw(18) << ueMetrics[i].trafficType
                  << std::right << std::fixed << std::setprecision(2)
                  << std::setw(12) << ueMetrics[i].pdr
                  << std::setw(15) << ueMetrics[i].avgDelay
                  << std::setw(18) << ueMetrics[i].throughput
                  << std::setw(12) << ueMetrics[i].txPackets
                  << std::setw(12) << ueMetrics[i].rxPackets
                  << std::setw(15) << ueMetrics[i].rxBytes << std::endl;
        
        reportFile << std::left << std::setw(8) << i
                   << std::setw(18) << ueMetrics[i].trafficType
                   << std::right << std::fixed << std::setprecision(2)
                   << std::setw(12) << ueMetrics[i].pdr
                   << std::setw(15) << ueMetrics[i].avgDelay
                   << std::setw(18) << ueMetrics[i].throughput
                   << std::setw(12) << ueMetrics[i].txPackets
                   << std::setw(12) << ueMetrics[i].rxPackets
                   << std::setw(15) << ueMetrics[i].rxBytes << std::endl;
    }
    
    std::cout << separator << std::endl;
    reportFile << separator << std::endl;
    
    // Summary statistics
    double avgPdr = 0.0, avgDelay = 0.0, avgThroughput = 0.0;
    uint32_t count = 0;
    
    for (uint32_t i = 0; i < nUes; ++i)
    {
        if (ueMetrics[i].txPackets > 0)
        {
            avgPdr += ueMetrics[i].pdr;
            avgDelay += ueMetrics[i].avgDelay;
            avgThroughput += ueMetrics[i].throughput;
            count++;
        }
    }
    
    if (count > 0)
    {
        avgPdr /= count;
        avgDelay /= count;
        avgThroughput /= count;
    }
    
    line = "\nSUMMARY STATISTICS:";
    std::cout << line << std::endl;
    reportFile << line << std::endl;
    
    std::cout << std::fixed << std::setprecision(2);
    reportFile << std::fixed << std::setprecision(2);
    
    line = "Average PDR: " + std::to_string(avgPdr).substr(0, 5) + " %";
    std::cout << line << std::endl;
    reportFile << line << std::endl;
    
    line = "Average E2E Delay: " + std::to_string(avgDelay).substr(0, 6) + " ms";
    std::cout << line << std::endl;
    reportFile << line << std::endl;
    
    line = "Average Throughput: " + std::to_string(avgThroughput).substr(0, 6) + " Mbps";
    std::cout << line << std::endl;
    reportFile << line << std::endl;
    
    std::cout << separator << std::endl;
    reportFile << separator << std::endl;
    
    reportFile.close();
    
    std::cout << "\nReport saved to: " << kOutDir << "/ue_metrics_report.txt" << std::endl;
    std::cout << "FlowMonitor XML saved to: " << kOutDir << "/" << kFlowmonFile << std::endl;
    std::cout << "All results saved to: " << kOutDir << "/" << std::endl;
    
    Simulator::Destroy();
    return 0;
}

// ============================================================================
// HELPER FUNCTION IMPLEMENTATIONS
// ============================================================================

/**
 * Configure UE mobility using Gauss-Markov model
 * @param ueNodes Container of UE nodes
 * @param field Field size in meters
 * @param minHeight Minimum height for UE movement (meters)
 * @param maxHeight Maximum height for UE movement (meters)
 */
void
ConfigureUeMobility(NodeContainer& ueNodes, double field, double minHeight, double maxHeight)
{
    std::cout << "\n=== Configuring UE Mobility ===" << std::endl;
    
    // Define movement bounds
    double minX = 0.0;
    double maxX = field;
    double minY = 0.0;
    double maxY = field;
    double minZ = minHeight;
    double maxZ = maxHeight;
    
    // Initial positions: distribute UEs across the field with varying heights
    MobilityHelper staMobility;
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
    
    staMobility.SetPositionAllocator(posAlloc);
    staMobility.SetMobilityModel("ns3::GaussMarkovMobilityModel",
        "Bounds", BoxValue(Box(minX, maxX, minY, maxY, minZ, maxZ)),
        "TimeStep", TimeValue(Seconds(1.0)),
        "Alpha", DoubleValue(0.85),
        "MeanVelocity", StringValue("ns3::UniformRandomVariable[Min=0.3|Max=0.8]"),
        "MeanDirection", StringValue("ns3::UniformRandomVariable[Min=0|Max=6.283185307]"),
        "MeanPitch", StringValue("ns3::UniformRandomVariable[Min=-0.05|Max=0.05]"),
        "NormalVelocity", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.0|Bound=0.0]"),
        "NormalDirection", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.1|Bound=0.2]"),
        "NormalPitch", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.01|Bound=0.02]"));
    
    staMobility.Install(ueNodes);
    
    std::cout << "Movement Type: Smooth, correlated pedestrian movement" << std::endl;
    std::cout << "Speed Range: 0.3 - 0.8 m/s (slow walking)" << std::endl;
    std::cout << "Alpha: 0.85 (high memory, smooth trajectories)" << std::endl;
    std::cout << "Bounds: (" << minX << "," << maxX << ") × (" << minY << "," << maxY << ") × (" 
              << minZ << "," << maxZ << ")" << std::endl;
    std::cout << "====================================\n" << std::endl;
}

/**
 * Configure gNB (base station) positions
 * @param gnbNodes Container of gNB nodes
 * @param field Field size in meters
 */
void
ConfigureGnbMobility(NodeContainer& gnbNodes, double field)
{
    std::cout << "=== Configuring gNB Positions ===" << std::endl;
    
    MobilityHelper gnbMob;
    Ptr<ListPositionAllocator> gnbPos = CreateObject<ListPositionAllocator>();
    gnbPos->Add(Vector(-100.0, field * 0.5, 30.0));
    gnbPos->Add(Vector(field + 100.0, field * 0.5, 30.0));
    gnbMob.SetPositionAllocator(gnbPos);
    gnbMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    gnbMob.Install(gnbNodes);
    
    // Report gNB positions and distances
    std::vector<Vector> gnbPositions;
    for (uint32_t e = 0; e < gnbNodes.GetN(); ++e)
    {
        Ptr<MobilityModel> mm = gnbNodes.Get(e)->GetObject<MobilityModel>();
        Vector p = mm->GetPosition();
        gnbPositions.push_back(p);
        std::cout << "gNB" << e << ": (" << p.x << ", " << p.y << ", " << p.z << ")" << std::endl;
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
            std::cout << "gNB" << i << "-gNB" << j << ": " << d << std::endl;
        }
    }
    std::cout << "==================================\n" << std::endl;
}

/**
 * Create building obstacles in the simulation area
 * @param field Field size in meters
 * @return Container with all buildings
 */
BuildingContainer
CreateBuildingObstacles(double field)
{
    std::cout << "=== Creating Building Obstacles ===" << std::endl;
    
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
    std::cout << "Static buildings configured (dynamic movements disabled)" << std::endl;
    std::cout << "====================================\n" << std::endl;
    
    return buildings;
}

/**
 * Attach UEs to nearest gNBs based on distance
 * @param nrHelper NR helper object
 * @param ueNodes Container of UE nodes
 * @param gnbNodes Container of gNB nodes
 * @param ueDevs UE network devices
 * @param gnbDevs gNB network devices
 */
void
AttachUesToGnbs(Ptr<NrHelper> nrHelper,
               NodeContainer ueNodes,
               NodeContainer gnbNodes,
               NetDeviceContainer ueDevs,
               NetDeviceContainer gnbDevs)
{
    std::cout << "=== Attaching UEs to gNBs ===" << std::endl;
    
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
        std::cout << "UE " << i << " attached to gNB" << bestGnbIdx << std::endl;
    }
    
    std::cout << "====================================\n" << std::endl;
}

/**
 * Setup internet applications for all UEs
 * @param ueNodes Container of UE nodes
 * @param remoteHost Remote host node (internet server)
 * @param ueIpIfaces UE IP interfaces
 * @param simStop Simulation stop time
 */
void
SetupInternetApplications(NodeContainer ueNodes,
                         Ptr<Node> remoteHost,
                         Ipv4InterfaceContainer ueIpIfaces,
                         double simStop)
{
    std::cout << "\n=== Setting Up Internet Applications ===" << std::endl;
    
    Ipv4Address remoteHostAddr = remoteHost->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
    std::cout << "Remote Host (Internet Server) IP: " << remoteHostAddr << std::endl;
    
    // Port definitions
    const uint16_t httpPort = 80;
    const uint16_t httpsPort = 443;
    const uint16_t videoPort = 8080;
    const uint16_t voipPort = 5060;
    const uint16_t ftpPort = 21;
    const uint16_t dnsPort = 53;
    
    ApplicationContainer serverApps;
    ApplicationContainer clientApps;
    
    // Servers on Remote Host
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
    
    PacketSinkHelper ftpServer("ns3::TcpSocketFactory",
                               InetSocketAddress(Ipv4Address::GetAny(), ftpPort));
    serverApps.Add(ftpServer.Install(remoteHost));
    
    UdpServerHelper dnsServer(dnsPort);
    serverApps.Add(dnsServer.Install(remoteHost));
    
    serverApps.Start(Seconds(0.5));
    serverApps.Stop(Seconds(simStop));
    
    // Application sends data in realistic packet sizes (1400 bytes = typical MTU)
    // Each UE will transfer >= 1 MB total data
    const uint32_t packetSize = 1400; // Realistic MTU size
    const uint32_t minTransferSize = 2 * 1024 * 1024; // 2 MB total per UE
    
    // UE clients - Each UE transfers >= 1 MB of data using realistic packet sizes
    
    // UE 0-1: HTTP (TCP) - Transfer 2 MB total
    for (uint32_t i = 0; i < 2; ++i)
    {
        BulkSendHelper httpClient("ns3::TcpSocketFactory",
                                 InetSocketAddress(remoteHostAddr, httpPort));
        httpClient.SetAttribute("MaxBytes", UintegerValue(minTransferSize));
        httpClient.SetAttribute("SendSize", UintegerValue(packetSize));
        ApplicationContainer httpApp = httpClient.Install(ueNodes.Get(i));
        httpApp.Start(Seconds(1.0 + i * 0.1));
        httpApp.Stop(Seconds(simStop));
        clientApps.Add(httpApp);
    }
    
    // UE 2-3: HTTPS (TCP) - Transfer 2 MB total
    for (uint32_t i = 2; i < 4; ++i)
    {
        BulkSendHelper httpsClient("ns3::TcpSocketFactory",
                                  InetSocketAddress(remoteHostAddr, httpsPort));
        httpsClient.SetAttribute("MaxBytes", UintegerValue(minTransferSize));
        httpsClient.SetAttribute("SendSize", UintegerValue(packetSize));
        ApplicationContainer httpsApp = httpsClient.Install(ueNodes.Get(i));
        httpsApp.Start(Seconds(1.2 + (i-2) * 0.1));
        httpsApp.Stop(Seconds(simStop));
        clientApps.Add(httpsApp);
    }
    
    // UE 4-5: Video (TCP) - Transfer 3 MB total (higher bandwidth)
    for (uint32_t i = 4; i < 6; ++i)
    {
        BulkSendHelper videoClient("ns3::TcpSocketFactory",
                                  InetSocketAddress(remoteHostAddr, videoPort));
        videoClient.SetAttribute("MaxBytes", UintegerValue(3 * 1024 * 1024));
        videoClient.SetAttribute("SendSize", UintegerValue(packetSize));
        ApplicationContainer videoApp = videoClient.Install(ueNodes.Get(i));
        videoApp.Start(Seconds(1.4 + (i-4) * 0.1));
        videoApp.Stop(Seconds(simStop));
        clientApps.Add(videoApp);
    }
    
    // UE 6-7: VoIP (UDP) - Transfer ~1.5 MB at 1.5 Mbps
    for (uint32_t i = 6; i < 8; ++i)
    {
        OnOffHelper voipClient("ns3::UdpSocketFactory",
                              InetSocketAddress(remoteHostAddr, voipPort));
        voipClient.SetAttribute("DataRate", DataRateValue(DataRate("1.5Mbps")));
        voipClient.SetAttribute("PacketSize", UintegerValue(packetSize));
        voipClient.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1.0]"));
        voipClient.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0.0]"));
        ApplicationContainer voipApp = voipClient.Install(ueNodes.Get(i));
        voipApp.Start(Seconds(1.6 + (i-6) * 0.1));
        voipApp.Stop(Seconds(simStop));
        clientApps.Add(voipApp);
    }
    
    // UE 8: FTP (TCP) - Transfer 2.5 MB total
    BulkSendHelper ftpClient("ns3::TcpSocketFactory",
                            InetSocketAddress(remoteHostAddr, ftpPort));
    ftpClient.SetAttribute("MaxBytes", UintegerValue(2500000));
    ftpClient.SetAttribute("SendSize", UintegerValue(packetSize));
    ApplicationContainer ftpApp = ftpClient.Install(ueNodes.Get(8));
    ftpApp.Start(Seconds(1.8));
    ftpApp.Stop(Seconds(simStop));
    clientApps.Add(ftpApp);
    
    // UE 9: Mixed (TCP) - Transfer 2 MB total
    BulkSendHelper mixedClient("ns3::TcpSocketFactory",
                              InetSocketAddress(remoteHostAddr, httpPort));
    mixedClient.SetAttribute("MaxBytes", UintegerValue(minTransferSize));
    mixedClient.SetAttribute("SendSize", UintegerValue(packetSize));
    ApplicationContainer mixedApp = mixedClient.Install(ueNodes.Get(9));
    mixedApp.Start(Seconds(2.0));
    mixedApp.Stop(Seconds(simStop));
    clientApps.Add(mixedApp);
    
    std::cout << "Internet traffic configured (1400 byte packets, >= 1 MB total per UE):" << std::endl;
    std::cout << "  UE 0-1: HTTP (TCP) - 2 MB total" << std::endl;
    std::cout << "  UE 2-3: HTTPS (TCP) - 2 MB total" << std::endl;
    std::cout << "  UE 4-5: Video (TCP) - 3 MB total" << std::endl;
    std::cout << "  UE 6-7: VoIP (UDP) - ~1.5 MB total" << std::endl;
    std::cout << "  UE 8:   FTP (TCP) - 2.5 MB total" << std::endl;
    std::cout << "  UE 9:   Mixed (TCP) - 2 MB total" << std::endl;
    std::cout << "====================================\n" << std::endl;
}
