#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/mesh-module.h"
#include "ns3/wifi-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/ipv4-flow-classifier.h"
#include "ns3/animation-interface.h"
#include "ns3/csma-module.h"
#include "ns3/buildings-module.h"
#include "ns3/rng-seed-manager.h"
#include "ns3/config.h"
#include "ns3/wifi-net-device.h"
#include "ns3/ipv4-routing-table-entry.h"
#include "ns3/node-list.h"
#include "ns3/mac48-address.h"
#include "ns3/simulator.h"
#include "ns3/sta-wifi-mac.h"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <map>
#include <limits>
#include <iostream>

using namespace ns3;
                                                                    
NS_LOG_COMPONENT_DEFINE("MeshSimulation");

// ============================================================================
// Mesh AP Device Configuration (Based on Real Hardware - param.csv)
// ============================================================================
struct MeshAPDeviceConfig
{
    std::string name;                    // Device name
    std::string description;             // Use case description
    
    // Physical layer parameters
    double txPowerStart;                 // TX power start (dBm) - for mesh backhaul
    double txPowerEnd;                   // TX power end (dBm) - for mesh backhaul
    double hotspotTxPower;               // TX power for hotspot/AP mode (dBm) - separate radio
    double rxSensitivity;                // RX sensitivity (dBm)
    double rxGain;                       // RX antenna gain (dB)
    double txGain;                       // TX antenna gain (dB)
    
    // WiFi configuration
    WifiStandard wifiStandard;           // WiFi standard enum
    std::string dataMode;                // Data mode (e.g., "VhtMcs8")
    uint32_t numInterfaces;              // Number of mesh interfaces
    
    // Topology parameters (for 250m spacing in 3x3 grid)
    double meshRange;                    // Expected mesh range (m)
    
    // Constructor
    MeshAPDeviceConfig(std::string n, std::string desc, double txStart, double txEnd,
                      double hotspotTx, double rxSens, double rxG, double txG, 
                      WifiStandard standard, std::string mode, uint32_t interfaces, double range)
        : name(n), description(desc), txPowerStart(txStart), txPowerEnd(txEnd),
          hotspotTxPower(hotspotTx), rxSensitivity(rxSens), rxGain(rxG), txGain(txG), 
          wifiStandard(standard), dataMode(mode), numInterfaces(interfaces),
          meshRange(range) {}
};

/*
 * Factory function to get mesh device configuration by ID.
 * All profiles are configured for a 2.4GHz MESH interface (txPowerStart)
 * and a 5GHz HOTSPOT interface (hotspotTxPower).
 */
MeshAPDeviceConfig GetMeshDeviceConfig(uint32_t configId)
{
    switch(configId) {
        case 1:
            // ============================================================================
            // Case 1: TP-Link EAP225-Outdoor (Verified Specs)
            // Models the real device using its 2.4GHz radio for mesh and 5GHz for hotspot.
            // ============================================================================
            return MeshAPDeviceConfig(
                "TP-Link EAP225-Outdoor",
                "802.11n mesh @ 2.4GHz backhaul, 5GHz hotspot",
                23.0,                           // txPowerStart (dBm) - Verified 2.4GHz spec
                23.0,                           // txPowerEnd (dBm)
                22.0,                           // hotspotTxPower (dBm) - Verified 5GHz spec
                -90.0,                          // rxSensitivity (dBm) - Verified @ lowest rate
                5.0,                            // rxGain (dB) - External antenna
                5.0,                            // txGain (dB) - External antenna
                WIFI_STANDARD_80211n,           // wifiStandard (2.4 GHz, 802.11s compatible)
                "HtMcs7",                       // dataMode (802.11n)
                1,                              // numInterfaces
                300.0                           // meshRange (m)
            );
        
        case 2:
            // ============================================================================
            // Case 2: Netgear Orbi 960 (Premium WiFi 6E - More Antennas)
            // Real device: WiFi 6E, quad-band (2.4G, 5G-1, 5G-2, 6G), 12 antennas
            // NS-3 mesh: Using 802.11ax @ 2.4GHz for mesh with realistic PHY params
            // ============================================================================
            return MeshAPDeviceConfig(
                "Netgear Orbi 960 (WiFi 6E)",
                "Premium indoor mesh (802.11ax @ 2.4GHz mesh, 12 antennas, WiFi 6E)",
                20.0,                           // txPowerStart (dBm) - FCC indoor limit
                20.0,                           // txPowerEnd (dBm)
                20.0,                           // hotspotTxPower (dBm) - 5GHz hotspot
                -92.0,                          // rxSensitivity (dBm) - Better due to more antennas
                3.0,                            // rxGain (dB) - 12 antennas = better gain
                3.0,                            // txGain (dB)
                WIFI_STANDARD_80211ax,          // wifiStandard (WiFi 6E)
                "HeMcs9",                       // dataMode (High MCS - premium device)
                1,                              // numInterfaces
                120.0                           // meshRange (m)
            );
        
        case 3:
            // ============================================================================
            // Case 3: ASUS ZenWiFi XT8 (Mid-range WiFi 6 - Fewer Antennas)
            // Real device: WiFi 6, tri-band (2.4G, 5G-1, 5G-2), 6 antennas
            // NS-3 mesh: Using 802.11ax @ 2.4GHz for mesh with realistic PHY params
            // ============================================================================
            return MeshAPDeviceConfig(
                "ASUS ZenWiFi AX (XT8)",
                "Mid-range indoor mesh (802.11ax @ 2.4GHz mesh, 6 antennas, WiFi 6)",
                20.0,                           // txPowerStart (dBm) - FCC indoor limit
                20.0,                           // txPowerEnd (dBm)
                20.0,                           // hotspotTxPower (dBm) - 5GHz hotspot
                -88.0,                          // rxSensitivity (dBm) - Standard WiFi 6
                2.0,                            // rxGain (dB) - 6 antennas = standard gain
                2.0,                            // txGain (dB)
                WIFI_STANDARD_80211ax,          // wifiStandard (WiFi 6)
                "HeMcs7",                       // dataMode (Medium MCS - mid-range device)
                1,                              // numInterfaces
                100.0                           // meshRange (m)
            );
        
        case 0:
        default:
            // Default: Current configuration from wifi-test-2-adhoc-grid.cc
            // 802.11g, 2.4 GHz, medium power for testing
            return MeshAPDeviceConfig(
                "Default Test Configuration",
                "Current 802.11g mesh for testing (2.4 GHz)",
                20.0,                           // txPowerStart (dBm) - default mesh backhaul
                20.0,                           // txPowerEnd (dBm)
                20.0,                           // hotspotTxPower (dBm) - default hotspot (same as mesh)
                -96.0,                          // rxSensitivity (dBm) - 802.11g typical
                0.0,                            // rxGain (dB) - no antenna gain
                0.0,                            // txGain (dB)
                WIFI_STANDARD_80211g,           // WiFi standard - current default
                "ErpOfdmRate54Mbps",            // Data mode (802.11g)
                1,                              // numInterfaces - single band
                250.0                           // meshRange (m)
            );
    }
}

// ============================================================================
// Struct to hold mesh network configuration
// ============================================================================
struct MeshNetworkConfig
{
    NodeContainer meshNodes;
    NetDeviceContainer meshDevices;
    Ipv4InterfaceContainer meshInterfaces;
    YansWifiPhyHelper wifiPhy;
};

// ============================================================================
// Struct to hold internet infrastructure configuration
// ============================================================================
struct InternetConfig
{
    NodeContainer internetNodes;
    NetDeviceContainer backhaulDevices;
    NetDeviceContainer backboneDevices;
    Ipv4InterfaceContainer backhaulInterfaces;
    Ipv4InterfaceContainer internetInterfaces;
};

// ============================================================================
// Struct to hold AP/STA hotspot configuration
// ============================================================================
struct HotspotConfig
{
    NodeContainer staNodes;
    NetDeviceContainer apDevices;
    NetDeviceContainer staDevices;
    Ipv4InterfaceContainer apInterfaces;
    Ipv4InterfaceContainer staInterfaces;
    std::vector<uint32_t> apNodeIndices;
    uint32_t primaryApNodeIndex;
    Ssid commonSsid;
    std::map<Mac48Address, uint32_t> apBssidToMeshIndex;
    std::map<uint32_t, uint32_t> nodeIdToStaIndex;
    std::vector<uint32_t> currentStaApIndex;
};

namespace
{
struct StaRoamingContext
{
    MeshNetworkConfig* meshConfig{nullptr};
    HotspotConfig* hotspotConfig{nullptr};
    bool enabled{false};
};

StaRoamingContext g_staRoamingContext;

void
RemoveExistingHostRoute(Ptr<Ipv4StaticRouting> routing, const Ipv4Address& destination)
{
    for (uint32_t idx = 0; idx < routing->GetNRoutes(); ++idx)
    {
        Ipv4RoutingTableEntry entry = routing->GetRoute(idx);
        if (entry.IsHost() && entry.GetDest() == destination)
        {
            routing->RemoveRoute(idx);
            return;
        }
    }
}

void
RemoveExistingDefaultRoute(Ptr<Ipv4StaticRouting> routing)
{
    for (uint32_t idx = 0; idx < routing->GetNRoutes(); ++idx)
    {
        Ipv4RoutingTableEntry entry = routing->GetRoute(idx);
        if (entry.IsDefault())
        {
            routing->RemoveRoute(idx);
            return;
        }
    }
}

void
UpdateStaRouting(uint32_t staIndex, uint32_t apNodeIndex)
{
    if (!g_staRoamingContext.enabled || g_staRoamingContext.meshConfig == nullptr ||
        g_staRoamingContext.hotspotConfig == nullptr)
    {
        return;
    }

    MeshNetworkConfig& meshConfig = *g_staRoamingContext.meshConfig;
    HotspotConfig& hotspotConfig = *g_staRoamingContext.hotspotConfig;

    NS_ABORT_IF(staIndex >= hotspotConfig.staNodes.GetN());
    NS_ABORT_IF(apNodeIndex >= meshConfig.meshNodes.GetN());

    Ipv4Address staIp = hotspotConfig.staInterfaces.GetAddress(staIndex);
    Ipv4Address apMeshIp = meshConfig.meshInterfaces.GetAddress(apNodeIndex);
    Ipv4Address apHotspotIp = hotspotConfig.apInterfaces.GetAddress(apNodeIndex);

    Ipv4StaticRoutingHelper staticRouting;

    // Update gateway host route
    Ptr<Node> gatewayNode = meshConfig.meshNodes.Get(0);
    Ptr<Ipv4> gatewayIpv4 = gatewayNode->GetObject<Ipv4>();
    Ptr<Ipv4StaticRouting> gatewayRouting = staticRouting.GetStaticRouting(gatewayIpv4);
    Ptr<NetDevice> gatewayMeshDevice = meshConfig.meshDevices.Get(0);
    uint32_t gatewayMeshInterface = gatewayIpv4->GetInterfaceForDevice(gatewayMeshDevice);
    RemoveExistingHostRoute(gatewayRouting, staIp);
    gatewayRouting->AddHostRouteTo(staIp, apMeshIp, gatewayMeshInterface);

    // Update STA default route
    Ptr<Node> staNode = hotspotConfig.staNodes.Get(staIndex);
    Ptr<Ipv4> staIpv4 = staNode->GetObject<Ipv4>();
    Ptr<Ipv4StaticRouting> staRouting = staticRouting.GetStaticRouting(staIpv4);
    Ptr<NetDevice> staDevice = hotspotConfig.staDevices.Get(staIndex);
    uint32_t staInterface = staIpv4->GetInterfaceForDevice(staDevice);
    RemoveExistingDefaultRoute(staRouting);
    staRouting->SetDefaultRoute(apHotspotIp, staInterface);

    hotspotConfig.currentStaApIndex[staIndex] = apNodeIndex;

    std::cout << Simulator::Now().GetSeconds() << "s STA " << staIndex
              << " host route via mesh node " << apNodeIndex << " (STA IP " << staIp
              << ", AP mesh IP " << apMeshIp << ", AP hotspot IP " << apHotspotIp << ")"
              << std::endl;
}

void
HandleStaAssociation(uint32_t nodeId, Mac48Address apAddress)
{
    if (!g_staRoamingContext.enabled || g_staRoamingContext.hotspotConfig == nullptr)
    {
        return;
    }

    HotspotConfig& hotspotConfig = *g_staRoamingContext.hotspotConfig;
    auto staIt = hotspotConfig.nodeIdToStaIndex.find(nodeId);
    if (staIt == hotspotConfig.nodeIdToStaIndex.end())
    {
        return;
    }
    uint32_t staIndex = staIt->second;

    auto apIt = hotspotConfig.apBssidToMeshIndex.find(apAddress);
    if (apIt == hotspotConfig.apBssidToMeshIndex.end())
    {
        NS_LOG_WARN("STA " << staIndex << " associated with unknown AP BSSID " << apAddress);
        return;
    }
    uint32_t apNodeIndex = apIt->second;
    UpdateStaRouting(staIndex, apNodeIndex);
}

void
HandleStaDeAssociation(uint32_t nodeId, Mac48Address apAddress)
{
    if (!g_staRoamingContext.enabled || g_staRoamingContext.hotspotConfig == nullptr)
    {
        return;
    }

    HotspotConfig& hotspotConfig = *g_staRoamingContext.hotspotConfig;
    auto staIt = hotspotConfig.nodeIdToStaIndex.find(nodeId);
    if (staIt == hotspotConfig.nodeIdToStaIndex.end())
    {
        return;
    }
    uint32_t staIndex = staIt->second;
    hotspotConfig.currentStaApIndex[staIndex] = std::numeric_limits<uint32_t>::max();

    std::cout << Simulator::Now().GetSeconds() << "s STA " << staIndex
              << " disassociated from AP " << apAddress << std::endl;
}

void
EnableStaRoamingTracing(MeshNetworkConfig& meshConfig, HotspotConfig& hotspotConfig, bool enableHotspot)
{
    if (!enableHotspot)
    {
        return;
    }

    g_staRoamingContext.meshConfig = &meshConfig;
    g_staRoamingContext.hotspotConfig = &hotspotConfig;
    g_staRoamingContext.enabled = true;

    std::cout << "STA roaming tracing enabled (shared SSID: " << hotspotConfig.commonSsid.PeekString()
              << ")" << std::endl;

    uint32_t tracedCount = 0;
    for (uint32_t i = 0; i < hotspotConfig.staDevices.GetN(); ++i)
    {
        Ptr<WifiNetDevice> staDevice = DynamicCast<WifiNetDevice>(hotspotConfig.staDevices.Get(i));
        if (!staDevice)
        {
            continue;
        }
        Ptr<StaWifiMac> staMac = DynamicCast<StaWifiMac>(staDevice->GetMac());
        if (!staMac)
        {
            continue;
        }
        uint32_t nodeId = hotspotConfig.staNodes.Get(i)->GetId();
        staMac->TraceConnectWithoutContext("Assoc",
                                           MakeBoundCallback(&HandleStaAssociation, nodeId));
        staMac->TraceConnectWithoutContext("DeAssoc",
                                           MakeBoundCallback(&HandleStaDeAssociation, nodeId));
        std::cout << "  STA node " << nodeId << " trace hooks attached" << std::endl;
        ++tracedCount;
    }

    std::cout << "  Registered association callbacks for " << tracedCount << " STA MAC(s)"
              << std::endl;
}

} // namespace

// ============================================================================
// Helper: Predefined six-node mesh layout positions
// ============================================================================
std::vector<Vector> GetSixNodeMeshPositions(double meshApHeight)
{
    return {
        Vector(150.0, 0.0, meshApHeight),
        Vector(300.0, 0.0, meshApHeight),
        Vector(150.0, 150.0, meshApHeight),
        Vector(300.0, 150.0, meshApHeight),
        Vector(150.0, 300.0, meshApHeight),
        Vector(300.0, 300.0, meshApHeight)
    };
}

std::vector<Vector> GetCommonStaAnchorPositions()
{
    return {
        Vector(170.0, 10.0, 5.0),   // AP0 +20m east
        Vector(135.0, 25.0, 5.0),   // AP0 +25m north-west
        Vector(320.0, 10.0, 5.0),   // AP1 +20m east
        Vector(285.0, 22.0, 5.0),   // AP1 +25m north-west
        Vector(170.0, 170.0, 5.0),  // AP2 +20m east
        Vector(135.0, 165.0, 5.0),  // AP2 +25m south-west
        Vector(320.0, 170.0, 5.0),  // AP3 +20m east
        Vector(285.0, 165.0, 5.0),  // AP3 +25m south-west
        Vector(170.0, 320.0, 5.0),  // AP4 +20m east
        Vector(320.0, 320.0, 5.0)   // AP5 +20m east
    };
}

// ============================================================================
// Function: Set up mesh network with WiFi and mobility
// ============================================================================
MeshNetworkConfig SetupMeshNetwork(uint32_t nNodes, uint32_t gridWidth, double nodeSpacing, double meshApHeight, const MeshAPDeviceConfig& deviceCfg)
{
    NS_LOG_FUNCTION("Setting up mesh network with " << nNodes << " nodes at height " << meshApHeight << "m");
    NS_LOG_INFO("Using device config: " << deviceCfg.name);
    
    MeshNetworkConfig config;
    
    // Create mesh nodes
    config.meshNodes.Create(nNodes);
    
    // Set up Wi-Fi Mesh with configured standard
    WifiMacHelper wifiMac;
    WifiHelper wifi;
    
    // Set WiFi standard from device configuration
    wifi.SetStandard(deviceCfg.wifiStandard);
    
    NS_LOG_INFO("WiFi Standard: " << deviceCfg.wifiStandard << ", Data Mode: " << deviceCfg.dataMode);

    YansWifiChannelHelper wifiChannel;
    wifiChannel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    
    // Use ONLY HybridBuildingsPropagationLossModel (includes distance loss internally)
    // NO extra arguments - use default parameters
    wifiChannel.AddPropagationLoss("ns3::HybridBuildingsPropagationLossModel");
    
    
    
    config.wifiPhy.SetChannel(wifiChannel.Create());
    
    // Apply device-specific PHY parameters
    config.wifiPhy.Set("TxPowerStart", DoubleValue(deviceCfg.txPowerStart));
    config.wifiPhy.Set("TxPowerEnd", DoubleValue(deviceCfg.txPowerEnd));
    config.wifiPhy.Set("RxSensitivity", DoubleValue(deviceCfg.rxSensitivity));
    config.wifiPhy.Set("RxGain", DoubleValue(deviceCfg.rxGain));
    config.wifiPhy.Set("TxGain", DoubleValue(deviceCfg.txGain));
    
    NS_LOG_INFO("TX Power: " << deviceCfg.txPowerStart << " dBm, RX Sensitivity: " << deviceCfg.rxSensitivity << " dBm");
    NS_LOG_INFO("Antenna Gains - RX: " << deviceCfg.rxGain << " dB, TX: " << deviceCfg.txGain << " dB");

    // Enable ASCII tracing *before* installing devices
    AsciiTraceHelper ascii;
    config.wifiPhy.EnableAsciiAll(ascii.CreateFileStream("wifi_test_research/six_node_layout/wifi-test-2-adhoc-grid-six.tr"));

    MeshHelper mesh;
    mesh = MeshHelper::Default();
    mesh.SetStackInstaller("ns3::Dot11sStack");
    mesh.SetSpreadInterfaceChannels(MeshHelper::SPREAD_CHANNELS);
    mesh.SetMacType("RandomStart", TimeValue(Seconds(0.1)));
    mesh.SetNumberOfInterfaces(deviceCfg.numInterfaces);  // Use device config

    config.meshDevices = mesh.Install(config.wifiPhy, config.meshNodes);
    
    NS_LOG_INFO("Mesh installed with " << deviceCfg.numInterfaces << " interface(s)");

    // Install Internet stack
    InternetStackHelper internetStack;
    internetStack.Install(config.meshNodes);

    // Assign IP addresses to mesh network
    Ipv4AddressHelper address;
    address.SetBase("10.1.1.0", "255.255.255.0");
    config.meshInterfaces = address.Assign(config.meshDevices);

    // Set up mobility model (custom six-node layout)
    std::vector<Vector> meshPositions = GetSixNodeMeshPositions(meshApHeight);

    if (nNodes > meshPositions.size())
    {
        NS_LOG_WARN("Requested " << nNodes << " mesh nodes, but six-node layout only defines "
                                 << meshPositions.size() << " positions. Extra nodes will use grid fallback.");
    }

    Ptr<ListPositionAllocator> positionAlloc = CreateObject<ListPositionAllocator>();
    for (uint32_t i = 0; i < nNodes; ++i)
    {
        Vector pos;
        if (i < meshPositions.size())
        {
            pos = meshPositions[i];
        }
        else
        {
            uint32_t fallbackWidth = gridWidth > 0 ? gridWidth : static_cast<uint32_t>(std::ceil(std::sqrt(nNodes)));
            double x = (i % fallbackWidth) * nodeSpacing;
            double y = (i / fallbackWidth) * nodeSpacing;
            pos = Vector(x, y, meshApHeight);
        }
        positionAlloc->Add(pos);
        NS_LOG_INFO("Mesh node " << i << " position set to (" << pos.x << ", " << pos.y << ", " << pos.z << ")");
    }

    MobilityHelper mobility;
    mobility.SetPositionAllocator(positionAlloc);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(config.meshNodes);
    
    // Fixed building layout to match 5G/LTE playfield scenarios (400m x 400m field)
    BuildingContainer buildings;
    Ptr<Building> leftBelow = CreateObject<Building>();
    leftBelow->SetBoundaries(Box(0.0, 60.0, 96.0, 104.0, 0.0, 10.0));
    leftBelow->SetBuildingType(Building::Residential);
    leftBelow->SetExtWallsType(Building::ConcreteWithWindows);
    buildings.Add(leftBelow);
    Ptr<Building> rightBelow = CreateObject<Building>();
    rightBelow->SetBoundaries(Box(340.0, 400.0, 96.0, 104.0, 0.0, 10.0));
    rightBelow->SetBuildingType(Building::Residential);
    rightBelow->SetExtWallsType(Building::ConcreteWithWindows);
    buildings.Add(rightBelow);
    Ptr<Building> leftAbove = CreateObject<Building>();
    leftAbove->SetBoundaries(Box(0.0, 60.0, 296.0, 304.0, 0.0, 10.0));
    leftAbove->SetBuildingType(Building::Residential);
    leftAbove->SetExtWallsType(Building::ConcreteWithWindows);
    buildings.Add(leftAbove);
    Ptr<Building> rightAbove = CreateObject<Building>();
    rightAbove->SetBoundaries(Box(340.0, 400.0, 296.0, 304.0, 0.0, 10.0));
    rightAbove->SetBuildingType(Building::Residential);
    rightAbove->SetExtWallsType(Building::ConcreteWithWindows);
    buildings.Add(rightAbove);
    Ptr<Building> cluster250a = CreateObject<Building>();
    cluster250a->SetBoundaries(Box(80.0, 140.0, 300.0, 308.0, 0.0, 15.0));
    cluster250a->SetBuildingType(Building::Office);
    cluster250a->SetExtWallsType(Building::ConcreteWithWindows);
    buildings.Add(cluster250a);
    Ptr<Building> cluster250b = CreateObject<Building>();
    cluster250b->SetBoundaries(Box(170.0, 250.0, 300.0, 308.0, 0.0, 12.0));
    cluster250b->SetBuildingType(Building::Office);
    cluster250b->SetExtWallsType(Building::ConcreteWithWindows);
    buildings.Add(cluster250b);
    Ptr<Building> cluster50 = CreateObject<Building>();
    cluster50->SetBoundaries(Box(255.0, 335.0, 20.0, 28.0, 0.0, 18.0));
    cluster50->SetBuildingType(Building::Commercial);
    cluster50->SetExtWallsType(Building::ConcreteWithWindows);
    buildings.Add(cluster50);

    BuildingsHelper::Install(config.meshNodes);

    NS_LOG_INFO("Mesh network setup complete with fixed building layout (400m x 400m x 30m)");
    NS_LOG_INFO("  Node spacing: " << nodeSpacing << "m");
    return config;
}

// ============================================================================
// Function: Set up internet infrastructure (ISP router, server, backhaul)
// ============================================================================
InternetConfig SetupInternetInfrastructure(NodeContainer meshNodes, double nodeSpacing, double meshApHeight)
{
    NS_LOG_FUNCTION("Setting up internet infrastructure");
    
    InternetConfig config;
    
    // Create internet infrastructure nodes
    config.internetNodes.Create(2);  // ISP router + Internet server
    
    // Install internet stack
    InternetStackHelper internetStack;
    internetStack.Install(config.internetNodes);
    
    // Create Ethernet (CSMA) backhaul link from node 0 to ISP router
    CsmaHelper csma;
    csma.SetChannelAttribute("DataRate", StringValue("1Gbps"));
    csma.SetChannelAttribute("Delay", TimeValue(NanoSeconds(6560)));

    NodeContainer backhaulLink;
    backhaulLink.Add(meshNodes.Get(0));      // Mesh gateway (node 0)
    backhaulLink.Add(config.internetNodes.Get(0));  // ISP router
    config.backhaulDevices = csma.Install(backhaulLink);

    // Create internet backbone (ISP router to internet server)
    NodeContainer internetBackbone;
    internetBackbone.Add(config.internetNodes.Get(0));  // ISP router
    internetBackbone.Add(config.internetNodes.Get(1));  // Internet server
    config.backboneDevices = csma.Install(internetBackbone);
    
    // Assign IP addresses to backhaul link
    Ipv4AddressHelper backhaulAddress;
    backhaulAddress.SetBase("192.168.100.0", "255.255.255.0");
    config.backhaulInterfaces = backhaulAddress.Assign(config.backhaulDevices);

    // Assign IP addresses to internet backbone (simulating public IPs)
    Ipv4AddressHelper internetAddress;
    internetAddress.SetBase("8.8.8.0", "255.255.255.0");
    config.internetInterfaces = internetAddress.Assign(config.backboneDevices);
    
    // Set up mobility for internet nodes (stationary)
    MobilityHelper internetMobility;
    internetMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    internetMobility.Install(config.internetNodes);
    
    Ptr<ConstantPositionMobilityModel> posRouter = 
        config.internetNodes.Get(0)->GetObject<ConstantPositionMobilityModel>();
    posRouter->SetPosition(Vector(-400.0, nodeSpacing, meshApHeight));  // Same height as mesh APs
    
    Ptr<ConstantPositionMobilityModel> posServer = 
        config.internetNodes.Get(1)->GetObject<ConstantPositionMobilityModel>();
    posServer->SetPosition(Vector(-700.0, nodeSpacing, meshApHeight));  // Same height as mesh APs
    
    // Aggregate building information to internet nodes
    BuildingsHelper::Install(config.internetNodes);
    
    NS_LOG_INFO("Internet infrastructure setup complete");
    return config;
}

// ============================================================================
// Function: Set up hotspot infrastructure (AP on mesh node + mobile STA clients)
// ============================================================================
HotspotConfig SetupHotspotInfrastructure(NodeContainer meshNodes, 
                                          uint32_t primaryApNodeIndex,
                                          uint32_t numStaNodes,
                                          double nodeSpacing,
                                          double staHeight,
                                          const MeshAPDeviceConfig& deviceCfg)
{
    NS_LOG_FUNCTION("Setting up hotspot infrastructure with " << numStaNodes << " STA clients");
    NS_LOG_INFO("Using hotspot TX power: " << deviceCfg.hotspotTxPower << " dBm from device config");

    HotspotConfig config;
    config.primaryApNodeIndex = primaryApNodeIndex;
    config.commonSsid = Ssid("MeshHotspot");

    uint32_t meshCount = meshNodes.GetN();
    if (numStaNodes < meshCount)
    {
        NS_LOG_WARN("Requested " << numStaNodes << " STAs but there are " << meshCount
                     << " mesh nodes; some APs will not have dedicated clients.");
    }

    // Create STA nodes and install Internet stack
    config.staNodes.Create(numStaNodes);
    InternetStackHelper internetStack;
    internetStack.Install(config.staNodes);

    // Wi-Fi helpers for hotspot radios
    WifiHelper hotspotWifi;
    hotspotWifi.SetStandard(WIFI_STANDARD_80211ac);

    YansWifiChannelHelper hotspotChannel;
    hotspotChannel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    hotspotChannel.AddPropagationLoss("ns3::HybridBuildingsPropagationLossModel");

    Ptr<YansWifiChannel> sharedHotspotChannel = hotspotChannel.Create();

    // AP PHY: high-gain, higher power
    YansWifiPhyHelper apPhy;
    apPhy.SetChannel(sharedHotspotChannel);
    apPhy.Set("TxPowerStart", DoubleValue(deviceCfg.hotspotTxPower));
    apPhy.Set("TxPowerEnd", DoubleValue(deviceCfg.hotspotTxPower));
    apPhy.Set("TxGain", DoubleValue(deviceCfg.txGain));
    apPhy.Set("RxGain", DoubleValue(deviceCfg.rxGain));
    apPhy.Set("RxSensitivity", DoubleValue(deviceCfg.rxSensitivity));
    apPhy.Set("RxNoiseFigure", DoubleValue(5.0));

    // STA PHY: handheld client budget
    YansWifiPhyHelper staPhy;
    staPhy.SetChannel(sharedHotspotChannel);
    staPhy.Set("TxPowerStart", DoubleValue(15.0));
    staPhy.Set("TxPowerEnd", DoubleValue(15.0));
    staPhy.Set("TxGain", DoubleValue(1.0));
    staPhy.Set("RxGain", DoubleValue(1.0));
    staPhy.Set("RxSensitivity", DoubleValue(-90.0));
    staPhy.Set("RxNoiseFigure", DoubleValue(7.0));

    // Optional ASCII tracing
    AsciiTraceHelper ascii;
    apPhy.EnableAsciiAll(ascii.CreateFileStream("wifi_test_research/six_node_layout/wifi-test-2-ap-six.tr"));
    staPhy.EnableAsciiAll(ascii.CreateFileStream("wifi_test_research/six_node_layout/wifi-test-2-sta-six.tr"));

    // Install AP devices on every mesh node (shared SSID for roaming)
    for (uint32_t i = 0; i < meshCount; ++i)
    {
        config.apNodeIndices.push_back(i);
        WifiMacHelper apMac;
        apMac.SetType("ns3::ApWifiMac",
                      "Ssid", SsidValue(config.commonSsid),
                      "BeaconGeneration", BooleanValue(true),
                      "BeaconInterval", TimeValue(MicroSeconds(102400)));
        NetDeviceContainer apDev = hotspotWifi.Install(apPhy, apMac, meshNodes.Get(i));
        config.apDevices.Add(apDev);

        Ptr<WifiNetDevice> apWifiDev = DynamicCast<WifiNetDevice>(apDev.Get(0));
        if (apWifiDev)
        {
            Mac48Address bssid = apWifiDev->GetMac()->GetBssid(0);
            config.apBssidToMeshIndex[bssid] = i;
        }
    }

    // Install STA devices that can freely roam
    for (uint32_t i = 0; i < numStaNodes; ++i)
    {
        WifiMacHelper staMac;
        staMac.SetType("ns3::StaWifiMac",
                       "Ssid", SsidValue(config.commonSsid),
                       "ActiveProbing", BooleanValue(true));
        NetDeviceContainer staDev = hotspotWifi.Install(staPhy, staMac, config.staNodes.Get(i));
        config.staDevices.Add(staDev);

        Ptr<Node> staNode = config.staNodes.Get(i);
        config.nodeIdToStaIndex[staNode->GetId()] = i;
        config.currentStaApIndex.push_back(std::numeric_limits<uint32_t>::max());
    }

    // Assign unique IP ranges
    Ipv4AddressHelper staAddress;
    staAddress.SetBase("192.168.1.0", "255.255.255.0", "0.0.0.1");
    config.staInterfaces = staAddress.Assign(config.staDevices);

    Ipv4AddressHelper apAddress;
    apAddress.SetBase("192.168.1.0", "255.255.255.0", "0.0.0.101");
    config.apInterfaces = apAddress.Assign(config.apDevices);

    // Configure STA initial positions near their associated APs using anchor list
    const std::vector<Vector> anchorPositions = GetCommonStaAnchorPositions();

    for (uint32_t i = 0; i < numStaNodes; ++i)
    {
        Vector staPos = anchorPositions.empty()
                            ? Vector(0.0, 0.0, staHeight > 0.0 ? staHeight : 1.5)
                            : anchorPositions[i % anchorPositions.size()];

        // Adjust Z if caller requested a specific STA height
        if (staHeight > 0.0)
        {
            staPos.z = staHeight;
        }

        Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
        posAlloc->Add(staPos);

        MobilityHelper staMobilityHelper;
        staMobilityHelper.SetPositionAllocator(posAlloc);
        staMobilityHelper.SetMobilityModel("ns3::GaussMarkovMobilityModel",
            "Bounds", BoxValue(Box(0.0, 400.0,
                                    0.0, 400.0,
                                    0.0, 30.0)),
            "TimeStep", TimeValue(Seconds(1.0)),
            "Alpha", DoubleValue(0.85),
            "MeanVelocity", StringValue("ns3::UniformRandomVariable[Min=0.3|Max=0.8]"),
            "MeanDirection", StringValue("ns3::UniformRandomVariable[Min=0|Max=6.283185307]"),
            "MeanPitch", StringValue("ns3::UniformRandomVariable[Min=-0.05|Max=0.05]"),
            "NormalVelocity", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.0|Bound=0.0]"),
            "NormalDirection", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.1|Bound=0.2]"),
            "NormalPitch", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.01|Bound=0.02]"));
        staMobilityHelper.Install(config.staNodes.Get(i));

        uint32_t nodeId = config.staNodes.Get(i)->GetId();
        std::cout << "Anchored STA spawn " << i << " at ("
                  << staPos.x << ", " << staPos.y << ", " << staPos.z
                  << ") [nodeId " << nodeId << "]" << std::endl;
        NS_LOG_INFO("  STA " << i << " (nodeId " << nodeId << ") initial position ("
                    << staPos.x << ", " << staPos.y << ", " << staPos.z << ")");
    }

    BuildingsHelper::Install(config.staNodes);

    NS_LOG_INFO("Hotspot infrastructure setup complete: " << meshCount
                << " AP nodes with " << numStaNodes << " STA clients on 192.168.1.0/24");
    return config;
}

// ============================================================================
// Function: Configure IP forwarding on gateway, router, and AP node
// ============================================================================
void ConfigureIPForwarding(NodeContainer meshNodes, NodeContainer internetNodes, uint32_t /*primaryApNodeIndex*/)
{
    NS_LOG_FUNCTION("Configuring IP forwarding");
    
    // Enable IP forwarding on all mesh nodes (each may host an AP)
    for (uint32_t i = 0; i < meshNodes.GetN(); ++i)
    {
        Ptr<Ipv4> ipv4Mesh = meshNodes.Get(i)->GetObject<Ipv4>();
        ipv4Mesh->SetAttribute("IpForward", BooleanValue(true));
    }

    // Enable IP forwarding on ISP router
    Ptr<Ipv4> ipv4Router = internetNodes.Get(0)->GetObject<Ipv4>();
    ipv4Router->SetAttribute("IpForward", BooleanValue(true));
    
    NS_LOG_INFO("IP forwarding enabled on all mesh nodes and the ISP router");
}

// ============================================================================
// Function: Configure static routing (ROBUST VERSION with dynamic interface lookup)
// ============================================================================
void ConfigureStaticRouting(const MeshNetworkConfig& meshConfig,
                            const InternetConfig& internetConfig,
                            const HotspotConfig& hotspotConfig,
                            uint32_t nNodes,
                            bool enableHotspot)
{
    NS_LOG_FUNCTION("Configuring static routing");
    
    Ipv4StaticRoutingHelper staticRouting;

    // --- Configure all mesh nodes ---
    for (uint32_t i = 0; i < nNodes; i++)
    {
        Ptr<Ipv4> ipv4 = meshConfig.meshNodes.Get(i)->GetObject<Ipv4>();
        Ptr<Ipv4StaticRouting> routing = staticRouting.GetStaticRouting(ipv4);
        
        if (i == 0)
        {
            // Gateway Node (Node 0) - route internet traffic via Ethernet
            Ipv4Address nextHopIp = internetConfig.backhaulInterfaces.GetAddress(1);
            Ptr<NetDevice> gatewayCsmaDevice = internetConfig.backhaulDevices.Get(0);
            uint32_t gatewayCsmaInterface = ipv4->GetInterfaceForDevice(gatewayCsmaDevice);
            
            NS_LOG_INFO("Gateway (Node 0) default route to " << nextHopIp 
                       << " via interface " << gatewayCsmaInterface);
            routing->SetDefaultRoute(nextHopIp, gatewayCsmaInterface);
            
            if (enableHotspot)
            {
                NS_LOG_INFO("Gateway host routes to STAs will be managed dynamically on association events");
            }
        }
        else
        {
            // Regular Mesh Nodes - route all traffic to Gateway (Node 0)
            Ipv4Address gatewayMeshIp = meshConfig.meshInterfaces.GetAddress(0);
            Ptr<NetDevice> nodeMeshDevice = meshConfig.meshDevices.Get(i);
            uint32_t nodeMeshInterface = ipv4->GetInterfaceForDevice(nodeMeshDevice);
            routing->SetDefaultRoute(gatewayMeshIp, nodeMeshInterface);
        }
    }
    
    // --- Configure the ISP Router ---
    Ptr<Ipv4> ipv4IspRouter = internetConfig.internetNodes.Get(0)->GetObject<Ipv4>();
    Ptr<Ipv4StaticRouting> ispRouting = staticRouting.GetStaticRouting(ipv4IspRouter);
    
    Ipv4Address gatewayBackhaulIp = internetConfig.backhaulInterfaces.GetAddress(0);
    Ptr<NetDevice> ispCsmaDevice = internetConfig.backhaulDevices.Get(1);
    uint32_t ispBackhaulInterface = ipv4IspRouter->GetInterfaceForDevice(ispCsmaDevice);
    
    ispRouting->AddNetworkRouteTo(Ipv4Address("10.1.1.0"),
                                  Ipv4Mask("255.255.255.0"),
                                  gatewayBackhaulIp,
                                  ispBackhaulInterface);
    
    if (enableHotspot)
    {
        ispRouting->AddNetworkRouteTo(Ipv4Address("192.168.1.0"),
                                      Ipv4Mask("255.255.255.0"),
                                      gatewayBackhaulIp,
                                      ispBackhaulInterface);
        NS_LOG_INFO("ISP Router route to hotspot network (192.168.1.0/24) via gateway backhaul IP "
                    << gatewayBackhaulIp);
    }
    
    // --- Configure the Internet Server ---
    Ptr<Ipv4> ipv4Server = internetConfig.internetNodes.Get(1)->GetObject<Ipv4>();
    Ptr<Ipv4StaticRouting> serverRouting = staticRouting.GetStaticRouting(ipv4Server);
    
    Ipv4Address ispRouterIp = internetConfig.internetInterfaces.GetAddress(0);
    Ptr<NetDevice> serverCsmaDevice = internetConfig.backboneDevices.Get(1);
    uint32_t serverInterface = ipv4Server->GetInterfaceForDevice(serverCsmaDevice);
    
    serverRouting->SetDefaultRoute(ispRouterIp, serverInterface);
    
    // --- Configure STA nodes (if hotspot enabled) ---
    NS_LOG_INFO("Static routing configured for all nodes");
}

// ============================================================================
// Function: Set up applications (web server and client)
// ============================================================================
void SetupApplications(const MeshNetworkConfig& meshConfig,
                      const InternetConfig& internetConfig,
                      const HotspotConfig& hotspotConfig,
                      double simTime,
                      bool enableHotspot,
                      uint32_t packetSize)
{
    NS_LOG_FUNCTION("Setting up applications");
    
    const uint16_t httpPort = 80;
    const uint16_t httpsPort = 443;
    const uint16_t videoPort = 8080;
    const uint16_t voipPort = 5060;
    const uint16_t dnsPort = 53;
    
    // Install servers on the internet node (remote host analogue)
    ApplicationContainer serverApps;
    PacketSinkHelper httpServer("ns3::TcpSocketFactory",
                                InetSocketAddress(Ipv4Address::GetAny(), httpPort));
    serverApps.Add(httpServer.Install(internetConfig.internetNodes.Get(1)));
    PacketSinkHelper httpsServer("ns3::TcpSocketFactory",
                                 InetSocketAddress(Ipv4Address::GetAny(), httpsPort));
    serverApps.Add(httpsServer.Install(internetConfig.internetNodes.Get(1)));
    PacketSinkHelper videoServer("ns3::TcpSocketFactory",
                                 InetSocketAddress(Ipv4Address::GetAny(), videoPort));
    serverApps.Add(videoServer.Install(internetConfig.internetNodes.Get(1)));
    UdpServerHelper voipServer(voipPort);
    serverApps.Add(voipServer.Install(internetConfig.internetNodes.Get(1)));
    UdpServerHelper dnsServer(dnsPort);
    serverApps.Add(dnsServer.Install(internetConfig.internetNodes.Get(1)));
    serverApps.Start(Seconds(0.5));
    serverApps.Stop(Seconds(simTime));
    
    if (!enableHotspot)
    {
        return;
    }
    
    const uint32_t smallTransferBytes = 1 * 1024 * 1024;   // 1 MB
    const uint32_t largeTransferBytes = 1 * 1024 * 1024;   // 1 MB

    Address remoteHttpAddress(InetSocketAddress(internetConfig.internetInterfaces.GetAddress(1), httpPort));
    Address remoteHttpsAddress(InetSocketAddress(internetConfig.internetInterfaces.GetAddress(1), httpsPort));
    Address remoteVideoAddress(InetSocketAddress(internetConfig.internetInterfaces.GetAddress(1), videoPort));
    Address remoteVoipAddress(InetSocketAddress(internetConfig.internetInterfaces.GetAddress(1), voipPort));
    
    ApplicationContainer clientApps;
    uint32_t staCount = hotspotConfig.staNodes.GetN();
    
    auto installTcpBulk = [&](uint32_t staIndex, Address remote, uint32_t maxBytes, double offset) {
        if (staIndex >= staCount)
        {
            return;
        }
        BulkSendHelper bulk("ns3::TcpSocketFactory", remote);
        bulk.SetAttribute("MaxBytes", UintegerValue(maxBytes));
        bulk.SetAttribute("SendSize", UintegerValue(packetSize));
        ApplicationContainer app = bulk.Install(hotspotConfig.staNodes.Get(staIndex));
        app.Start(Seconds(5.0 + offset));
        app.Stop(Seconds(30.0));
        clientApps.Add(app);
    };
    
    auto installUdpVoip = [&](uint32_t staIndex, double offset, uint32_t maxBytes) {
        if (staIndex >= staCount)
        {
            return;
        }
        OnOffHelper voipClient("ns3::UdpSocketFactory", remoteVoipAddress);
        voipClient.SetAttribute("DataRate", DataRateValue(DataRate("1.5Mbps")));
        voipClient.SetAttribute("PacketSize", UintegerValue(packetSize));
        voipClient.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1.0]"));
        voipClient.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0.0]"));
        voipClient.SetAttribute("MaxBytes", UintegerValue(maxBytes));
        ApplicationContainer app = voipClient.Install(hotspotConfig.staNodes.Get(staIndex));
        app.Start(Seconds(5.0 + offset));
        app.Stop(Seconds(30.0));
        clientApps.Add(app);
    };
    
    installTcpBulk(0, remoteHttpAddress, smallTransferBytes, 0.0);
    installTcpBulk(1, remoteHttpAddress, smallTransferBytes, 0.1);
    installTcpBulk(2, remoteHttpsAddress, largeTransferBytes, 0.2);
    installTcpBulk(3, remoteHttpsAddress, largeTransferBytes, 0.3);
    installTcpBulk(4, remoteVideoAddress, largeTransferBytes, 0.4);
    installTcpBulk(5, remoteVideoAddress, largeTransferBytes, 0.5);
    installTcpBulk(6, remoteHttpAddress, smallTransferBytes, 0.6);
    installUdpVoip(7, 0.7, smallTransferBytes);
    installTcpBulk(8, remoteHttpAddress, smallTransferBytes, 0.8);
    installTcpBulk(9, remoteHttpAddress, largeTransferBytes, 0.9);
    
    NS_LOG_INFO("Traffic profile aligned with NR/LTE playfield: HTTP/HTTPS/Video/VoIP/Mixed with 1400-byte segments");
}

// ============================================================================
// Function: Configure NetAnim
// ============================================================================
void ConfigureNetAnim(AnimationInterface& anim)
{
    NS_LOG_FUNCTION("Configuring NetAnim");
    
    anim.SetMaxPktsPerTraceFile(10000000);  // Increase packet limit to 10 million for large grids
    anim.EnablePacketMetadata(true);
    anim.EnableIpv4RouteTracking("wifi_test_research/six_node_layout/wifi-test-2-adhoc-grid-six-routes.xml",
                                 Seconds(0), Seconds(100), Seconds(1));
    anim.EnableWifiMacCounters(Seconds(0), Seconds(100));
    anim.EnableWifiPhyCounters(Seconds(0), Seconds(100));

    NS_LOG_INFO("NetAnim configured with packet metadata and route tracking");
}

// ============================================================================
// Function: Display simulation information
// ============================================================================
void DisplaySimulationInfo(uint32_t nNodes, 
                          uint32_t gridWidth, 
                          double simTime,
                          bool enableHotspot,
                          uint32_t apNodeIndex,
                          uint32_t numStaNodes)
{
    NS_LOG_UNCOND("=======================================================================");
    NS_LOG_UNCOND("Starting HWMP Mesh Simulation with Internet Gateway and Hotspot:");
    NS_LOG_UNCOND("=======================================================================");
    std::string layoutDescription;
    if (gridWidth > 0 && gridWidth * gridWidth == nNodes)
    {
        std::ostringstream oss;
        oss << gridWidth << "x" << gridWidth << " grid";
        layoutDescription = oss.str();
    }
    else
    {
        layoutDescription = "Custom layout";
    }

    NS_LOG_UNCOND("  Mesh Nodes: " << nNodes);
    NS_LOG_UNCOND("  Mesh Network: 10.1.1.0/24");
    NS_LOG_UNCOND("  Gateway: Node 0 -> Internet via 1Gbps Ethernet (192.168.100.1)");
    NS_LOG_UNCOND("  Internet Server: 8.8.8.2 (simulated external server)");
    if (enableHotspot)
    {
        NS_LOG_UNCOND("-----------------------------------------------------------------------");
        NS_LOG_UNCOND("  Hotspot Enabled:");
        NS_LOG_UNCOND("    AP Nodes: 0-" << (nNodes - 1) << ")");
        NS_LOG_UNCOND("    Hotspot Network: 192.168.1.0/24");
    NS_LOG_UNCOND("    STA Clients: " << numStaNodes);
        NS_LOG_UNCOND("    STA Mobility: GaussMarkov 3D (0.3-0.8 m/s, 400m x 400m, Z: 0-30m)");
        NS_LOG_UNCOND("    STA Traffic: STA -> Access AP -> Mesh -> Gateway -> Server");
    }
    else
    {
        NS_LOG_UNCOND("  Hotspot: DISABLED");
    }
    
    NS_LOG_UNCOND("-----------------------------------------------------------------------");
    NS_LOG_UNCOND("  Simulation time: " << simTime << "s");
    NS_LOG_UNCOND("=======================================================================");
}

// ============================================================================
// Function: Save FlowMonitor results and print statistics
// ============================================================================
void SaveFlowMonitorResults(Ptr<FlowMonitor> monitor, FlowMonitorHelper& flowmon)
{
    NS_LOG_FUNCTION("Saving FlowMonitor results");
    
    monitor->CheckForLostPackets();
    
    // Save to XML file
    monitor->SerializeToXmlFile("wifi_test_research/six_node_layout/wifi-test-2-adhoc-grid-six-flowmon.xml", true, true);
    
    // Print statistics to console
    Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(
        flowmon.GetClassifier());
    
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();
    
    NS_LOG_UNCOND("\n=======================================================================");
    NS_LOG_UNCOND("FLOWMONITOR STATISTICS");
    NS_LOG_UNCOND("=======================================================================");
    
    double totalTxBytes = 0;
    double totalRxBytes = 0;
    double totalTxPackets = 0;
    double totalRxPackets = 0;
    double totalLostPackets = 0;
    double totalDelay = 0;
    uint32_t flowCount = 0;
    
    for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin();
         i != stats.end(); ++i)
    {
        flowCount++;
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(i->first);
        
        NS_LOG_UNCOND("\n-----------------------------------------------------------------------");
        NS_LOG_UNCOND("Flow " << i->first << " (" << t.sourceAddress << ":" << t.sourcePort 
                      << " -> " << t.destinationAddress << ":" << t.destinationPort << ")");
        NS_LOG_UNCOND("-----------------------------------------------------------------------");
        NS_LOG_UNCOND("  Protocol: " << (uint32_t)t.protocol);
        NS_LOG_UNCOND("  Tx Packets: " << i->second.txPackets);
        NS_LOG_UNCOND("  Tx Bytes:   " << (i->second.txBytes / 1048576.0) << " MB");
        NS_LOG_UNCOND("  Rx Packets: " << i->second.rxPackets);
        NS_LOG_UNCOND("  Rx Bytes:   " << (i->second.rxBytes / 1048576.0) << " MB");
        NS_LOG_UNCOND("  Lost Packets: " << i->second.lostPackets 
                      << " (" << (i->second.txPackets > 0 ? 
                      (100.0 * i->second.lostPackets / i->second.txPackets) : 0) << "%)");
        
        if (i->second.rxPackets > 0)
        {
            double avgDelay = i->second.delaySum.GetSeconds() / i->second.rxPackets;
            double avgJitter = i->second.jitterSum.GetSeconds() / (i->second.rxPackets - 1);
            double throughput = i->second.rxBytes * 8.0 / 
                               (i->second.timeLastRxPacket.GetSeconds() - 
                                i->second.timeFirstTxPacket.GetSeconds()) / 1048576.0; // Mbps
            
            NS_LOG_UNCOND("  Throughput: " << throughput << " Mbps");
            NS_LOG_UNCOND("  Avg Delay:  " << (avgDelay * 1000.0) << " ms");
            NS_LOG_UNCOND("  Avg Jitter: " << (avgJitter * 1000.0) << " ms");
            
            totalDelay += avgDelay;
        }
        else
        {
             NS_LOG_UNCOND("  Throughput: 0 Mbps (no packets received)");
             NS_LOG_UNCOND("  Avg Delay:  N/A");
             NS_LOG_UNCOND("  Avg Jitter: N/A");
        }
        
        totalTxBytes += i->second.txBytes;
        totalRxBytes += i->second.rxBytes;
        totalTxPackets += i->second.txPackets;
        totalRxPackets += i->second.rxPackets;
        totalLostPackets += i->second.lostPackets;
    }
    
    NS_LOG_UNCOND("\n=======================================================================");
    NS_LOG_UNCOND("OVERALL STATISTICS");
    NS_LOG_UNCOND("=======================================================================");
    NS_LOG_UNCOND("  Total Flows: " << flowCount);
    NS_LOG_UNCOND("  Total Tx Packets: " << totalTxPackets);
    NS_LOG_UNCOND("  Total Rx Packets: " << totalRxPackets);
    NS_LOG_UNCOND("  Total Lost Packets: " << totalLostPackets 
                  << " (" << (totalTxPackets > 0 ? 
                  (100.0 * totalLostPackets / totalTxPackets) : 0) << "%)");
    NS_LOG_UNCOND("  Total Tx Bytes: " << (totalTxBytes / 1048576.0) << " MB");
    NS_LOG_UNCOND("  Total Rx Bytes: " << (totalRxBytes / 1048576.0) << " MB");
    if (flowCount > 0 && totalRxPackets > 0)
    {
        NS_LOG_UNCOND("  Average Delay: " << ((totalDelay / flowCount) * 1000.0) << " ms");
    }
    NS_LOG_UNCOND("=======================================================================\n");
    
    NS_LOG_INFO("FlowMonitor results saved to XML and printed to console");
}

// ============================================================================
// Function: Save configuration to JSON file for analysis scripts
// ============================================================================
void SaveConfigurationJSON(uint32_t nNodes, uint32_t gridWidth, uint32_t numStaNodes, 
                           uint32_t packetSize, double nodeSpacing, uint32_t meshConfig,
                           const std::string& outputDir = "wifi_test_research/six_node_layout")
{
    std::stringstream json;
    json << "{\n";
    json << "  \"network_topology\": {\n";
    json << "    \"num_nodes\": " << nNodes << ",\n";
    json << "    \"grid_width\": " << gridWidth << ",\n";
    json << "    \"node_spacing_meters\": " << nodeSpacing << "\n";
    json << "  },\n";
    json << "  \"traffic_configuration\": {\n";
    json << "    \"packet_size_bytes\": " << packetSize << ",\n";
    json << "    \"num_sta_nodes\": " << numStaNodes << "\n";
    json << "  },\n";
    json << "  \"mesh_configuration\": {\n";
    json << "    \"config_id\": " << meshConfig << "\n";
    json << "  },\n";
    json << "  \"ip_configuration\": {\n";
    json << "    \"source_ip\": \"192.168.1.2\",\n";
    json << "    \"destination_ip\": \"8.8.8.2\"\n";
    json << "  },\n";
    json << "  \"port_information\": {\n";
    json << "    \"tcp_port\": 80,\n";
    json << "    \"udp_port\": 9,\n";
    json << "    \"note\": \"UDP disabled - only TCP traffic generated\"\n";
    json << "  },\n";
    json << "  \"output_files\": {\n";
    json << "    \"xml_file\": \"" << outputDir << "/wifi-test-2-adhoc-grid-six.xml\",\n";
    json << "    \"tr_file\": \"" << outputDir << "/wifi-test-2-adhoc-grid-six.tr\",\n";
    json << "    \"sta_tr_file\": \"" << outputDir << "/wifi-test-2-sta-six.tr\",\n";
    json << "    \"flowmon_file\": \"" << outputDir << "/wifi-test-2-adhoc-grid-six-flowmon.xml\"\n";
    json << "  }\n";
    json << "}\n";
    
    std::string filename = outputDir + "/config_test_2.json";
    std::ofstream configFile(filename);
    if (configFile.is_open())
    {
        configFile << json.str();
        configFile.close();
        NS_LOG_INFO("Configuration saved to " << filename);
    }
    else
    {
        NS_LOG_WARN("Unable to save configuration to " << filename);
    }
}

// ============================================================================
// MAIN FUNCTION - Clean and modular
// ============================================================================
int main(int argc, char* argv[])
{
    // Enable packet metadata for NetAnim
    PacketMetadata::Enable();
    Packet::EnablePrinting();

    RngSeedManager::SetSeed(1);

    Config::SetDefault("ns3::TcpSocket::SndBufSize", UintegerValue(10 * 1024 * 1024));
    Config::SetDefault("ns3::TcpSocket::RcvBufSize", UintegerValue(10 * 1024 * 1024));
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(1400));
    Config::SetDefault("ns3::TcpSocket::InitialCwnd", UintegerValue(10));

    // ========================================================================
    // STEP 1: Parse Configuration Parameters
    // ========================================================================
    uint32_t nNodes = 6;           // Number of mesh nodes (custom six-node layout)
    uint32_t gridWidth = 0;        // Grid width (unused for custom layout)
    uint32_t packetSize = 1400;    // Packet size in bytes
    uint32_t maxPackets = 100;     // Maximum number of packets
    double interval = 1.0;         // Interval between packets (seconds)
    double nodeSpacing = 150.0;    // Approximate spacing used for fallback positioning (meters)
    uint32_t tcpPacketSize = 1400; // TCP packet size in bytes
    double tcpInterval = 5.0;      // TCP interval between packets (seconds)
    double simTime = 30.0;         // Simulation time (seconds)
    bool enableHotspot = true;     // Enable hotspot (AP + STA) feature
    uint32_t apNodeIndex = 5;      // Which mesh node acts as AP
    uint32_t numStaNodes = 10;     // Number of STA clients (all TCP)
    double meshApHeight = 1.5;     // Mesh AP height (meters) - for height optimization tests
    double staHeight = 5.0;        // STA node height (meters) - for vertical spacing tests
    uint32_t meshConfig = 1;       // Mesh AP device configuration (0=Default, 1=TP-Link EAP225, 2=Netgear Orbi 960, 3=Asus ZenWiFi XT8)

    CommandLine cmd;
    cmd.AddValue("nNodes", "Number of mesh nodes", nNodes);
    cmd.AddValue("gridWidth", "Grid width (for NxN grid)", gridWidth);
    cmd.AddValue("packetSize", "Size of application packet in bytes", packetSize);
    cmd.AddValue("maxPackets", "Maximum number of packets to send", maxPackets);
    cmd.AddValue("interval", "Interval between packets (seconds)", interval);
    cmd.AddValue("nodeSpacing", "Distance between adjacent nodes (meters)", nodeSpacing);
    cmd.AddValue("tcpPacketSize", "TCP packet size in bytes", tcpPacketSize);
    cmd.AddValue("tcpInterval", "TCP interval between packets (seconds)", tcpInterval);
    cmd.AddValue("simTime", "Simulation time (seconds)", simTime);
    cmd.AddValue("enableHotspot", "Enable hotspot (AP + STA) feature", enableHotspot);
    cmd.AddValue("apNodeIndex", "Which mesh node acts as AP (0-5)", apNodeIndex);
    cmd.AddValue("numStaNodes", "Number of STA clients", numStaNodes);
    cmd.AddValue("meshApHeight", "Mesh AP height in meters (1.5, 10, 15)", meshApHeight);
    cmd.AddValue("staHeight", "STA node height in meters (0-30)", staHeight);
    cmd.AddValue("meshConfig", "Mesh AP device (0=Default 802.11g, 1=TP-Link EAP225, 2=Netgear Orbi 960, 3=Asus ZenWiFi XT8)", meshConfig);
    cmd.Parse(argc, argv);
    
    // Validate mesh config
    if (meshConfig > 3) {
        NS_LOG_WARN("Invalid meshConfig value " << meshConfig << ", using default (0)");
        meshConfig = 0;
    }
    
    // Get selected mesh device configuration
    MeshAPDeviceConfig deviceCfg = GetMeshDeviceConfig(meshConfig);
    
    // ========================================================================
    // Custom six-node mesh topology (positions defined in GetSixNodeMeshPositions)
    // ========================================================================
    const std::vector<Vector> layoutPositions = GetSixNodeMeshPositions(meshApHeight);
    if (nNodes != layoutPositions.size())
    {
        NS_LOG_WARN("Overriding nNodes (" << nNodes << ") to match six-node layout ("
                     << layoutPositions.size() << ")");
        nNodes = layoutPositions.size();
    }

    gridWidth = 0;  // indicates custom layout for logging purposes

    double minX = layoutPositions.empty() ? 0.0 : layoutPositions.front().x;
    double maxX = minX;
    double minY = layoutPositions.empty() ? 0.0 : layoutPositions.front().y;
    double maxY = minY;

    for (const auto& pos : layoutPositions)
    {
        minX = std::min(minX, pos.x);
        maxX = std::max(maxX, pos.x);
        minY = std::min(minY, pos.y);
        maxY = std::max(maxY, pos.y);
    }

    double actualCoverageX = maxX - minX;
    double actualCoverageY = maxY - minY;

    // Update AP node index (last node in layout)
    apNodeIndex = nNodes > 0 ? nNodes - 1 : 0;
    
    NS_LOG_UNCOND("=======================================================================");
    NS_LOG_UNCOND("Mesh AP Device Configuration:");
    NS_LOG_UNCOND("=======================================================================");
    NS_LOG_UNCOND("  Device: " << deviceCfg.name);
    NS_LOG_UNCOND("  Description: " << deviceCfg.description);
    NS_LOG_UNCOND("  WiFi Standard: " << deviceCfg.wifiStandard);
    NS_LOG_UNCOND("  Data Mode: " << deviceCfg.dataMode);
    NS_LOG_UNCOND("  TX Power (Mesh Backhaul): " << deviceCfg.txPowerStart << " dBm");
    NS_LOG_UNCOND("  TX Power (Hotspot/AP): " << deviceCfg.hotspotTxPower << " dBm");
    NS_LOG_UNCOND("  RX Sensitivity: " << deviceCfg.rxSensitivity << " dBm");
    NS_LOG_UNCOND("  Antenna Gain (RX/TX): " << deviceCfg.rxGain << "/" << deviceCfg.txGain << " dB");
    NS_LOG_UNCOND("  Number of Interfaces: " << deviceCfg.numInterfaces);
    NS_LOG_UNCOND("=======================================================================\n");

    // ========================================================================
    // STEP 2: Set Up Mesh Network
    // ========================================================================
    MeshNetworkConfig meshNetConfig = SetupMeshNetwork(nNodes, gridWidth, nodeSpacing, meshApHeight, deviceCfg);

    // ========================================================================
    // STEP 3: Set Up Internet Infrastructure
    // ========================================================================
    InternetConfig internetConfig = SetupInternetInfrastructure(meshNetConfig.meshNodes, nodeSpacing, meshApHeight);

    // ========================================================================
    // STEP 4: Set Up Hotspot Infrastructure (if enabled)
    // ========================================================================
    HotspotConfig hotspotConfig;
    if (enableHotspot)
    {
        hotspotConfig = SetupHotspotInfrastructure(meshNetConfig.meshNodes, 
                                                    apNodeIndex, 
                                                    numStaNodes, 
                                                    nodeSpacing,
                                                    staHeight,
                                                    deviceCfg);  // Pass device config for hotspot TX power
    }

    // ========================================================================
    // STEP 5: Configure IP Forwarding
    // ========================================================================
    ConfigureIPForwarding(meshNetConfig.meshNodes, internetConfig.internetNodes, apNodeIndex);

    // ========================================================================
    // STEP 6: Configure Static Routing
    // ========================================================================
    ConfigureStaticRouting(meshNetConfig, internetConfig, hotspotConfig, nNodes, enableHotspot);

    // ========================================================================
    // STEP 7.5: Enable STA roaming callbacks (association-driven routing updates)
    // ========================================================================
    EnableStaRoamingTracing(meshNetConfig, hotspotConfig, enableHotspot);

    // ========================================================================
    // STEP 7: Set Up Applications
    // ========================================================================
    SetupApplications(meshNetConfig, internetConfig, hotspotConfig, simTime, enableHotspot, packetSize);

    // ========================================================================
    // STEP 8: Configure NetAnim and FlowMonitor
    // ========================================================================
    AnimationInterface anim("wifi_test_research/six_node_layout/wifi-test-2-adhoc-grid-six.xml");
    ConfigureNetAnim(anim);
    
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.InstallAll();

    // ========================================================================
    // STEP 9: Display Info and Run Simulation
    // ========================================================================
    DisplaySimulationInfo(nNodes, gridWidth, simTime, enableHotspot, apNodeIndex, numStaNodes);
    
    // Save configuration JSON for analysis scripts
    SaveConfigurationJSON(nNodes, gridWidth, numStaNodes, packetSize, nodeSpacing, meshConfig);
    
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    // ========================================================================
    // STEP 10: Save Results and Cleanup
    // ========================================================================
    SaveFlowMonitorResults(monitor, flowmon);

    if (enableHotspot)
    {
        std::cout << "\nFinal STA -> AP associations\n";
        std::cout << "----------------------------------------\n";
        for (uint32_t i = 0; i < hotspotConfig.currentStaApIndex.size(); ++i)
        {
            uint32_t apIdx = hotspotConfig.currentStaApIndex[i];
            Ipv4Address staIp = hotspotConfig.staInterfaces.GetAddress(i);
            if (apIdx != std::numeric_limits<uint32_t>::max())
            {
                std::cout << "STA " << i << " (" << staIp << ") attached to mesh node "
                          << apIdx << " (AP BSSID ";
                bool printed = false;
                for (const auto& entry : hotspotConfig.apBssidToMeshIndex)
                {
                    if (entry.second == apIdx)
                    {
                        std::cout << entry.first;
                        printed = true;
                        break;
                    }
                }
                if (!printed)
                {
                    std::cout << "unknown";
                }
                std::cout << ")\n";
            }
            else
            {
                std::cout << "STA " << i << " (" << staIp << ") no active association\n";
            }
        }
        std::cout << "----------------------------------------\n\n";
    }

    Simulator::Destroy();

    std::ostringstream parseCmd;
    parseCmd << "cd /home/sayed/pic_lab_project/ns3_project_for_kit && "
             << "python3 wifi_test_research/parse_flowmon_xml.py "
             << "wifi_test_research/six_node_layout/wifi-test-2-adhoc-grid-six-flowmon.xml"
             << " --sim-time=" << simTime
             << " --md wifi_test_research/six_node_layout/wifi-test-2-adhoc-grid-six-metrics.md";

    std::cout << "Running FlowMonitor parser..." << std::endl;
    int parseStatus = std::system(parseCmd.str().c_str());
    if (parseStatus != 0)
    {
        std::cerr << "FlowMonitor parser exited with status " << parseStatus << std::endl;
    }

    return 0;
}

