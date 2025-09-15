#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def parse_flowmon_xml(xml_file):
    """Parse FlowMonitor XML file and extract flow statistics"""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    flows = []
    for flow in root.findall('.//Flow'):
        flow_data = {
            'flowId': int(flow.get('flowId')),
            'timeFirstTxPacket': float(flow.get('timeFirstTxPacket')) / 1e9,  # Convert to seconds
            'timeFirstRxPacket': float(flow.get('timeFirstRxPacket')) / 1e9,
            'timeLastTxPacket': float(flow.get('timeLastTxPacket')) / 1e9,
            'timeLastRxPacket': float(flow.get('timeLastRxPacket')) / 1e9,
            'delaySum': float(flow.get('delaySum')) / 1e9,  # Convert to seconds
            'jitterSum': float(flow.get('jitterSum')) / 1e9,
            'lastDelay': float(flow.get('lastDelay')) / 1e9,
            'maxDelay': float(flow.get('maxDelay')) / 1e9,
            'minDelay': float(flow.get('minDelay')) / 1e9,
            'txBytes': int(flow.get('txBytes')),
            'rxBytes': int(flow.get('rxBytes')),
            'txPackets': int(flow.get('txPackets')),
            'rxPackets': int(flow.get('rxPackets')),
            'lostPackets': int(flow.get('lostPackets')),
            'timesForwarded': int(flow.get('timesForwarded'))
        }
        flows.append(flow_data)
    
    return pd.DataFrame(flows)

def create_visualizations(df):
    """Create various visualizations of the flow data"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('WiFi Mesh Network Flow Analysis', fontsize=16)
    
    # 1. Throughput over time
    ax1 = axes[0, 0]
    df['throughput_mbps'] = (df['rxBytes'] * 8) / ((df['timeLastRxPacket'] - df['timeFirstRxPacket']) * 1e6)
    ax1.bar(df['flowId'], df['throughput_mbps'])
    ax1.set_xlabel('Flow ID')
    ax1.set_ylabel('Throughput (Mbps)')
    ax1.set_title('Flow Throughput')
    ax1.grid(True, alpha=0.3)
    
    # 2. Packet loss rate
    ax2 = axes[0, 1]
    df['loss_rate'] = df['lostPackets'] / (df['txPackets'] + df['lostPackets']) * 100
    ax2.bar(df['flowId'], df['loss_rate'])
    ax2.set_xlabel('Flow ID')
    ax2.set_ylabel('Packet Loss Rate (%)')
    ax2.set_title('Packet Loss Rate')
    ax2.grid(True, alpha=0.3)
    
    # 3. Average delay
    ax3 = axes[0, 2]
    df['avg_delay'] = df['delaySum'] / df['rxPackets'] * 1000  # Convert to ms
    ax3.bar(df['flowId'], df['avg_delay'])
    ax3.set_xlabel('Flow ID')
    ax3.set_ylabel('Average Delay (ms)')
    ax3.set_title('Average End-to-End Delay')
    ax3.grid(True, alpha=0.3)
    
    # 4. Jitter
    ax4 = axes[1, 0]
    df['avg_jitter'] = df['jitterSum'] / df['rxPackets'] * 1000  # Convert to ms
    ax4.bar(df['flowId'], df['avg_jitter'])
    ax4.set_xlabel('Flow ID')
    ax4.set_ylabel('Average Jitter (ms)')
    ax4.set_title('Average Jitter')
    ax4.grid(True, alpha=0.3)
    
    # 5. Bytes transmitted vs received
    ax5 = axes[1, 1]
    x = np.arange(len(df))
    width = 0.35
    ax5.bar(x - width/2, df['txBytes']/1e6, width, label='Transmitted (MB)', alpha=0.8)
    ax5.bar(x + width/2, df['rxBytes']/1e6, width, label='Received (MB)', alpha=0.8)
    ax5.set_xlabel('Flow ID')
    ax5.set_ylabel('Bytes (MB)')
    ax5.set_title('Bytes Transmitted vs Received')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # 6. Delay distribution
    ax6 = axes[1, 2]
    ax6.hist(df['avg_delay'], bins=10, alpha=0.7, edgecolor='black')
    ax6.set_xlabel('Average Delay (ms)')
    ax6.set_ylabel('Number of Flows')
    ax6.set_title('Delay Distribution')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('flowmon_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print summary statistics
    print("\n=== Flow Summary Statistics ===")
    print(f"Total flows: {len(df)}")
    print(f"Total bytes transmitted: {df['txBytes'].sum() / 1e6:.2f} MB")
    print(f"Total bytes received: {df['rxBytes'].sum() / 1e6:.2f} MB")
    print(f"Overall packet loss rate: {df['lostPackets'].sum() / (df['txPackets'].sum() + df['lostPackets'].sum()) * 100:.2f}%")
    print(f"Average throughput: {df['throughput_mbps'].mean():.2f} Mbps")
    print(f"Average delay: {df['avg_delay'].mean():.2f} ms")
    print(f"Average jitter: {df['avg_jitter'].mean():.2f} ms")

if __name__ == "__main__":
    # Parse the XML file
    df = parse_flowmon_xml('flowmon-wifi-mesh-playfield-rw.xml')
    
    # Create visualizations
    create_visualizations(df)
    
    # Save detailed CSV report
    df.to_csv('flowmon_analysis.csv', index=False)
    print("Detailed analysis saved to 'flowmon_analysis.csv'")
