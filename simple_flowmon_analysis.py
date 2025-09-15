#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import json

def parse_flowmon_xml(xml_file):
    """Parse FlowMonitor XML file and extract flow statistics"""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    flows = []
    for flow in root.findall('.//Flow'):
        # Helper function to parse time values with 'ns' suffix
        def parse_time_ns(time_str):
            if time_str is None:
                return 0.0
            return float(time_str.replace('ns', '')) / 1e9
        
        # Helper function to safely convert to int
        def safe_int(value, default=0):
            return int(value) if value is not None else default
        
        flow_data = {
            'flowId': safe_int(flow.get('flowId')),
            'timeFirstTxPacket': parse_time_ns(flow.get('timeFirstTxPacket')),
            'timeFirstRxPacket': parse_time_ns(flow.get('timeFirstRxPacket')),
            'timeLastTxPacket': parse_time_ns(flow.get('timeLastTxPacket')),
            'timeLastRxPacket': parse_time_ns(flow.get('timeLastRxPacket')),
            'delaySum': parse_time_ns(flow.get('delaySum')),
            'jitterSum': parse_time_ns(flow.get('jitterSum')),
            'lastDelay': parse_time_ns(flow.get('lastDelay')),
            'maxDelay': parse_time_ns(flow.get('maxDelay')),
            'minDelay': parse_time_ns(flow.get('minDelay')),
            'txBytes': safe_int(flow.get('txBytes')),
            'rxBytes': safe_int(flow.get('rxBytes')),
            'txPackets': safe_int(flow.get('txPackets')),
            'rxPackets': safe_int(flow.get('rxPackets')),
            'lostPackets': safe_int(flow.get('lostPackets')),
            'timesForwarded': safe_int(flow.get('timesForwarded'))
        }
        flows.append(flow_data)
    
    return flows

def print_analysis(flows):
    """Print detailed analysis of flow data"""
    print("=" * 60)
    print("WiFi Mesh Network Flow Analysis")
    print("=" * 60)
    
    total_tx_bytes = sum(flow['txBytes'] for flow in flows)
    total_rx_bytes = sum(flow['rxBytes'] for flow in flows)
    total_tx_packets = sum(flow['txPackets'] for flow in flows)
    total_rx_packets = sum(flow['rxPackets'] for flow in flows)
    total_lost_packets = sum(flow['lostPackets'] for flow in flows)
    
    print(f"Total flows: {len(flows)}")
    print(f"Total bytes transmitted: {total_tx_bytes / 1e6:.2f} MB")
    print(f"Total bytes received: {total_rx_bytes / 1e6:.2f} MB")
    print(f"Total packets transmitted: {total_tx_packets}")
    print(f"Total packets received: {total_rx_packets}")
    print(f"Total packets lost: {total_lost_packets}")
    
    if total_tx_packets > 0:
        loss_rate = (total_lost_packets / (total_tx_packets + total_lost_packets)) * 100
        print(f"Overall packet loss rate: {loss_rate:.2f}%")
    
    print("\n" + "=" * 60)
    print("Per-Flow Analysis")
    print("=" * 60)
    
    for flow in flows:
        print(f"\nFlow {flow['flowId']}:")
        print(f"  Duration: {flow['timeLastTxPacket'] - flow['timeFirstTxPacket']:.2f} seconds")
        print(f"  Bytes: TX={flow['txBytes']:,}, RX={flow['rxBytes']:,}")
        print(f"  Packets: TX={flow['txPackets']:,}, RX={flow['rxPackets']:,}, Lost={flow['lostPackets']:,}")
        
        if flow['rxPackets'] > 0:
            avg_delay = (flow['delaySum'] / flow['rxPackets']) * 1000  # Convert to ms
            avg_jitter = (flow['jitterSum'] / flow['rxPackets']) * 1000  # Convert to ms
            print(f"  Avg Delay: {avg_delay:.2f} ms")
            print(f"  Avg Jitter: {avg_jitter:.2f} ms")
            print(f"  Min Delay: {flow['minDelay'] * 1000:.2f} ms")
            print(f"  Max Delay: {flow['maxDelay'] * 1000:.2f} ms")
        
        if flow['timeLastRxPacket'] > flow['timeFirstRxPacket']:
            duration = flow['timeLastRxPacket'] - flow['timeFirstRxPacket']
            throughput = (flow['rxBytes'] * 8) / (duration * 1e6)  # Mbps
            print(f"  Throughput: {throughput:.2f} Mbps")
        
        print(f"  Times Forwarded: {flow['timesForwarded']}")

def create_csv_report(flows, filename="flowmon_analysis.csv"):
    """Create a CSV report of flow data"""
    with open(filename, 'w') as f:
        # Write header
        f.write("FlowID,FirstTxTime,FirstRxTime,LastTxTime,LastRxTime,")
        f.write("TxBytes,RxBytes,TxPackets,RxPackets,LostPackets,")
        f.write("AvgDelay_ms,AvgJitter_ms,MinDelay_ms,MaxDelay_ms,")
        f.write("Throughput_Mbps,TimesForwarded\n")
        
        # Write data
        for flow in flows:
            avg_delay = (flow['delaySum'] / flow['rxPackets'] * 1000) if flow['rxPackets'] > 0 else 0
            avg_jitter = (flow['jitterSum'] / flow['rxPackets'] * 1000) if flow['rxPackets'] > 0 else 0
            
            duration = flow['timeLastRxPacket'] - flow['timeFirstRxPacket'] if flow['timeLastRxPacket'] > flow['timeFirstRxPacket'] else 1
            throughput = (flow['rxBytes'] * 8) / (duration * 1e6) if duration > 0 else 0
            
            f.write(f"{flow['flowId']},{flow['timeFirstTxPacket']:.6f},{flow['timeFirstRxPacket']:.6f},")
            f.write(f"{flow['timeLastTxPacket']:.6f},{flow['timeLastRxPacket']:.6f},")
            f.write(f"{flow['txBytes']},{flow['rxBytes']},{flow['txPackets']},{flow['rxPackets']},{flow['lostPackets']},")
            f.write(f"{avg_delay:.2f},{avg_jitter:.2f},{flow['minDelay'] * 1000:.2f},{flow['maxDelay'] * 1000:.2f},")
            f.write(f"{throughput:.2f},{flow['timesForwarded']}\n")
    
    print(f"\nCSV report saved to: {filename}")

if __name__ == "__main__":
    # Parse the XML file
    flows = parse_flowmon_xml('flowmon-wifi-mesh-playfield-rw.xml')
    
    # Print analysis
    print_analysis(flows)
    
    # Create CSV report
    create_csv_report(flows)
    
    # Create JSON report for further processing
    with open('flowmon_analysis.json', 'w') as f:
        json.dump(flows, f, indent=2)
    print("JSON report saved to: flowmon_analysis.json")
