#!/usr/bin/env python3
"""
LTE IPv4 L3 Trace Analyzer
Parses LTE simulation traces and extracts UDP/TCP statistics
"""
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import subprocess
import glob

OUTPUT_DIR = "Lte_outputs"
IPV4_L3_FILE = os.path.join(OUTPUT_DIR, "ipv4-l3.tr")

# Regex patterns for LTE IPv4 L3 traces
# Header line start (captures event/time/node/direction)
header_prefix_pattern = re.compile(
    r'^(?P<event>[tr])\s+'
    r'(?P<time>[\d.]+)\s+'
    r'/NodeList/(?P<node>\d+)/\$ns3::Ipv4L3Protocol/(?P<direction>\w+)\([^)]*\)\s+' 
)

# Generic IPv4 header (works for outer and inner headers)
ipv4_any_pattern = re.compile(
    r'ns3::Ipv4Header\s+\('
    r'.*?protocol\s+(?P<protocol>\d+)'
    r'.*?id\s+(?P<ip_id>\d+)'
    r'.*?length:\s*(?P<length>\d+)\s+'
    r'(?P<src_ip>[\d.]+)\s*>\s*(?P<dst_ip>[\d.]+)\)',
    re.DOTALL
)

# UDP header pattern
udp_pattern = re.compile(
    r'ns3::UdpHeader\s+\(length:\s*\d+\s+'
    r'(?P<src_port>\d+)\s*>\s*(?P<dst_port>\d+)\)'
)

# TCP header pattern  
tcp_pattern = re.compile(
    r'ns3::TcpHeader\s+\([^)]*'
    r'(?P<src_port>\d+)\s*>\s*(?P<dst_port>\d+)'
)

# GTP-U tunnel pattern (LTE-specific)
gtpu_pattern = re.compile(
    r'ns3::GtpuHeader\s+\([^)]*teid=(?P<teid>\d+)'
)

def parse_ipv4_l3_traces(file_path):
    """Parse IPv4 L3 trace file for LTE simulation"""
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return pd.DataFrame()
    
    print(f"Parsing {file_path}...")
    records = []
    
    with open(file_path, 'r', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            # Parse header prefix for event/time/node/direction
            prefix = header_prefix_pattern.search(line)
            if not prefix:
                continue
            event = prefix.group('event')
            time_s = float(prefix.group('time'))
            node = int(prefix.group('node'))
            direction = prefix.group('direction')

            # Find all IPv4 headers on the line (outer + possible inner over GTP-U)
            ipv4_matches = list(ipv4_any_pattern.finditer(line))
            if not ipv4_matches:
                continue

            # Prefer the innermost IPv4 header when multiple are present (common with LTE GTP-U)
            gtpu_match = gtpu_pattern.search(line)
            chosen = ipv4_matches[-1] if len(ipv4_matches) >= 2 else ipv4_matches[0]

            protocol = int(chosen.group('protocol'))
            ip_id = int(chosen.group('ip_id'))
            length = int(chosen.group('length'))
            src_ip = chosen.group('src_ip')
            dst_ip = chosen.group('dst_ip')
            
            # Determine L4 protocol
            l4_proto = 'OTHER'
            src_port = None
            dst_port = None
            
            # Search L4 headers AFTER the chosen IPv4 header to bind the correct ports
            tail = line[chosen.end():]
            if protocol == 17:  # UDP
                l4_proto = 'UDP'
                udp_match = udp_pattern.search(tail)
                if udp_match:
                    src_port = int(udp_match.group('src_port'))
                    dst_port = int(udp_match.group('dst_port'))
            elif protocol == 6:  # TCP
                l4_proto = 'TCP'
                tcp_match = tcp_pattern.search(tail)
                if tcp_match:
                    src_port = int(tcp_match.group('src_port'))
                    dst_port = int(tcp_match.group('dst_port'))
            
            # Check for GTP-U tunnel (LTE encapsulation). If GTP header isn't printed,
            # treat multiple IPv4 headers as a proxy for tunneling.
            is_tunneled = bool(gtpu_match) or (len(ipv4_matches) >= 2)
            teid = int(gtpu_match.group('teid')) if gtpu_match else None
            
            records.append({
                'event': event,
                'time': time_s,
                'node': node,
                'direction': direction,
                'protocol': l4_proto,
                'ip_id': ip_id,
                'length': length,
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'src_port': src_port,
                'dst_port': dst_port,
                'is_tunneled': is_tunneled,
                'teid': teid
            })
            
            if line_num % 10000 == 0:
                print(f"  Processed {line_num} lines, found {len(records)} packets...")
    
    df = pd.DataFrame(records)
    print(f"✓ Parsed {len(df)} packets from {line_num} lines")
    return df

def analyze_udp_flows(df):
    """Analyze UDP flows"""
    udp_df = df[df['protocol'] == 'UDP'].copy()
    
    if udp_df.empty:
        print("No UDP packets found!")
        return None
    
    print(f"\n=== UDP Analysis ===")
    print(f"Total UDP packets: {len(udp_df)}")
    
    # Group by flow (src_ip, dst_ip, dst_port)
    udp_df['flow'] = udp_df['src_ip'] + ' > ' + udp_df['dst_ip'] + ':' + udp_df['dst_port'].astype(str)
    
    flow_stats = []
    for flow_name, group in udp_df.groupby('flow'):
        tx_packets = len(group[group['event'] == 't'])
        rx_packets = len(group[group['event'] == 'r'])
        total_bytes = group['length'].sum()
        duration = group['time'].max() - group['time'].min()
        throughput_mbps = (total_bytes * 8 / 1e6) / duration if duration > 0 else 0
        
        flow_stats.append({
            'flow': flow_name,
            'tx_packets': tx_packets,
            'rx_packets': rx_packets,
            'delivery_ratio': rx_packets / tx_packets if tx_packets > 0 else 0,
            'total_bytes': total_bytes,
            'duration_s': duration,
            'throughput_mbps': throughput_mbps
        })
    
    flow_df = pd.DataFrame(flow_stats)
    print(flow_df.to_string())
    return flow_df

def analyze_tcp_flows(df):
    """Analyze TCP flows"""
    tcp_df = df[df['protocol'] == 'TCP'].copy()
    
    if tcp_df.empty:
        print("\nNo TCP packets found!")
        return None
    
    print(f"\n=== TCP Analysis ===")
    print(f"Total TCP packets: {len(tcp_df)}")
    
    # Group by flow
    tcp_df['flow'] = tcp_df['src_ip'] + ' > ' + tcp_df['dst_ip'] + ':' + tcp_df['dst_port'].astype(str)
    
    flow_stats = []
    for flow_name, group in tcp_df.groupby('flow'):
        tx_packets = len(group[group['event'] == 't'])
        rx_packets = len(group[group['event'] == 'r'])
        total_bytes = group['length'].sum()
        duration = group['time'].max() - group['time'].min()
        throughput_mbps = (total_bytes * 8 / 1e6) / duration if duration > 0 else 0
        
        flow_stats.append({
            'flow': flow_name,
            'tx_packets': tx_packets,
            'rx_packets': rx_packets,
            'delivery_ratio': rx_packets / tx_packets if tx_packets > 0 else 0,
            'total_bytes': total_bytes,
            'duration_s': duration,
            'throughput_mbps': throughput_mbps
        })
    
    flow_df = pd.DataFrame(flow_stats)
    print(flow_df.to_string())
    return flow_df

def plot_throughput_over_time(df, output_dir):
    """Plot throughput over time for UDP and TCP"""
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # UDP throughput
    udp_df = df[(df['protocol'] == 'UDP') & (df['event'] == 't')]
    if not udp_df.empty:
        bins = np.arange(0, udp_df['time'].max() + 0.5, 0.5)
        udp_df['time_bin'] = pd.cut(udp_df['time'], bins=bins)
        throughput = udp_df.groupby('time_bin')['length'].sum() * 8 / 1e6 / 0.5  # Mbps
        
        bin_centers = [(interval.left + interval.right) / 2 for interval in throughput.index]
        ax1.plot(bin_centers, throughput.values, 'b-o', linewidth=2, markersize=4)
        ax1.set_title('UDP Throughput Over Time', fontsize=14, weight='bold')
        ax1.set_xlabel('Time (s)', fontsize=12)
        ax1.set_ylabel('Throughput (Mbps)', fontsize=12)
        ax1.grid(True, alpha=0.3)
    else:
        ax1.text(0.5, 0.5, 'No UDP Data', ha='center', va='center', transform=ax1.transAxes)
    
    # TCP throughput
    tcp_df = df[(df['protocol'] == 'TCP') & (df['event'] == 't')]
    if not tcp_df.empty:
        bins = np.arange(0, tcp_df['time'].max() + 0.5, 0.5)
        tcp_df['time_bin'] = pd.cut(tcp_df['time'], bins=bins)
        throughput = tcp_df.groupby('time_bin')['length'].sum() * 8 / 1e6 / 0.5  # Mbps
        
        bin_centers = [(interval.left + interval.right) / 2 for interval in throughput.index]
        ax2.plot(bin_centers, throughput.values, 'r-o', linewidth=2, markersize=4)
        ax2.set_title('TCP Throughput Over Time', fontsize=14, weight='bold')
        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Throughput (Mbps)', fontsize=12)
        ax2.grid(True, alpha=0.3)
    else:
        # Try to get TCP data from PCAP files
        print("No TCP in IPv4 traces, trying PCAP files...")
        tcp_pcap_data = get_tcp_from_pcaps(output_dir)
        print(f"Found {len(tcp_pcap_data)} TCP packets in PCAP files")
        if not tcp_pcap_data.empty:
            bins = np.arange(0, tcp_pcap_data['time'].max() + 0.5, 0.5)
            tcp_pcap_data['time_bin'] = pd.cut(tcp_pcap_data['time'], bins=bins)
            throughput = tcp_pcap_data.groupby('time_bin')['length'].sum() * 8 / 1e6 / 0.5  # Mbps
            
            bin_centers = [(interval.left + interval.right) / 2 for interval in throughput.index]
            ax2.plot(bin_centers, throughput.values, 'r-o', linewidth=2, markersize=4)
            ax2.set_title('TCP Throughput Over Time (from PCAP)', fontsize=14, weight='bold')
            ax2.set_xlabel('Time (s)', fontsize=12)
            ax2.set_ylabel('Throughput (Mbps)', fontsize=12)
            ax2.grid(True, alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'No TCP Data', ha='center', va='center', transform=ax2.transAxes)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'lte_throughput_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

def main():
    print("LTE IPv4 L3 Trace Analyzer")
    print("=" * 60)
    
    # Parse traces
    df = parse_ipv4_l3_traces(IPV4_L3_FILE)
    
    if df.empty:
        print("No data to analyze!")
        return
    
    # Save raw parsed data
    csv_file = os.path.join(OUTPUT_DIR, 'lte_ipv4_parsed.csv')
    df.to_csv(csv_file, index=False)
    print(f"✓ Saved parsed data: {csv_file}")
    
    # Analyze UDP flows
    udp_flows = analyze_udp_flows(df)
    if udp_flows is not None:
        udp_flows.to_csv(os.path.join(OUTPUT_DIR, 'lte_udp_flows.csv'), index=False)
    
    # Analyze TCP flows
    tcp_flows = analyze_tcp_flows(df)
    if tcp_flows is not None:
        tcp_flows.to_csv(os.path.join(OUTPUT_DIR, 'lte_tcp_flows.csv'), index=False)
    
    # Plot throughput
    plot_throughput_over_time(df, OUTPUT_DIR)
    
    # Summary statistics
    print(f"\n=== Overall Statistics ===")
    print(f"Total packets: {len(df)}")
    print(f"UDP packets: {len(df[df['protocol'] == 'UDP'])}")
    print(f"TCP packets: {len(df[df['protocol'] == 'TCP'])}")
    print(f"Tunneled packets (GTP-U): {df['is_tunneled'].sum()}")
    print(f"Unique nodes: {df['node'].nunique()}")
    print(f"Simulation duration: {df['time'].max():.2f}s")
    
    print(f"\n✓ Analysis complete! Results saved in {OUTPUT_DIR}/")

def get_tcp_from_pcaps(output_dir):
    """Extract TCP data from PCAP files using tshark"""
    pcap_files = glob.glob(os.path.join(output_dir, "lte_playfield_rw_pcap*.pcap"))
    if not pcap_files:
        return pd.DataFrame()
    
    all_data = []
    for pcap_file in pcap_files:
        try:
            # Use tshark to extract TCP data
            cmd = [
                'tshark', '-r', pcap_file, '-T', 'fields',
                '-e', 'frame.time_relative',
                '-e', 'frame.len',
                '-Y', 'tcp'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                continue
            
            lines = result.stdout.strip().split('\n')
            if not lines or lines == ['']:
                continue
            
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        all_data.append({
                            'time': float(parts[0]) if parts[0] else 0.0,
                            'length': int(parts[1]) if parts[1] else 0
                        })
                    except (ValueError, IndexError):
                        continue
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    return pd.DataFrame(all_data)

if __name__ == "__main__":
    main()

