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
#include <cmath>
#include <fstream>
#include <sstream>

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
                "Verified specs (802.11n mesh @ 2.4GHz, shared band)",
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
                120.0                           // meshRange (m) - Premium device = longer range
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
                100.0                           // meshRange (m) - Standard range
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
                250.0                           // meshRange (m) - current 250m spacing
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
    Ipv4InterfaceContainer hotspotInterfaces;
    uint32_t apNodeIndex;  // Which mesh node acts as AP (e.g., Node 8)
};

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
    config.wifiPhy.EnableAsciiAll(ascii.CreateFileStream("wifi_test_research/wifi-test-2-adhoc-grid.tr"));

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

    // Set up mobility model (grid)
    MobilityHelper mobility;
    mobility.SetPositionAllocator("ns3::GridPositionAllocator",
                                  "MinX", DoubleValue(0.0),
                                  "MinY", DoubleValue(0.0),
                                  "DeltaX", DoubleValue(nodeSpacing),
                                  "DeltaY", DoubleValue(nodeSpacing),
                                  "GridWidth", UintegerValue(gridWidth),
                                  "LayoutType", StringValue("RowFirst"),
                                  "Z", DoubleValue(meshApHeight));  // Mesh AP height (configurable)
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(config.meshNodes);
    
    // *** ENABLE ALL 4 BUILDINGS FOR TESTING ***
    double buildingHeight = 15.0;   // 15 meters tall buildings
    
    // Strategic placement: Block direct paths between mesh nodes to force multi-hop routing
    // Grid layout:  0 - 1 - 2
    //               3 - 4 - 5
    //               6 - 7 - 8
    
    // ADAPTIVE BUILDING POSITIONING - works with any node spacing
    // Buildings sized at 30% of node spacing, offset by 35% from grid lines
    // This ensures buildings occupy 35%-65% of each grid cell
    // Nodes are at 0%, 100%, 200% - safely away from buildings
    double buildingSize = nodeSpacing * 0.3;      // 30% of spacing
    double buildingOffset = nodeSpacing * 0.35;   // 35% from grid line
    
    // Building 1: Between Node 0 and Node 4 (blocks diagonal)
    // Positioned at 35%-65% of first grid cell
    Ptr<Building> building1 = CreateObject<Building>();
    building1->SetBoundaries(Box(buildingOffset, buildingOffset + buildingSize,
                                 buildingOffset, buildingOffset + buildingSize,
                                 0.0, buildingHeight));
    building1->SetBuildingType(Building::Office);
    building1->SetExtWallsType(Building::ConcreteWithWindows);
    building1->SetNFloors(3);
    building1->SetNRoomsX(5);
    building1->SetNRoomsY(4);
    
    // Building 2: Between Node 4 and Node 8 (blocks diagonal)
    // Positioned at 135%-165% of grid (in second grid cell)
    Ptr<Building> building2 = CreateObject<Building>();
    building2->SetBoundaries(Box(nodeSpacing + buildingOffset, nodeSpacing + buildingOffset + buildingSize,
                                 nodeSpacing + buildingOffset, nodeSpacing + buildingOffset + buildingSize,
                                 0.0, buildingHeight));
    building2->SetBuildingType(Building::Commercial);
    building2->SetExtWallsType(Building::ConcreteWithWindows);
    building2->SetNFloors(3);
    building2->SetNRoomsX(6);
    building2->SetNRoomsY(5);
    
    // Building 3: In grid cell (1,0) - between nodes 1,2,4,5
    // Positioned at 135%-165% X, 35%-65% Y (different grid cell gap)
    Ptr<Building> building3 = CreateObject<Building>();
    building3->SetBoundaries(Box(nodeSpacing + buildingOffset, nodeSpacing + buildingOffset + buildingSize,
                                 buildingOffset, buildingOffset + buildingSize,
                                 0.0, buildingHeight));
    building3->SetBuildingType(Building::Office);
    building3->SetExtWallsType(Building::ConcreteWithWindows);
    building3->SetNFloors(3);
    building3->SetNRoomsX(4);
    building3->SetNRoomsY(3);
    
    // Building 4: In grid cell (0,1) - between nodes 3,4,6,7
    // Positioned at 35%-65% X, 135%-165% Y (different grid cell gap)
    Ptr<Building> building4 = CreateObject<Building>();
    building4->SetBoundaries(Box(buildingOffset, buildingOffset + buildingSize,
                                 nodeSpacing + buildingOffset, nodeSpacing + buildingOffset + buildingSize,
                                 0.0, buildingHeight));
    building4->SetBuildingType(Building::Commercial);
    building4->SetExtWallsType(Building::ConcreteWithWindows);
    building4->SetNFloors(3);
    building4->SetNRoomsX(3);
    building4->SetNRoomsY(5);
    
    // Aggregate building information to all mesh nodes
    BuildingsHelper::Install(config.meshNodes);
    
    NS_LOG_INFO("Mesh network setup complete with ALL 4 ADAPTIVE buildings");
    NS_LOG_INFO("  Building 1-4: ConcreteWithWindows, 15m tall");
    NS_LOG_INFO("  Node spacing: " << nodeSpacing << "m, Building size: " << buildingSize << "m");
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
                                          uint32_t apNodeIndex,
                                          uint32_t numStaNodes,
                                          double nodeSpacing,
                                          double staHeight,
                                          const MeshAPDeviceConfig& deviceCfg)
{
    NS_LOG_FUNCTION("Setting up hotspot infrastructure with " << numStaNodes << " STA clients");
    NS_LOG_INFO("Using hotspot TX power: " << deviceCfg.hotspotTxPower << " dBm from device config");
    
    HotspotConfig config;
    config.apNodeIndex = apNodeIndex;
    
    // Create STA nodes
    config.staNodes.Create(numStaNodes);
    
    // Install Internet stack on STA nodes
    InternetStackHelper internetStack;
    internetStack.Install(config.staNodes);
    
    // Set up separate WiFi channel for AP/STA (802.11ac hotspot)
    WifiHelper hotspotWifi;
    hotspotWifi.SetStandard(WIFI_STANDARD_80211ac);
    
    YansWifiChannelHelper hotspotChannel;
    hotspotChannel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    
    // Use ONLY HybridBuildingsPropagationLossModel (includes distance loss internally)
    // NO extra arguments - use default parameters
    hotspotChannel.AddPropagationLoss("ns3::HybridBuildingsPropagationLossModel");
    
    YansWifiPhyHelper hotspotPhy;
    
    // Set hotspot Tx power from device configuration (separate from mesh backhaul)
    hotspotPhy.Set("TxPowerStart", DoubleValue(deviceCfg.hotspotTxPower));
    hotspotPhy.Set("TxPowerEnd", DoubleValue(deviceCfg.hotspotTxPower));
    
    hotspotPhy.SetChannel(hotspotChannel.Create());
    
    // Enable ASCII tracing *before* installing devices
    AsciiTraceHelper ascii;
    hotspotPhy.EnableAsciiAll(ascii.CreateFileStream("wifi_test_research/wifi-test-2-sta.tr"));
    
    // Configure WiFi MAC for AP and STA
    Ssid ssid = Ssid("Node" + std::to_string(apNodeIndex) + "-Hotspot");
    WifiMacHelper hotspotMac;
    
    // Install AP device on the designated mesh node (e.g., Node 8)
    hotspotMac.SetType("ns3::ApWifiMac",
                       "Ssid", SsidValue(ssid),
                       "BeaconGeneration", BooleanValue(true),
                       "BeaconInterval", TimeValue(MicroSeconds(102400)));
    config.apDevices = hotspotWifi.Install(hotspotPhy, hotspotMac, meshNodes.Get(apNodeIndex));
    
    // Install STA devices on mobile clients
    hotspotMac.SetType("ns3::StaWifiMac",
                       "Ssid", SsidValue(ssid),
                       "ActiveProbing", BooleanValue(false));
    config.staDevices = hotspotWifi.Install(hotspotPhy, hotspotMac, config.staNodes);
    
    // Assign IP addresses to hotspot network (192.168.2.0/24)
    Ipv4AddressHelper hotspotAddress;
    hotspotAddress.SetBase("192.168.2.0", "255.255.255.0");
    
    // Combine AP and STA devices for IP assignment
    NetDeviceContainer hotspotDevices;
    hotspotDevices.Add(config.apDevices);
    hotspotDevices.Add(config.staDevices);
    config.hotspotInterfaces = hotspotAddress.Assign(hotspotDevices);
    
    // Get AP node position for centering STA mobility area
    Ptr<ConstantPositionMobilityModel> apMobility = 
        meshNodes.Get(apNodeIndex)->GetObject<ConstantPositionMobilityModel>();
    Vector apPosition = apMobility->GetPosition();
    
    // Set up mobile STA nodes with GaussMarkov 3D mobility
    // 20m x 20m area centered on AP position, 3D movement (0-30m height)
    
    // Define movement bounds (20m x 20m area, 0-30m height)
    double movementRadius = 10.0;  // 10m radius = 20m x 20m area
    double minX = apPosition.x - movementRadius;
    double maxX = apPosition.x + movementRadius;
    double minY = apPosition.y - movementRadius;
    double maxY = apPosition.y + movementRadius;
    double minZ = 0.0;
    double maxZ = 30.0;
    
    // Set up GaussMarkov mobility for each STA individually
    for (uint32_t i = 0; i < config.staNodes.GetN(); i++)
    {
        // Random initial position within bounds
        double initX = apPosition.x + (rand() % 20 - 10);  // ±10m from AP
        double initY = apPosition.y + (rand() % 20 - 10);
        double initZ = staHeight + (rand() % 10);  // Start near staHeight parameter
        
        MobilityHelper staMobility;
        Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
        posAlloc->Add(Vector(initX, initY, initZ));
        
        staMobility.SetPositionAllocator(posAlloc);
        staMobility.SetMobilityModel("ns3::GaussMarkovMobilityModel",
            "Bounds", BoxValue(Box(minX, maxX, minY, maxY, minZ, maxZ)),
            "TimeStep", TimeValue(Seconds(1.0)),
            "Alpha", DoubleValue(0.85),  // 85% memory - smooth, correlated movement
            "MeanVelocity", StringValue("ns3::UniformRandomVariable[Min=0.3|Max=0.8]"),  // Pedestrian speed
            "MeanDirection", StringValue("ns3::UniformRandomVariable[Min=0|Max=6.283185307]"),  // 0-2π radians
            "MeanPitch", StringValue("ns3::UniformRandomVariable[Min=-0.05|Max=0.05]"),  // Slight vertical angle
            "NormalVelocity", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.0|Bound=0.0]"),
            "NormalDirection", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.1|Bound=0.2]"),
            "NormalPitch", StringValue("ns3::NormalRandomVariable[Mean=0.0|Variance=0.01|Bound=0.02]"));
        
        staMobility.Install(config.staNodes.Get(i));
        
        NS_LOG_INFO("  STA " << i << " initial position: (" << initX << ", " << initY << ", " << initZ << ")");
    }
    
    NS_LOG_INFO("STA nodes configured with GaussMarkov 3D mobility (0.3-0.8 m/s, 20m x 20m area, 0-30m height)");
    NS_LOG_INFO("  Movement centered around AP Node " << apNodeIndex << " at (" << apPosition.x << ", " << apPosition.y << ")");
    
    // Aggregate building information to STA nodes
    BuildingsHelper::Install(config.staNodes);
    
    NS_LOG_INFO("Hotspot infrastructure setup complete: AP on Node " << apNodeIndex << 
                ", " << numStaNodes << " STA clients on 192.168.2.0/24");
    return config;
}

// ============================================================================
// Function: Configure IP forwarding on gateway, router, and AP node
// ============================================================================
void ConfigureIPForwarding(NodeContainer meshNodes, NodeContainer internetNodes, uint32_t apNodeIndex)
{
    NS_LOG_FUNCTION("Configuring IP forwarding");
    
    // Enable IP forwarding on node 0 (gateway)
    Ptr<Ipv4> ipv4Node0 = meshNodes.Get(0)->GetObject<Ipv4>();
    ipv4Node0->SetAttribute("IpForward", BooleanValue(true));

    // Enable IP forwarding on ISP router
    Ptr<Ipv4> ipv4Router = internetNodes.Get(0)->GetObject<Ipv4>();
    ipv4Router->SetAttribute("IpForward", BooleanValue(true));

    // Enable IP forwarding on AP node (e.g., Node 8) - acts as router for STA clients
    Ptr<Ipv4> ipv4ApNode = meshNodes.Get(apNodeIndex)->GetObject<Ipv4>();
    ipv4ApNode->SetAttribute("IpForward", BooleanValue(true));
    
    NS_LOG_INFO("IP forwarding enabled on gateway, ISP router, and AP node " << apNodeIndex);
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
            
            NS_LOG_INFO("Gateway (Node 0) default route to " << nextHopIp << 
                       " via interface " << gatewayCsmaInterface);
            routing->SetDefaultRoute(nextHopIp, gatewayCsmaInterface);
            
            // If hotspot enabled, add route to hotspot network via AP node's mesh IP
            if (enableHotspot)
            {
                Ipv4Address apMeshIp = meshConfig.meshInterfaces.GetAddress(hotspotConfig.apNodeIndex);
                Ptr<NetDevice> gatewayMeshDevice = meshConfig.meshDevices.Get(0);
                uint32_t gatewayMeshInterface = ipv4->GetInterfaceForDevice(gatewayMeshDevice);
                
                routing->AddNetworkRouteTo(Ipv4Address("192.168.2.0"),
                                          Ipv4Mask("255.255.255.0"),
                                          apMeshIp,
                                          gatewayMeshInterface);
                
                NS_LOG_INFO("Gateway (Node 0) route to hotspot network (192.168.2.0/24) via Node " << 
                           hotspotConfig.apNodeIndex << " mesh IP " << apMeshIp);
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
    
    // If hotspot enabled, add route to hotspot network via gateway's backhaul IP
    if (enableHotspot)
    {
        ispRouting->AddNetworkRouteTo(Ipv4Address("192.168.2.0"),
                                      Ipv4Mask("255.255.255.0"),
                                      gatewayBackhaulIp,
                                      ispBackhaulInterface);
        
        NS_LOG_INFO("ISP Router route to hotspot network (192.168.2.0/24) via gateway backhaul IP " << 
                   gatewayBackhaulIp);
    }
    
    // --- Configure the Internet Server ---
    Ptr<Ipv4> ipv4Server = internetConfig.internetNodes.Get(1)->GetObject<Ipv4>();
    Ptr<Ipv4StaticRouting> serverRouting = staticRouting.GetStaticRouting(ipv4Server);
    
    Ipv4Address ispRouterIp = internetConfig.internetInterfaces.GetAddress(0);
    Ptr<NetDevice> serverCsmaDevice = internetConfig.backboneDevices.Get(1);
    uint32_t serverInterface = ipv4Server->GetInterfaceForDevice(serverCsmaDevice);
    
    serverRouting->SetDefaultRoute(ispRouterIp, serverInterface);
    
    // --- Configure STA nodes (if hotspot enabled) ---
    if (enableHotspot)
    {
        for (uint32_t i = 0; i < hotspotConfig.staNodes.GetN(); i++)
        {
            Ptr<Ipv4> ipv4Sta = hotspotConfig.staNodes.Get(i)->GetObject<Ipv4>();
            Ptr<Ipv4StaticRouting> staRouting = staticRouting.GetStaticRouting(ipv4Sta);
            
            // STA default route to AP node's hotspot IP (192.168.2.1)
            Ipv4Address apHotspotIp = hotspotConfig.hotspotInterfaces.GetAddress(0);
            Ptr<NetDevice> staDevice = hotspotConfig.staDevices.Get(i);
            uint32_t staInterface = ipv4Sta->GetInterfaceForDevice(staDevice);
            
            staRouting->SetDefaultRoute(apHotspotIp, staInterface);
            
            NS_LOG_INFO("STA " << i << " default route to AP hotspot IP " << apHotspotIp);
        }
    }
    
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
                      uint32_t meshClientNodeIndex,
                      uint32_t packetSize)
{
    NS_LOG_FUNCTION("Setting up applications");
    
    uint16_t webPort = 80;
    uint16_t udpPort = 9;
    
    // Set up Internet TCP web server (simulating external server like Google)
    PacketSinkHelper webServer("ns3::TcpSocketFactory", 
                               InetSocketAddress(Ipv4Address::GetAny(), webPort));
    ApplicationContainer webServerApp = webServer.Install(internetConfig.internetNodes.Get(1));
    webServerApp.Start(Seconds(1.0));
    webServerApp.Stop(Seconds(simTime));
    
    // Set up Internet UDP server
    PacketSinkHelper udpServer("ns3::UdpSocketFactory", 
                               InetSocketAddress(Ipv4Address::GetAny(), udpPort));
    ApplicationContainer udpServerApp = udpServer.Install(internetConfig.internetNodes.Get(1));
    udpServerApp.Start(Seconds(1.0));
    udpServerApp.Stop(Seconds(simTime));

    // Set up web client on mesh node to access internet server
    Address webServerAddress(InetSocketAddress(internetConfig.internetInterfaces.GetAddress(1), webPort));
    OnOffHelper webClient("ns3::TcpSocketFactory", webServerAddress);
    webClient.SetAttribute("PacketSize", UintegerValue(packetSize));
    webClient.SetAttribute("DataRate", StringValue("1Mbps"));
    webClient.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=2]"));
    webClient.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    ApplicationContainer webClientApp = webClient.Install(meshConfig.meshNodes.Get(meshClientNodeIndex));
    webClientApp.Start(Seconds(5.0));
    webClientApp.Stop(Seconds(30.0));
    
    NS_LOG_INFO("Applications configured: Server on internet node, Client on mesh node " << meshClientNodeIndex);
    
    // Set up web clients on STA nodes (if hotspot enabled)
    // Pattern: TCP ONLY (UDP disabled due to OnTime < transmission time for 1MB packets)
    if (enableHotspot)
    {
        for (uint32_t i = 0; i < hotspotConfig.staNodes.GetN(); i++)
        {
            double startTime = 6.0 + i * 0.5;  // Stagger start times by 0.5s
            
            // TCP client for all STA nodes
            OnOffHelper staWebClient("ns3::TcpSocketFactory", webServerAddress);
            staWebClient.SetAttribute("PacketSize", UintegerValue(packetSize));
            staWebClient.SetAttribute("DataRate", StringValue("1Mbps"));
            staWebClient.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=2]"));
            staWebClient.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
            
            ApplicationContainer staClientApp = staWebClient.Install(hotspotConfig.staNodes.Get(i));
            staClientApp.Start(Seconds(startTime));
            staClientApp.Stop(Seconds(30.0));
            
            NS_LOG_INFO("STA " << i << " (TCP) web client configured to access internet server via AP Node " << 
                       hotspotConfig.apNodeIndex << " at " << startTime << "s");
        }
    }
}

// ============================================================================
// Function: Configure NetAnim
// ============================================================================
void ConfigureNetAnim(AnimationInterface& anim)
{
    NS_LOG_FUNCTION("Configuring NetAnim");
    
    anim.SetMaxPktsPerTraceFile(10000000);  // Increase packet limit to 10 million for large grids
    anim.EnablePacketMetadata(true);
    anim.EnableIpv4RouteTracking("wifi_test_research/wifi-test-2-adhoc-grid-routes.xml",
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
                          uint32_t numStaNodes,
                          uint32_t meshClientNodeIndex)
{
    NS_LOG_UNCOND("=======================================================================");
    NS_LOG_UNCOND("Starting HWMP Mesh Simulation with Internet Gateway and Hotspot:");
    NS_LOG_UNCOND("=======================================================================");
    NS_LOG_UNCOND("  Mesh Nodes: " << nNodes << " (" << gridWidth << "x" << gridWidth << " grid)");
    NS_LOG_UNCOND("  Mesh Network: 10.1.1.0/24");
    NS_LOG_UNCOND("  Gateway: Node 0 -> Internet via 1Gbps Ethernet (192.168.100.1)");
    NS_LOG_UNCOND("  Internet Server: 8.8.8.2 (simulated external server)");
    NS_LOG_UNCOND("  Mesh Traffic: Node " << meshClientNodeIndex << " -> Server 8.8.8.2 (port 80)");
    
    if (enableHotspot)
    {
        NS_LOG_UNCOND("-----------------------------------------------------------------------");
        NS_LOG_UNCOND("  Hotspot Enabled:");
        NS_LOG_UNCOND("    AP Node: Node " << apNodeIndex << " (hybrid mesh + AP)");
        NS_LOG_UNCOND("    Hotspot Network: 192.168.2.0/24");
        NS_LOG_UNCOND("    STA Clients: " << numStaNodes);
        NS_LOG_UNCOND("    STA Mobility: GaussMarkov 3D (0.3-0.8 m/s, 20m x 20m, Z: 0-30m)");
        NS_LOG_UNCOND("    STA Traffic: STA -> Server 8.8.8.2 via AP -> Mesh -> Gateway");
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
    monitor->SerializeToXmlFile("wifi_test_research/wifi-test-2-adhoc-grid-flowmon.xml", true, true);
    
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
                           const std::string& outputDir = "wifi_test_research")
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
    json << "    \"source_ip\": \"192.168.2.2\",\n";
    json << "    \"destination_ip\": \"8.8.8.2\"\n";
    json << "  },\n";
    json << "  \"port_information\": {\n";
    json << "    \"tcp_port\": 80,\n";
    json << "    \"udp_port\": 9,\n";
    json << "    \"note\": \"UDP disabled - only TCP traffic generated\"\n";
    json << "  },\n";
    json << "  \"output_files\": {\n";
    json << "    \"xml_file\": \"" << outputDir << "/wifi-test-2-adhoc-grid.xml\",\n";
    json << "    \"tr_file\": \"" << outputDir << "/wifi-test-2-adhoc-grid.tr\",\n";
    json << "    \"sta_tr_file\": \"" << outputDir << "/wifi-test-2-sta.tr\",\n";
    json << "    \"flowmon_file\": \"" << outputDir << "/wifi-test-2-adhoc-grid-flowmon.xml\"\n";
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
    Packet::EnablePrinting();
    Packet::EnableChecking();

    // ========================================================================
    // STEP 1: Parse Configuration Parameters
    // ========================================================================
    uint32_t nNodes = 9;           // Number of nodes (3x3 grid)
    uint32_t gridWidth = 3;        // Grid width
    uint32_t packetSize = 1024;    // Packet size in bytes
    uint32_t maxPackets = 100;     // Maximum number of packets
    double interval = 1.0;         // Interval between packets (seconds)
    double nodeSpacing = 250.0;    // Distance between nodes (meters) - OPTIMAL for HybridBuildings
    uint32_t tcpPacketSize = 1024; // TCP packet size in bytes
    double tcpInterval = 5.0;      // TCP interval between packets (seconds)
    double simTime = 35.0;         // Simulation time (seconds)
    bool enableHotspot = true;     // Enable hotspot (AP + STA) feature
    uint32_t apNodeIndex = 8;      // Which mesh node acts as AP
    uint32_t numStaNodes = 2;      // Number of STA clients (all TCP)
    double meshApHeight = 1.5;     // Mesh AP height (meters) - for height optimization tests
    double staHeight = 5.0;        // STA node height (meters) - for vertical spacing tests
    uint32_t meshConfig = 0;       // Mesh AP device configuration (0=default, 1=TP-Link, 2=Orbi, 3=ZenWiFi)

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
    cmd.AddValue("apNodeIndex", "Which mesh node acts as AP (0-8)", apNodeIndex);
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
    // FIXED Network Topology for Consistent Coverage
    // Target: 400m × 400m × 30m coverage with 9 APs (3×3 grid)
    // ========================================================================
    
    // Fixed node spacing for consistent 400m × 400m coverage across all configs
    nodeSpacing = 200.0;  // All configs use 200m spacing
    
    // Use constant 3×3 grid for all configurations
    // Config 1 (300m range): 3×3 grid with 200m spacing → 400m coverage (67% of range) ✅
    // Config 2 (120m range): 3×3 grid with 200m spacing → 400m coverage (167% of range) ⚠️
    // Config 3 (100m range): 3×3 grid with 200m spacing → 400m coverage (200% of range) ⚠️
    gridWidth = 3;  // Fixed 3×3 grid for all configs
    
    // Calculate total nodes
    nNodes = gridWidth * gridWidth;
    
    // Calculate actual coverage achieved
    double actualCoverageX = (gridWidth - 1) * nodeSpacing;
    double actualCoverageY = (gridWidth - 1) * nodeSpacing;
    
    // Update AP node index (last node - bottom-right corner)
    apNodeIndex = nNodes - 1;
    
    // Update mesh client node index (second to last or node before corner)
    uint32_t meshClientNodeIndex = nNodes - 2;
    
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
    NS_LOG_UNCOND("  Expected Range: " << deviceCfg.meshRange << " meters");
    NS_LOG_UNCOND("=======================================================================");
    NS_LOG_UNCOND("Auto-Calculated Network Topology:");
    NS_LOG_UNCOND("=======================================================================");
    NS_LOG_UNCOND("  Node Spacing: " << nodeSpacing << "m (80% of " << deviceCfg.meshRange << "m range)");
    NS_LOG_UNCOND("  Grid Size: " << gridWidth << "×" << gridWidth);
    NS_LOG_UNCOND("  Total Mesh Nodes: " << nNodes << " APs");
    NS_LOG_UNCOND("  Coverage Area: " << actualCoverageX << "m × " << actualCoverageY << "m");
    NS_LOG_UNCOND("  Vertical Range: 0-30m (Buildings at 15m height)");
    NS_LOG_UNCOND("  AP Node: Node " << apNodeIndex << " (bottom-right corner)");
    NS_LOG_UNCOND("  Mesh Client: Node " << meshClientNodeIndex);
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
    // STEP 7: Set Up Applications
    // ========================================================================
    SetupApplications(meshNetConfig, internetConfig, hotspotConfig, simTime, enableHotspot, meshClientNodeIndex, packetSize);

    // ========================================================================
    // STEP 8: Configure NetAnim and FlowMonitor
    // ========================================================================
    AnimationInterface anim("wifi_test_research/wifi-test-2-adhoc-grid.xml");
    ConfigureNetAnim(anim);
    
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.InstallAll();

    // ========================================================================
    // STEP 9: Display Info and Run Simulation
    // ========================================================================
    DisplaySimulationInfo(nNodes, gridWidth, simTime, enableHotspot, apNodeIndex, numStaNodes, meshClientNodeIndex);
    
    // Save configuration JSON for analysis scripts
    SaveConfigurationJSON(nNodes, gridWidth, numStaNodes, packetSize, nodeSpacing, meshConfig);
    
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    // ========================================================================
    // STEP 10: Save Results and Cleanup
    // ========================================================================
    SaveFlowMonitorResults(monitor, flowmon);
    Simulator::Destroy();

    return 0;
}
