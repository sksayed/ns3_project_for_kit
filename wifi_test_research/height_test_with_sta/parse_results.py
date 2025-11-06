#!/usr/bin/env python3
"""
FlowMonitor XML Parser for Mesh AP Height Optimization
Extracts PDR, Throughput, and End-to-End Delay metrics
"""

import xml.etree.ElementTree as ET
import os
import csv
import re
from collections import defaultdict
import statistics

# Get the script's directory and construct absolute paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, 'results')
OUTPUT_CSV = os.path.join(RESULTS_DIR, 'parsed_results.csv')

def parse_flowmonitor_xml(xml_file):
    """
    Parse a single FlowMonitor XML file and extract metrics
    Returns: dict with PDR, throughput, delay for STA→Server flows
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"  ✗ Error parsing {xml_file}: {e}")
        return None
    
    # Find all flows
    flow_stats = root.find('FlowStats')
    if flow_stats is None:
        print(f"  ⚠ No FlowStats in {xml_file}")
        return None
    
    # Get classifier to identify flow sources/destinations
    classifier = root.find('Ipv4FlowClassifier')
    if classifier is None:
        print(f"  ⚠ No Ipv4FlowClassifier in {xml_file}")
        return None
    
    # Build flow ID to IP mapping
    flow_info = {}
    for flow in classifier.findall('Flow'):
        flow_id = flow.get('flowId')
        src_ip = flow.get('sourceAddress')
        dst_ip = flow.get('destinationAddress')
        flow_info[flow_id] = {'src': src_ip, 'dst': dst_ip}
    
    # Extract metrics for STA→Server flows (192.168.2.x → 8.8.8.2)
    sta_flows = []
    
    for flow in flow_stats.findall('Flow'):
        flow_id = flow.get('flowId')
        
        # Check if this is a STA→Server flow
        if flow_id in flow_info:
            src_ip = flow_info[flow_id]['src']
            dst_ip = flow_info[flow_id]['dst']
            
            # STA network is 192.168.2.x, Server is 8.8.8.2
            if src_ip.startswith('192.168.2.') and dst_ip == '8.8.8.2':
                tx_packets = int(flow.get('txPackets', 0))
                rx_packets = int(flow.get('rxPackets', 0))
                tx_bytes = int(flow.get('txBytes', 0))
                rx_bytes = int(flow.get('rxBytes', 0))
                delay_sum = float(flow.get('delaySum', '0').replace('ns', '').replace('+', ''))
                time_first_tx = float(flow.get('timeFirstTxPacket', '0').replace('ns', '').replace('+', ''))
                time_last_rx = float(flow.get('timeLastRxPacket', '0').replace('ns', '').replace('+', ''))
                
                if tx_packets > 0:
                    # Calculate PDR (Packet Delivery Ratio)
                    pdr = (rx_packets / tx_packets) * 100.0
                    
                    # Calculate Throughput (Mbps)
                    if time_last_rx > time_first_tx and rx_bytes > 0:
                        duration = (time_last_rx - time_first_tx) / 1e9  # Convert ns to seconds
                        throughput = (rx_bytes * 8.0) / (duration * 1e6)  # Convert to Mbps
                    else:
                        throughput = 0.0
                    
                    # Calculate Average End-to-End Delay (ms)
                    if rx_packets > 0:
                        avg_delay = (delay_sum / rx_packets) / 1e6  # Convert ns to ms
                    else:
                        avg_delay = 0.0
                    
                    sta_flows.append({
                        'pdr': pdr,
                        'throughput': throughput,
                        'delay': avg_delay,
                        'tx_packets': tx_packets,
                        'rx_packets': rx_packets
                    })
    
    # Aggregate all STA flows (in case multiple STAs)
    if sta_flows:
        total_tx = sum(f['tx_packets'] for f in sta_flows)
        total_rx = sum(f['rx_packets'] for f in sta_flows)
        
        # Overall PDR
        pdr = (total_rx / total_tx * 100.0) if total_tx > 0 else 0.0
        
        # Average throughput across all flows
        throughput = statistics.mean(f['throughput'] for f in sta_flows)
        
        # Average delay across all flows
        delay = statistics.mean(f['delay'] for f in sta_flows)
        
        return {
            'pdr': pdr,
            'throughput': throughput,
            'delay': delay
        }
    
    return None


def parse_filename(filename):
    """
    Extract AP height, STA height, and trial from filename
    Format: ap{X}m_sta{Y}m_{trial}_flowmon.xml
    """
    match = re.match(r'ap(\d+(?:\.\d+)?)m_sta(\d+)m_(trial\d+)_flowmon\.xml', filename)
    if match:
        return {
            'ap_height': float(match.group(1)),
            'sta_height': int(match.group(2)),
            'trial': match.group(3)
        }
    return None


def main():
    print("=" * 80)
    print("  FLOWMONITOR XML PARSER")
    print("=" * 80)
    print(f"  Results directory: {RESULTS_DIR}")
    print()
    
    # Find all FlowMonitor XML files
    xml_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('_flowmon.xml')]
    
    if not xml_files:
        print("✗ No FlowMonitor XML files found!")
        return
    
    print(f"Found {len(xml_files)} FlowMonitor files")
    print()
    
    # Parse each file
    results = []
    
    for xml_file in sorted(xml_files):
        filepath = os.path.join(RESULTS_DIR, xml_file)
        
        # Extract configuration from filename
        config = parse_filename(xml_file)
        if not config:
            print(f"  ⚠ Skipping {xml_file} - invalid filename format")
            continue
        
        print(f"  Parsing: AP={config['ap_height']}m, STA={config['sta_height']}m, {config['trial']}")
        
        # Parse metrics
        metrics = parse_flowmonitor_xml(filepath)
        
        if metrics:
            results.append({
                'ap_height': config['ap_height'],
                'sta_height': config['sta_height'],
                'trial': config['trial'],
                'pdr': metrics['pdr'],
                'throughput': metrics['throughput'],
                'delay': metrics['delay']
            })
            print(f"    ✓ PDR: {metrics['pdr']:.2f}%, Throughput: {metrics['throughput']:.2f} Mbps, Delay: {metrics['delay']:.2f} ms")
        else:
            print(f"    ✗ No STA→Server flows found")
    
    print()
    print(f"Successfully parsed {len(results)} files")
    print()
    
    # Group by configuration and calculate statistics
    configs = defaultdict(list)
    for r in results:
        key = (r['ap_height'], r['sta_height'])
        configs[key].append(r)
    
    # Calculate mean and std for each configuration
    aggregated = []
    
    for (ap_h, sta_h), trials in sorted(configs.items()):
        if len(trials) >= 2:  # Need at least 2 trials for std
            pdr_values = [t['pdr'] for t in trials]
            throughput_values = [t['throughput'] for t in trials]
            delay_values = [t['delay'] for t in trials]
            
            aggregated.append({
                'ap_height': ap_h,
                'sta_height': sta_h,
                'pdr_mean': statistics.mean(pdr_values),
                'pdr_std': statistics.stdev(pdr_values) if len(pdr_values) > 1 else 0.0,
                'throughput_mean': statistics.mean(throughput_values),
                'throughput_std': statistics.stdev(throughput_values) if len(throughput_values) > 1 else 0.0,
                'delay_mean': statistics.mean(delay_values),
                'delay_std': statistics.stdev(delay_values) if len(delay_values) > 1 else 0.0,
                'num_trials': len(trials)
            })
        elif len(trials) == 1:
            # Only one trial - use values directly with 0 std
            aggregated.append({
                'ap_height': ap_h,
                'sta_height': sta_h,
                'pdr_mean': trials[0]['pdr'],
                'pdr_std': 0.0,
                'throughput_mean': trials[0]['throughput'],
                'throughput_std': 0.0,
                'delay_mean': trials[0]['delay'],
                'delay_std': 0.0,
                'num_trials': 1
            })
    
    # Write to CSV
    if aggregated:
        with open(OUTPUT_CSV, 'w', newline='') as csvfile:
            fieldnames = ['ap_height', 'sta_height', 'pdr_mean', 'pdr_std', 
                         'throughput_mean', 'throughput_std', 'delay_mean', 'delay_std', 'num_trials']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in aggregated:
                writer.writerow(row)
        
        print("=" * 80)
        print(f"✓ Aggregated results saved to: {OUTPUT_CSV}")
        print(f"  Total configurations: {len(aggregated)}")
        print("=" * 80)
        print()
    else:
        print("✗ No aggregated data to save")


if __name__ == '__main__':
    main()

