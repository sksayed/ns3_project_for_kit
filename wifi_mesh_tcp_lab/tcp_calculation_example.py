#!/usr/bin/env python3
"""
TCP Data Transfer Calculation Example
Demonstrates how to calculate TCP metrics from ns-3 simulation results
"""

import xml.etree.ElementTree as ET
import json

class TCPFlowAnalyzer:
    """Analyzes TCP flow data from ns-3 FlowMonitor XML output"""
    
    def __init__(self, flowmon_xml_path):
        self.xml_path = flowmon_xml_path
        self.flows = []
        
    def parse_flowmon_xml(self):
        """Parse FlowMonitor XML file"""
        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            
            for flow in root.findall('.//Flow'):
                flow_data = {
                    'flowId': flow.get('flowId'),
                    'timeFirstTxPacket': float(flow.get('timeFirstTxPacket', '0').rstrip('ns')) / 1e9,
                    'timeLastRxPacket': float(flow.get('timeLastRxPacket', '0').rstrip('ns')) / 1e9,
                    'txBytes': int(flow.get('txBytes', '0')),
                    'rxBytes': int(flow.get('rxBytes', '0')),
                    'txPackets': int(flow.get('txPackets', '0')),
                    'rxPackets': int(flow.get('rxPackets', '0')),
                    'lostPackets': int(flow.get('lostPackets', '0')),
                    'delaySum': float(flow.get('delaySum', '0').rstrip('ns')) / 1e9,
                    'jitterSum': float(flow.get('jitterSum', '0').rstrip('ns')) / 1e9,
                }
                self.flows.append(flow_data)
            
            return self.flows
        except Exception as e:
            print(f"Error parsing FlowMonitor XML: {e}")
            return []
    
    def calculate_metrics(self, flow_data, sim_time):
        """Calculate comprehensive TCP metrics"""
        
        # Basic metrics
        tx_bytes = flow_data['txBytes']
        rx_bytes = flow_data['rxBytes']
        tx_packets = flow_data['txPackets']
        rx_packets = flow_data['rxPackets']
        lost_packets = flow_data['lostPackets']
        
        # Calculate derived metrics
        metrics = {
            'flow_id': flow_data['flowId'],
            
            # Data transfer
            'tx_bytes': tx_bytes,
            'rx_bytes': rx_bytes,
            'tx_packets': tx_packets,
            'rx_packets': rx_packets,
            'lost_packets': lost_packets,
            
            # Throughput (bits per second)
            'throughput_bps': (rx_bytes * 8) / sim_time if sim_time > 0 else 0,
            'throughput_kbps': (rx_bytes * 8) / sim_time / 1000 if sim_time > 0 else 0,
            'throughput_mbps': (rx_bytes * 8) / sim_time / 1e6 if sim_time > 0 else 0,
            
            # Packet delivery ratio
            'pdr_percent': (rx_packets / tx_packets * 100) if tx_packets > 0 else 0,
            
            # Loss rate
            'loss_rate_percent': (lost_packets / tx_packets * 100) if tx_packets > 0 else 0,
            
            # Average delay
            'avg_delay_sec': (flow_data['delaySum'] / rx_packets) if rx_packets > 0 else 0,
            'avg_delay_ms': (flow_data['delaySum'] / rx_packets * 1000) if rx_packets > 0 else 0,
            
            # Average jitter
            'avg_jitter_sec': (flow_data['jitterSum'] / rx_packets) if rx_packets > 0 else 0,
            'avg_jitter_ms': (flow_data['jitterSum'] / rx_packets * 1000) if rx_packets > 0 else 0,
            
            # Protocol overhead
            'overhead_bytes': tx_bytes - rx_bytes,
            'overhead_percent': ((tx_bytes - rx_bytes) / tx_bytes * 100) if tx_bytes > 0 else 0,
            
            # Transmission duration
            'duration_sec': flow_data['timeLastRxPacket'] - flow_data['timeFirstTxPacket'],
        }
        
        return metrics
    
    def print_metrics(self, metrics):
        """Pretty print TCP metrics"""
        print("\n" + "="*60)
        print(f"TCP Flow Analysis - Flow ID: {metrics['flow_id']}")
        print("="*60)
        
        print("\n📊 DATA TRANSFER:")
        print(f"  Transmitted:  {metrics['tx_bytes']:,} bytes ({metrics['tx_packets']:,} packets)")
        print(f"  Received:     {metrics['rx_bytes']:,} bytes ({metrics['rx_packets']:,} packets)")
        print(f"  Lost:         {metrics['lost_packets']:,} packets")
        
        print("\n🚀 THROUGHPUT:")
        print(f"  {metrics['throughput_bps']:,.2f} bits/sec")
        print(f"  {metrics['throughput_kbps']:,.2f} Kbps")
        print(f"  {metrics['throughput_mbps']:.4f} Mbps")
        
        print("\n📈 PERFORMANCE:")
        print(f"  Packet Delivery Ratio: {metrics['pdr_percent']:.2f}%")
        print(f"  Packet Loss Rate:      {metrics['loss_rate_percent']:.2f}%")
        
        print("\n⏱️  TIMING:")
        print(f"  Average Delay:  {metrics['avg_delay_ms']:.3f} ms")
        print(f"  Average Jitter: {metrics['avg_jitter_ms']:.3f} ms")
        print(f"  Duration:       {metrics['duration_sec']:.3f} seconds")
        
        print("\n📦 OVERHEAD:")
        print(f"  Protocol Overhead: {metrics['overhead_bytes']:,} bytes ({metrics['overhead_percent']:.2f}%)")
        
        print("\n" + "="*60 + "\n")


def example_manual_calculation():
    """Example: Manual calculation of TCP metrics"""
    print("\n" + "="*70)
    print("EXAMPLE: Manual TCP Calculation")
    print("="*70)
    
    # Simulation parameters
    sim_time = 10.0  # seconds
    max_bytes_sent = 1_000_000  # 1 MB
    
    # FlowMonitor results (example values)
    tx_packets = 691
    rx_packets = 689
    tx_bytes = 1_057_330
    rx_bytes = 1_054_472
    delay_sum = 2.145  # seconds
    
    print("\n📋 Given:")
    print(f"  Application wants to send: {max_bytes_sent:,} bytes (1 MB)")
    print(f"  Simulation time:           {sim_time} seconds")
    print(f"  TCP segment size:          1,448 bytes (typical)")
    
    print("\n📊 FlowMonitor Results:")
    print(f"  TX Packets: {tx_packets}")
    print(f"  RX Packets: {rx_packets}")
    print(f"  TX Bytes:   {tx_bytes:,}")
    print(f"  RX Bytes:   {rx_bytes:,}")
    
    print("\n🔢 Calculations:")
    
    # 1. Number of segments needed
    segment_size = 1448
    segments_needed = max_bytes_sent // segment_size + (1 if max_bytes_sent % segment_size else 0)
    print(f"\n  1. Segments needed = {max_bytes_sent:,} / {segment_size} = {segments_needed}")
    
    # 2. Protocol overhead per packet
    tcp_header = 32
    ip_header = 20
    overhead_per_packet = tcp_header + ip_header
    print(f"\n  2. Overhead per packet = TCP({tcp_header}) + IP({ip_header}) = {overhead_per_packet} bytes")
    
    # 3. Total bytes on wire
    bytes_on_wire = segments_needed * (segment_size + overhead_per_packet)
    print(f"\n  3. Bytes on wire = {segments_needed} × ({segment_size} + {overhead_per_packet})")
    print(f"                    = {segments_needed} × {segment_size + overhead_per_packet}")
    print(f"                    = {bytes_on_wire:,} bytes")
    
    # 4. Throughput
    throughput_bps = rx_bytes * 8 / sim_time
    throughput_mbps = throughput_bps / 1e6
    print(f"\n  4. Throughput = ({rx_bytes:,} bytes × 8 bits) / {sim_time} sec")
    print(f"                = {throughput_bps:,.0f} bits/sec")
    print(f"                = {throughput_mbps:.4f} Mbps")
    
    # 5. Goodput (application layer)
    app_rx_bytes = max_bytes_sent * (rx_packets / tx_packets)  # Approximate
    goodput_mbps = (app_rx_bytes * 8) / sim_time / 1e6
    print(f"\n  5. Goodput = ({app_rx_bytes:,.0f} bytes × 8 bits) / {sim_time} sec")
    print(f"             = {goodput_mbps:.4f} Mbps (application data only)")
    
    # 6. Protocol efficiency
    efficiency = (app_rx_bytes / rx_bytes) * 100
    print(f"\n  6. Protocol Efficiency = {app_rx_bytes:,.0f} / {rx_bytes:,} × 100%")
    print(f"                         = {efficiency:.2f}%")
    
    # 7. Packet delivery ratio
    pdr = (rx_packets / tx_packets) * 100
    print(f"\n  7. Packet Delivery Ratio = {rx_packets} / {tx_packets} × 100%")
    print(f"                            = {pdr:.2f}%")
    
    # 8. Average delay
    avg_delay_ms = (delay_sum / rx_packets) * 1000
    print(f"\n  8. Average Delay = {delay_sum:.3f} sec / {rx_packets} packets")
    print(f"                    = {avg_delay_ms:.3f} ms per packet")
    
    print("\n" + "="*70)


def compare_layers():
    """Compare measurements at different protocol layers"""
    print("\n" + "="*70)
    print("COMPARISON: Different Measurement Layers")
    print("="*70)
    
    # Example data
    app_bytes = 1_000_000      # Application layer (PacketSink)
    transport_bytes = 1_022_000  # TCP layer (with TCP headers)
    network_bytes = 1_042_000    # IP layer (with IP headers)
    link_bytes = 1_072_000       # WiFi layer (with WiFi headers + retransmissions)
    
    print("\n📚 Protocol Stack (from bottom to top):")
    print(f"\n  ┌─────────────────────────────────────────┐")
    print(f"  │ Application Layer                       │")
    print(f"  │ PacketSink: {app_bytes:,} bytes            │  ← Useful data")
    print(f"  ├─────────────────────────────────────────┤")
    print(f"  │ Transport Layer (TCP)                   │")
    print(f"  │ + TCP headers: {transport_bytes - app_bytes:,} bytes         │")
    print(f"  │ = {transport_bytes:,} bytes             │")
    print(f"  ├─────────────────────────────────────────┤")
    print(f"  │ Network Layer (IP)                      │")
    print(f"  │ + IP headers: {network_bytes - transport_bytes:,} bytes          │")
    print(f"  │ = {network_bytes:,} bytes ← FlowMonitor   │")
    print(f"  ├─────────────────────────────────────────┤")
    print(f"  │ Link Layer (WiFi)                       │")
    print(f"  │ + WiFi overhead: {link_bytes - network_bytes:,} bytes     │")
    print(f"  │ = {link_bytes:,} bytes  ← PCAP/Traces  │")
    print(f"  └─────────────────────────────────────────┘")
    
    print(f"\n📊 Overhead Analysis:")
    tcp_overhead = ((transport_bytes - app_bytes) / app_bytes) * 100
    ip_overhead = ((network_bytes - transport_bytes) / app_bytes) * 100
    wifi_overhead = ((link_bytes - network_bytes) / app_bytes) * 100
    total_overhead = ((link_bytes - app_bytes) / app_bytes) * 100
    
    print(f"  TCP overhead:   {tcp_overhead:.2f}%")
    print(f"  IP overhead:    {ip_overhead:.2f}%")
    print(f"  WiFi overhead:  {wifi_overhead:.2f}%")
    print(f"  ─────────────────────────")
    print(f"  Total overhead: {total_overhead:.2f}%")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TCP DATA TRANSFER CALCULATION EXAMPLES")
    print("="*70)
    
    # Example 1: Manual calculation
    example_manual_calculation()
    
    # Example 2: Compare layers
    compare_layers()
    
    # Example 3: Parse FlowMonitor XML (if file exists)
    print("\n" + "="*70)
    print("EXAMPLE: Parsing FlowMonitor XML")
    print("="*70)
    
    xml_files = [
        "wifi_mesh_tcp_lab/tcp_mesh_adhoc_mode_flowmon.xml",
        "wifi_mesh_tcp_lab/tcp_mesh_single_ap_flowmon.xml",
        "wifi_mesh_tcp_lab/tcp_mesh_dual_ap_close_flowmon.xml",
        "wifi_mesh_tcp_lab/tcp_mesh_dual_ap_distant_flowmon.xml",
        "wifi_mesh_backhaul_outputs/flowmon-wifi-mesh-backhaul.xml",
    ]
    
    analyzer = None
    for xml_file in xml_files:
        try:
            analyzer = TCPFlowAnalyzer(xml_file)
            flows = analyzer.parse_flowmon_xml()
            if flows:
                print(f"\n✅ Found {len(flows)} flow(s) in {xml_file}")
                for flow in flows:
                    metrics = analyzer.calculate_metrics(flow, sim_time=10.0)
                    analyzer.print_metrics(metrics)
                break
        except:
            continue
    
    if not analyzer or not flows:
        print("\n⚠️  No FlowMonitor XML files found.")
        print("   Run a simulation first to generate flow data:")
        print("   ./ns3 run wifi_mesh_tcp_lab/tcp_mesh_adhoc_mode")
        print("   (Output files will be in wifi_mesh_tcp_lab/ directory)")
    
    print("\n" + "="*70)
    print("For more information, see TCP_MEASUREMENT_GUIDE.md")
    print("="*70 + "\n")

