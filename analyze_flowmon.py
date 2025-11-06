#!/usr/bin/env python3
"""
FlowMonitor XML Analysis Script
Analyzes NS-3 FlowMonitor XML output and generates detailed UE metrics report
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path

def parse_flowmon_xml(xml_file):
    """Parse FlowMonitor XML file and extract metrics"""
    
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Extract flow statistics
    flows = {}
    for flow_elem in root.findall('.//FlowStats/Flow'):
        flow_id = int(flow_elem.get('flowId'))
        flows[flow_id] = {
            'txBytes': int(flow_elem.get('txBytes', 0)),
            'rxBytes': int(flow_elem.get('rxBytes', 0)),
            'txPackets': int(flow_elem.get('txPackets', 0)),
            'rxPackets': int(flow_elem.get('rxPackets', 0)),
            'lostPackets': int(flow_elem.get('lostPackets', 0)),
            'delaySum': float(flow_elem.get('delaySum', 0).replace('ns', '').replace('+', '')) / 1e9,  # Convert to seconds
            'jitterSum': float(flow_elem.get('jitterSum', 0).replace('ns', '').replace('+', '')) / 1e9,
            'timeFirstTxPacket': float(flow_elem.get('timeFirstTxPacket', 0).replace('ns', '').replace('+', '')) / 1e9,
            'timeLastRxPacket': float(flow_elem.get('timeLastRxPacket', 0).replace('ns', '').replace('+', '')) / 1e9,
        }
    
    # Extract flow classifier
    flow_classifier = {}
    ipv4_classifier = root.find('.//Ipv4FlowClassifier')
    if ipv4_classifier is not None:
        for flow_elem in ipv4_classifier.findall('Flow'):
            flow_id = int(flow_elem.get('flowId'))
            flow_classifier[flow_id] = {
                'sourceAddress': flow_elem.get('sourceAddress'),
                'destinationAddress': flow_elem.get('destinationAddress'),
                'protocol': flow_elem.get('protocol'),
                'sourcePort': flow_elem.get('sourcePort'),
                'destinationPort': flow_elem.get('destinationPort'),
            }
    
    return flows, flow_classifier

def map_ue_to_flows(flows, flow_classifier):
    """Map UE IP addresses to flow statistics"""
    
    # UE IP addresses start from 7.0.0.2, 7.0.0.3, ..., 7.0.0.11
    ue_metrics = {}
    
    for flow_id, classifier in flow_classifier.items():
        if flow_id not in flows:
            continue
            
        src_ip = classifier['sourceAddress']
        flow_stats = flows[flow_id]
        
        # Extract UE number from IP address (7.0.0.X where X-1 is UE number)
        if src_ip.startswith('7.0.0.'):
            ue_num = int(src_ip.split('.')[-1]) - 2  # UE 0 is 7.0.0.2
            
            if ue_num not in ue_metrics:
                ue_metrics[ue_num] = {
                    'txBytes': 0,
                    'rxBytes': 0,
                    'txPackets': 0,
                    'rxPackets': 0,
                    'lostPackets': 0,
                    'delaySum': 0.0,
                    'protocol': [],
                    'flows': []
                }
            
            # Aggregate statistics
            ue_metrics[ue_num]['txBytes'] += flow_stats['txBytes']
            ue_metrics[ue_num]['rxBytes'] += flow_stats['rxBytes']
            ue_metrics[ue_num]['txPackets'] += flow_stats['txPackets']
            ue_metrics[ue_num]['rxPackets'] += flow_stats['rxPackets']
            ue_metrics[ue_num]['lostPackets'] += flow_stats['lostPackets']
            ue_metrics[ue_num]['delaySum'] += flow_stats['delaySum']
            
            # Track protocol
            proto = 'TCP' if classifier['protocol'] == '6' else 'UDP' if classifier['protocol'] == '17' else 'Other'
            if proto not in ue_metrics[ue_num]['protocol']:
                ue_metrics[ue_num]['protocol'].append(proto)
            
            ue_metrics[ue_num]['flows'].append(flow_id)
    
    return ue_metrics

def generate_report(ue_metrics, sim_time=30.0):
    """Generate detailed UE metrics report"""
    
    # UE traffic types
    traffic_types = {
        0: "HTTP (TCP)",
        1: "HTTP (TCP)",
        2: "HTTPS (TCP)",
        3: "HTTPS (TCP)",
        4: "Video (TCP)",
        5: "Video (TCP)",
        6: "VoIP (UDP)",
        7: "VoIP (UDP)",
        8: "FTP (TCP)",
        9: "Mixed (TCP)",
    }
    
    print("\n" + "=" * 100)
    print("5G NR SIMULATION - DETAILED UE METRICS REPORT (from FlowMonitor)")
    print("Packet Size: 1 MB (1,048,576 bytes)")
    print(f"Simulation Time: {sim_time} seconds")
    print("=" * 100)
    
    # Header
    header = f"{'UE ID':<8}{'Traffic Type':<18}{'Protocol':<12}{'PDR (%)':<12}{'Delay (ms)':<15}{'Throughput (Mbps)':<20}{'TX Pkts':<12}{'RX Pkts':<12}{'RX Bytes':<15}"
    print(header)
    print("=" * 100)
    
    total_pdr = 0
    total_delay = 0
    total_throughput = 0
    ue_count = 0
    
    # Process each UE
    for ue_id in range(10):
        if ue_id in ue_metrics:
            metrics = ue_metrics[ue_id]
            
            # Calculate metrics
            pdr = (metrics['rxPackets'] / metrics['txPackets'] * 100.0) if metrics['txPackets'] > 0 else 0.0
            avg_delay = (metrics['delaySum'] / metrics['rxPackets'] * 1000.0) if metrics['rxPackets'] > 0 else 0.0  # ms
            throughput = (metrics['rxBytes'] * 8.0 / (sim_time - 0.5) / 1e6) if metrics['rxBytes'] > 0 else 0.0  # Mbps
            
            protocol_str = '/'.join(metrics['protocol']) if metrics['protocol'] else 'N/A'
            
            # Print row
            print(f"{ue_id:<8}{traffic_types.get(ue_id, 'Unknown'):<18}{protocol_str:<12}"
                  f"{pdr:<12.2f}{avg_delay:<15.2f}{throughput:<20.2f}"
                  f"{metrics['txPackets']:<12}{metrics['rxPackets']:<12}{metrics['rxBytes']:<15}")
            
            if metrics['txPackets'] > 0:
                total_pdr += pdr
                total_delay += avg_delay
                total_throughput += throughput
                ue_count += 1
        else:
            # UE with no traffic
            print(f"{ue_id:<8}{traffic_types.get(ue_id, 'Unknown'):<18}{'N/A':<12}"
                  f"{0.0:<12.2f}{0.0:<15.2f}{0.0:<20.2f}"
                  f"{0:<12}{0:<12}{0:<15}")
    
    print("=" * 100)
    
    # Summary statistics
    print("\nSUMMARY STATISTICS:")
    if ue_count > 0:
        print(f"  Average PDR: {total_pdr / ue_count:.2f} %")
        print(f"  Average E2E Delay: {total_delay / ue_count:.2f} ms")
        print(f"  Average Throughput: {total_throughput / ue_count:.2f} Mbps")
        print(f"  Total Throughput: {total_throughput:.2f} Mbps")
    else:
        print("  No data transmitted")
    
    print("=" * 100)

def main():
    xml_file = Path("5g_outputs/flowmon-nr-playfield-rw.xml")
    
    if not xml_file.exists():
        print(f"Error: FlowMonitor XML file not found: {xml_file}")
        sys.exit(1)
    
    print(f"Analyzing FlowMonitor XML: {xml_file}")
    
    flows, flow_classifier = parse_flowmon_xml(xml_file)
    
    print(f"\nTotal flows found: {len(flows)}")
    print(f"Classified flows: {len(flow_classifier)}")
    
    ue_metrics = map_ue_to_flows(flows, flow_classifier)
    
    generate_report(ue_metrics, sim_time=10.0)

if __name__ == "__main__":
    main()

