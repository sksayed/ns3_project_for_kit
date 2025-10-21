#!/usr/bin/env python3
# Parse FlowMonitor XML results and generate summary plots/CSV.
import xml.etree.ElementTree as ET
import matplotlib
# Use a non-interactive backend so this works in headless environments.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def parse_flowmon_xml(xml_file):
    """Parse FlowMonitor XML file and extract per-flow statistics into a DataFrame."""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    def parse_time_to_seconds(value: str) -> float:
        """Convert strings like '+2.0e+09ns', '25ms', '1.2s' to seconds (float)."""
        if value is None:
            return 0.0
        v = value.strip()
        if v.endswith('ns'):
            return float(v[:-2]) / 1e9
        if v.endswith('us'):
            return float(v[:-2]) / 1e6
        if v.endswith('ms'):
            return float(v[:-2]) / 1e3
        if v.endswith('s'):
            return float(v[:-1])
        return float(v)

    def get_int(elem, attr, default=0):
        """Safely read integer attributes; return default if missing/invalid."""
        v = elem.get(attr)
        try:
            return int(v) if v is not None and v != '' else default
        except Exception:
            return default

    flows = []
    # Iterate over <Flow> entries and collect key metrics.
    for flow in root.findall('.//Flow'):
        flow_id = get_int(flow, 'flowId', default=-1)
        if flow_id < 0:
            continue
        flow_data = {
            'flowId': flow_id,
            'timeFirstTxPacket': parse_time_to_seconds(flow.get('timeFirstTxPacket')),
            'timeFirstRxPacket': parse_time_to_seconds(flow.get('timeFirstRxPacket')),
            'timeLastTxPacket': parse_time_to_seconds(flow.get('timeLastTxPacket')),
            'timeLastRxPacket': parse_time_to_seconds(flow.get('timeLastRxPacket')),
            'delaySum': parse_time_to_seconds(flow.get('delaySum')),
            'jitterSum': parse_time_to_seconds(flow.get('jitterSum')),
            'lastDelay': parse_time_to_seconds(flow.get('lastDelay')),
            'maxDelay': parse_time_to_seconds(flow.get('maxDelay')),
            'minDelay': parse_time_to_seconds(flow.get('minDelay')),
            'txBytes': get_int(flow, 'txBytes'),
            'rxBytes': get_int(flow, 'rxBytes'),
            'txPackets': get_int(flow, 'txPackets'),
            'rxPackets': get_int(flow, 'rxPackets'),
            'lostPackets': get_int(flow, 'lostPackets'),
            'timesForwarded': get_int(flow, 'timesForwarded')
        }
        flows.append(flow_data)
    
    # Return as a pandas DataFrame for convenient plotting/aggregation.
    return pd.DataFrame(flows)

def create_visualizations(df, out_dir="Lte_outputs"):
    """Create multi-panel summary plots and save a PNG to out_dir."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('LTE Network Flow Analysis', fontsize=16)
    
    # 1. Throughput over time
    ax1 = axes[0, 0]
    # Guard against zero/negative durations to avoid divide-by-zero.
    duration = (df['timeLastRxPacket'] - df['timeFirstRxPacket']).replace(0, np.nan)
    df['throughput_mbps'] = (df['rxBytes'] * 8) / (duration * 1e6)
    df['throughput_mbps'] = df['throughput_mbps'].fillna(0)
    ax1.bar(df['flowId'], df['throughput_mbps'])
    ax1.set_xlabel('Flow ID')
    ax1.set_ylabel('Throughput (Mbps)')
    ax1.set_title('Flow Throughput')
    ax1.grid(True, alpha=0.3)
    
    # 2. Packet loss rate
    ax2 = axes[0, 1]
    # Packet loss = lost / (tx + lost), expressed as percentage.
    denom = (df['txPackets'] + df['lostPackets']).replace(0, np.nan)
    df['loss_rate'] = (df['lostPackets'] / denom * 100).fillna(0)
    ax2.bar(df['flowId'], df['loss_rate'])
    ax2.set_xlabel('Flow ID')
    ax2.set_ylabel('Packet Loss Rate (%)')
    ax2.set_title('Packet Loss Rate')
    ax2.grid(True, alpha=0.3)
    
    # 3. Average delay
    ax3 = axes[0, 2]
    # Average E2E delay = delaySum / rxPackets (ms), NaN-safe.
    df['avg_delay'] = (df['delaySum'] / df['rxPackets'].replace(0, np.nan) * 1000).fillna(0)
    ax3.bar(df['flowId'], df['avg_delay'])
    ax3.set_xlabel('Flow ID')
    ax3.set_ylabel('Average Delay (ms)')
    ax3.set_title('Average End-to-End Delay')
    ax3.grid(True, alpha=0.3)
    
    # 4. Jitter
    ax4 = axes[1, 0]
    # Average jitter = jitterSum / rxPackets (ms), NaN-safe.
    df['avg_jitter'] = (df['jitterSum'] / df['rxPackets'].replace(0, np.nan) * 1000).fillna(0)
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
    
    # Save figure to disk (no GUI window shown due to Agg backend).
    plt.tight_layout()
    plt.savefig(f'{out_dir}/flowmon_analysis.png', dpi=300, bbox_inches='tight')
    
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
    # Input/Output directory where the ns-3 simulation wrote its results.
    in_dir = 'Lte_outputs'
    xml_path = f"{in_dir}/flowmon-lte-playfield-rw.xml"

    # Parse FlowMonitor XML into a DataFrame.
    df = parse_flowmon_xml(xml_path)
    
    # Create and save plots summarizing throughput, loss, delay, jitter, bytes.
    create_visualizations(df, out_dir=in_dir)
    
    # Save a CSV report with the raw per-flow statistics and derived metrics.
    df.to_csv(f"{in_dir}/flowmon_analysis.csv", index=False)
    print("Detailed analysis saved to 'Lte_outputs/flowmon_analysis.csv'")
