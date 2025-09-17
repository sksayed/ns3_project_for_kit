#!/usr/bin/env python3
"""
PCAP TCP Path Analyzer for LTE Networks
Analyzes PCAP files to extract TCP connection paths and performance metrics.
"""

import os
import glob
import subprocess
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import re

def run_tshark_analysis(pcap_file):
    """Run tshark analysis on PCAP file to extract TCP information."""
    try:
        # Use tshark to extract TCP stream information
        cmd = [
            'tshark', '-r', pcap_file, '-T', 'fields',
            '-e', 'frame.time_relative',
            '-e', 'ip.src',
            '-e', 'ip.dst',
            '-e', 'tcp.srcport',
            '-e', 'tcp.dstport',
            '-e', 'tcp.stream',
            '-e', 'frame.len',
            '-e', 'tcp.flags',
            '-Y', 'tcp'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"tshark failed: {result.stderr}")
            return None
        
        lines = result.stdout.strip().split('\n')
        if not lines or lines == ['']:
            return None
        
        data = []
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 7:
                try:
                    data.append({
                        'time': float(parts[0]) if parts[0] else 0.0,
                        'src_ip': parts[1] if parts[1] else '',
                        'dst_ip': parts[2] if parts[2] else '',
                        'src_port': int(parts[3]) if parts[3] else 0,
                        'dst_port': int(parts[4]) if parts[4] else 0,
                        'stream_id': int(parts[5]) if parts[5] else 0,
                        'length': int(parts[6]) if parts[6] else 0,
                        'flags': parts[7] if len(parts) > 7 else ''
                    })
                except (ValueError, IndexError):
                    continue
        
        return pd.DataFrame(data)
    
    except subprocess.TimeoutExpired:
        print(f"tshark timeout for {pcap_file}")
        return None
    except Exception as e:
        print(f"Error running tshark on {pcap_file}: {e}")
        return None

def analyze_tcp_streams(df):
    """Analyze TCP streams to extract connection paths and metrics."""
    if df is None or df.empty:
        return None
    
    streams = {}
    
    for _, row in df.iterrows():
        stream_id = row['stream_id']
        if stream_id not in streams:
            streams[stream_id] = {
                'src_ip': row['src_ip'],
                'dst_ip': row['dst_ip'],
                'src_port': row['src_port'],
                'dst_port': row['dst_port'],
                'packets': [],
                'start_time': row['time'],
                'end_time': row['time'],
                'total_bytes': 0
            }
        
        streams[stream_id]['packets'].append({
            'time': row['time'],
            'length': row['length'],
            'flags': row['flags']
        })
        streams[stream_id]['end_time'] = max(streams[stream_id]['end_time'], row['time'])
        streams[stream_id]['total_bytes'] += row['length']
    
    # Convert to DataFrame
    stream_data = []
    for stream_id, stream_info in streams.items():
        duration = stream_info['end_time'] - stream_info['start_time']
        throughput = (stream_info['total_bytes'] * 8) / (duration * 1e6) if duration > 0 else 0
        
        stream_data.append({
            'stream_id': stream_id,
            'src_ip': stream_info['src_ip'],
            'dst_ip': stream_info['dst_ip'],
            'src_port': stream_info['src_port'],
            'dst_port': stream_info['dst_port'],
            'duration': duration,
            'total_bytes': stream_info['total_bytes'],
            'throughput_mbps': throughput,
            'packet_count': len(stream_info['packets'])
        })
    
    return pd.DataFrame(stream_data)

def create_tcp_analysis_plots(streams_df, output_dir):
    """Create plots for TCP analysis."""
    if streams_df is None or streams_df.empty:
        print("No TCP streams found for analysis")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('LTE TCP Stream Analysis', fontsize=16, fontweight='bold')
    
    # 1. Throughput by stream
    ax1 = axes[0, 0]
    ax1.bar(streams_df['stream_id'], streams_df['throughput_mbps'], 
           color='skyblue', alpha=0.7)
    ax1.set_xlabel('Stream ID')
    ax1.set_ylabel('Throughput (Mbps)')
    ax1.set_title('TCP Throughput by Stream')
    ax1.grid(True, alpha=0.3)
    
    # 2. Duration vs Throughput
    ax2 = axes[0, 1]
    scatter = ax2.scatter(streams_df['duration'], streams_df['throughput_mbps'], 
                         c=streams_df['total_bytes'], cmap='viridis', 
                         alpha=0.7, s=100)
    ax2.set_xlabel('Duration (s)')
    ax2.set_ylabel('Throughput (Mbps)')
    ax2.set_title('Duration vs Throughput (colored by total bytes)')
    ax2.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax2, label='Total Bytes')
    
    # 3. Packet count distribution
    ax3 = axes[1, 0]
    ax3.hist(streams_df['packet_count'], bins=15, color='lightgreen', 
            alpha=0.7, edgecolor='black')
    ax3.set_xlabel('Packet Count')
    ax3.set_ylabel('Number of Streams')
    ax3.set_title('Packet Count Distribution')
    ax3.grid(True, alpha=0.3)
    
    # 4. Bytes transferred by stream
    ax4 = axes[1, 1]
    ax4.bar(streams_df['stream_id'], streams_df['total_bytes'] / 1e6, 
           color='salmon', alpha=0.7)
    ax4.set_xlabel('Stream ID')
    ax4.set_ylabel('Total Bytes (MB)')
    ax4.set_title('Bytes Transferred by Stream')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'tcp_analysis.png'), dpi=300, bbox_inches='tight')
    plt.close()

def analyze_pcap_files(output_dir):
    """Analyze all PCAP files in the output directory."""
    pcap_files = glob.glob(os.path.join(output_dir, "lte_playfield_rw_pcap*.pcap"))
    
    if not pcap_files:
        print("No PCAP files found in", output_dir)
        return
    
    print(f"Found {len(pcap_files)} PCAP files")
    
    all_streams = []
    
    for pcap_file in pcap_files:
        print(f"Analyzing {os.path.basename(pcap_file)}...")
        
        # Run tshark analysis
        df = run_tshark_analysis(pcap_file)
        if df is not None and not df.empty:
            # Analyze TCP streams
            streams_df = analyze_tcp_streams(df)
            if streams_df is not None and not streams_df.empty:
                all_streams.append(streams_df)
    
    if all_streams:
        # Combine all stream data
        combined_streams = pd.concat(all_streams, ignore_index=True)
        
        # Save results
        combined_streams.to_csv(os.path.join(output_dir, 'tcp_streams_analysis.csv'), index=False)
        
        # Create plots
        create_tcp_analysis_plots(combined_streams, output_dir)
        
        # Print summary
        print(f"\nTCP Analysis Summary:")
        print(f"Total streams: {len(combined_streams)}")
        print(f"Average throughput: {combined_streams['throughput_mbps'].mean():.2f} Mbps")
        print(f"Total bytes transferred: {combined_streams['total_bytes'].sum() / 1e6:.2f} MB")
        print(f"Average stream duration: {combined_streams['duration'].mean():.2f} seconds")
        
        print(f"\nResults saved to:")
        print(f"- {output_dir}/tcp_streams_analysis.csv")
        print(f"- {output_dir}/tcp_analysis.png")
    else:
        print("No TCP streams found in PCAP files")

def main():
    """Main function."""
    output_dir = "Lte_outputs"
    
    if not os.path.exists(output_dir):
        print(f"Output directory {output_dir} does not exist.")
        return
    
    # Check if tshark is available
    try:
        subprocess.run(['tshark', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("tshark not found. Please install Wireshark/tshark to analyze PCAP files.")
        return
    
    analyze_pcap_files(output_dir)

if __name__ == "__main__":
    main()
