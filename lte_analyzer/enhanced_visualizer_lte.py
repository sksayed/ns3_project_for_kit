#!/usr/bin/env python3
"""
Enhanced LTE Network Visualizer
Creates comprehensive analysis reports and visualizations for LTE network simulations.
"""

import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import glob
import xml.etree.ElementTree as ET

def parse_flowmon_xml(xml_file):
    """Parse FlowMonitor XML file and return DataFrame."""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        flows = []
        for flow in root.findall('.//Flow'):
            flow_id = int(flow.get('flowId', -1))
            if flow_id < 0:
                continue
                
            # Parse time values
            def parse_time(value):
                if value is None:
                    return 0.0
                v = str(value).strip()
                if v.endswith('ns'):
                    return float(v[:-2]) / 1e9
                if v.endswith('us'):
                    return float(v[:-2]) / 1e6
                if v.endswith('ms'):
                    return float(v[:-2]) / 1e3
                if v.endswith('s'):
                    return float(v[:-1])
                return float(v)
            
            flow_data = {
                'flowId': flow_id,
                'timeFirstTxPacket': parse_time(flow.get('timeFirstTxPacket')),
                'timeLastTxPacket': parse_time(flow.get('timeLastTxPacket')),
                'txBytes': int(flow.get('txBytes', 0)),
                'rxBytes': int(flow.get('rxBytes', 0)),
                'txPackets': int(flow.get('txPackets', 0)),
                'rxPackets': int(flow.get('rxPackets', 0)),
                'avg_delay': parse_time(flow.get('delaySum')) / max(int(flow.get('rxPackets', 1)), 1) * 1000,  # Convert to ms
                'avg_jitter': parse_time(flow.get('jitterSum')) / max(int(flow.get('rxPackets', 1)), 1) * 1000,  # Convert to ms
            }
            
            # Calculate throughput and loss rate
            duration = flow_data['timeLastTxPacket'] - flow_data['timeFirstTxPacket']
            flow_data['duration'] = max(duration, 0.001)
            flow_data['throughput_mbps'] = (flow_data['rxBytes'] * 8) / (flow_data['duration'] * 1e6)
            flow_data['loss_rate'] = ((flow_data['txPackets'] - flow_data['rxPackets']) / max(flow_data['txPackets'], 1)) * 100
            
            flows.append(flow_data)
        
        return pd.DataFrame(flows)
    except Exception as e:
        print(f"Error parsing FlowMonitor XML: {e}")
        return pd.DataFrame()

def create_analysis_report():
    """Create a comprehensive HTML analysis report for LTE outputs only."""
    output_dir = "Lte_outputs"
    if not os.path.exists(output_dir):
        print(f"Error: Output directory {output_dir} not found. Please run the LTE simulation first.")
        return
    print(f"Using output directory: {output_dir}")
    
    # Check if required files exist
    required_files = [
        "traces_parsed.csv",
        "tr_summary.csv", 
        "tr_by_rate.csv",
        "tr_udp_ports.csv"
    ]
    
    # Check for flowmon file (CSV or LTE XML)
    flowmon_files = ["flowmon_analysis.csv", "flowmon-lte-playfield-rw.xml"]
    flowmon_file = None
    for file in flowmon_files:
        if os.path.exists(os.path.join(output_dir, file)):
            flowmon_file = file
            break
    
    if flowmon_file:
        required_files.append(flowmon_file)
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(output_dir, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"Warning: Missing files: {missing_files}")
        print(f"Available files in {output_dir}:")
        for f in os.listdir(output_dir):
            print(f"  - {f}")
        return
    
    # Load data
    try:
        traces_df = pd.read_csv(os.path.join(output_dir, "traces_parsed.csv"))
        summary_df = pd.read_csv(os.path.join(output_dir, "tr_summary.csv"))
        rate_df = pd.read_csv(os.path.join(output_dir, "tr_by_rate.csv"))
        udp_ports_df = pd.read_csv(os.path.join(output_dir, "tr_udp_ports.csv"))
        
        # Handle flowmon data (CSV or XML)
        if flowmon_file.endswith('.csv'):
            flowmon_df = pd.read_csv(os.path.join(output_dir, flowmon_file))
        else:
            # Parse XML flowmon file
            flowmon_df = parse_flowmon_xml(os.path.join(output_dir, flowmon_file))
            
    except Exception as e:
        print(f"Error loading data: {e}")
        return
    
    # Create performance dashboard
    create_performance_dashboard(traces_df, flowmon_df, output_dir)
    
    # Create network topology visualization
    create_network_topology_plot(output_dir)
    
    # Create throughput heatmap
    create_throughput_heatmap(traces_df, output_dir)
    
    # Generate HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LTE Network Analysis Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 3px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            img {{ max-width: 100%; height: auto; margin: 10px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>LTE Network Analysis Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="section">
            <h2>Key Performance Metrics</h2>
            <div class="metric">
                <div class="metric-value">{len(traces_df):,}</div>
                <div class="metric-label">Total Frames</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(flowmon_df)}</div>
                <div class="metric-label">Active Flows</div>
            </div>
            <div class="metric">
                <div class="metric-value">{flowmon_df['throughput_mbps'].mean():.2f}</div>
                <div class="metric-label">Avg Throughput (Mbps)</div>
            </div>
            <div class="metric">
                <div class="metric-value">{flowmon_df['avg_delay'].mean():.2f}</div>
                <div class="metric-label">Avg Delay (ms)</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Performance Dashboard</h2>
            <img src="performance_dashboard.png" alt="Performance Dashboard">
        </div>
        
        <div class="section">
            <h2>Network Topology</h2>
            <img src="network_topology.png" alt="Network Topology">
        </div>
        
        <div class="section">
            <h2>Throughput Analysis</h2>
            <img src="throughput_heatmap.png" alt="Throughput Heatmap">
        </div>
        
        <div class="section">
            <h2>Flow Statistics</h2>
            {flowmon_df.to_html(classes='table', index=False, escape=False)}
        </div>
        
        <div class="section">
            <h2>Rate Distribution</h2>
            {rate_df.to_html(classes='table', index=False, escape=False)}
        </div>
        
        <div class="section">
            <h2>UDP Port Analysis</h2>
            {udp_ports_df.to_html(classes='table', index=False, escape=False)}
        </div>
    </body>
    </html>
    """
    
    with open(os.path.join(output_dir, "analysis_report.html"), "w") as f:
        f.write(html_content)
    
    print(f"Analysis report generated: {output_dir}/analysis_report.html")

def create_performance_dashboard(traces_df, flowmon_df, output_dir):
    """Create a comprehensive performance dashboard."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('LTE Network Performance Dashboard', fontsize=16, fontweight='bold')
    
    # 1. Frame rate distribution over time
    ax1 = axes[0, 0]
    if not traces_df.empty and 'time' in traces_df.columns:
        time_bins = np.arange(traces_df['time'].min(), traces_df['time'].max() + 1, 1)
        frame_counts = traces_df.groupby(pd.cut(traces_df['time'], time_bins)).size()
        ax1.plot(time_bins[:-1], frame_counts.values, 'b-', linewidth=2)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Frames per Second')
        ax1.set_title('Frame Rate Over Time')
        ax1.grid(True, alpha=0.3)
    
    # 2. Throughput by flow
    ax2 = axes[0, 1]
    if not flowmon_df.empty and 'throughput_mbps' in flowmon_df.columns:
        ax2.bar(range(len(flowmon_df)), flowmon_df['throughput_mbps'], color='skyblue', alpha=0.7)
        ax2.set_xlabel('Flow ID')
        ax2.set_ylabel('Throughput (Mbps)')
        ax2.set_title('Throughput by Flow')
        ax2.grid(True, alpha=0.3)
    
    # 3. Delay distribution
    ax3 = axes[0, 2]
    if not flowmon_df.empty and 'avg_delay' in flowmon_df.columns:
        ax3.hist(flowmon_df['avg_delay'], bins=15, color='lightgreen', alpha=0.7, edgecolor='black')
        ax3.set_xlabel('Delay (ms)')
        ax3.set_ylabel('Number of Flows')
        ax3.set_title('Delay Distribution')
        ax3.grid(True, alpha=0.3)
    
    # 4. Packet loss rate
    ax4 = axes[1, 0]
    if not flowmon_df.empty and 'loss_rate' in flowmon_df.columns:
        ax4.bar(range(len(flowmon_df)), flowmon_df['loss_rate'], color='salmon', alpha=0.7)
        ax4.set_xlabel('Flow ID')
        ax4.set_ylabel('Packet Loss Rate (%)')
        ax4.set_title('Packet Loss Rate by Flow')
        ax4.grid(True, alpha=0.3)
    
    # 5. Jitter analysis
    ax5 = axes[1, 1]
    if not flowmon_df.empty and 'avg_jitter' in flowmon_df.columns:
        ax5.scatter(flowmon_df['avg_delay'], flowmon_df['avg_jitter'], 
                   c=flowmon_df['throughput_mbps'], cmap='viridis', alpha=0.7, s=100)
        ax5.set_xlabel('Average Delay (ms)')
        ax5.set_ylabel('Average Jitter (ms)')
        ax5.set_title('Delay vs Jitter (colored by throughput)')
        ax5.grid(True, alpha=0.3)
        plt.colorbar(ax5.collections[0], ax=ax5, label='Throughput (Mbps)')
    
    # 6. Bytes transmitted vs received
    ax6 = axes[1, 2]
    if not flowmon_df.empty and 'txBytes' in flowmon_df.columns and 'rxBytes' in flowmon_df.columns:
        x = np.arange(len(flowmon_df))
        width = 0.35
        ax6.bar(x - width/2, flowmon_df['txBytes']/1e6, width, label='Transmitted (MB)', alpha=0.8)
        ax6.bar(x + width/2, flowmon_df['rxBytes']/1e6, width, label='Received (MB)', alpha=0.8)
        ax6.set_xlabel('Flow ID')
        ax6.set_ylabel('Bytes (MB)')
        ax6.set_title('Bytes Transmitted vs Received')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'performance_dashboard.png'), dpi=300, bbox_inches='tight')
    plt.close()

def create_network_topology_plot(output_dir):
    """Create a network topology visualization."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # Create a simple network topology representation
    # This is a placeholder - in a real implementation, you would parse
    # the actual network configuration from the simulation files
    
    # Simulate 10 UEs in a 400x400 field
    field_size = 400
    n_ues = 10
    
    # Position UEs along diagonal
    x_positions = np.linspace(0, field_size, n_ues)
    y_positions = np.linspace(0, field_size, n_ues)
    
    # Plot UEs
    ax.scatter(x_positions, y_positions, c='blue', s=100, label='UEs', zorder=3)
    
    # Plot eNBs
    enb_x = [field_size * 0.25, field_size * 0.75]
    enb_y = [field_size * 0.5, field_size * 0.5]
    ax.scatter(enb_x, enb_y, c='red', s=200, marker='^', label='eNBs', zorder=3)
    
    # Add buildings (obstacles)
    building_positions = [
        (30, 100, 60, 8),  # leftBelow
        (340, 100, 60, 8), # rightBelow
        (30, 300, 60, 8),  # leftAbove
        (340, 300, 60, 8), # rightAbove
        (110, 250, 60, 8), # cluster250a
        (200, 250, 80, 8), # cluster250b
        (300, 50, 80, 8),  # cluster50
    ]
    
    for x, y, w, h in building_positions:
        rect = plt.Rectangle((x, y), w, h, facecolor='gray', alpha=0.7, zorder=2)
        ax.add_patch(rect)
    
    # Add connections (simplified)
    for i in range(n_ues):
        # Connect to nearest eNB
        dist_to_enb1 = np.sqrt((x_positions[i] - enb_x[0])**2 + (y_positions[i] - enb_y[0])**2)
        dist_to_enb2 = np.sqrt((x_positions[i] - enb_x[1])**2 + (y_positions[i] - enb_y[1])**2)
        
        if dist_to_enb1 < dist_to_enb2:
            ax.plot([x_positions[i], enb_x[0]], [y_positions[i], enb_y[0]], 
                   'k--', alpha=0.3, linewidth=1)
        else:
            ax.plot([x_positions[i], enb_x[1]], [y_positions[i], enb_y[1]], 
                   'k--', alpha=0.3, linewidth=1)
    
    # Label special nodes
    ax.annotate('Sayed (UE0)', (x_positions[0], y_positions[0]), 
               xytext=(10, 10), textcoords='offset points', fontsize=10, fontweight='bold')
    ax.annotate('Sadia (UE9)', (x_positions[-1], y_positions[-1]), 
               xytext=(10, 10), textcoords='offset points', fontsize=10, fontweight='bold')
    
    ax.set_xlim(-20, field_size + 20)
    ax.set_ylim(-20, field_size + 20)
    ax.set_xlabel('X Position (m)')
    ax.set_ylabel('Y Position (m)')
    ax.set_title('LTE Network Topology')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'network_topology.png'), dpi=300, bbox_inches='tight')
    plt.close()

def create_throughput_heatmap(traces_df, output_dir):
    """Create a throughput heatmap visualization."""
    if traces_df.empty or 'time' not in traces_df.columns or 'node' not in traces_df.columns:
        print("Insufficient data for throughput heatmap")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # Create time bins
    time_bins = np.arange(traces_df['time'].min(), traces_df['time'].max() + 1, 1)
    
    # Calculate throughput for each node over time
    throughput_data = []
    for node in sorted(traces_df['node'].dropna().unique()):
        node_data = traces_df[traces_df['node'] == node]
        node_throughput = []
        
        for i in range(len(time_bins) - 1):
            time_mask = (node_data['time'] >= time_bins[i]) & (node_data['time'] < time_bins[i+1])
            period_data = node_data[time_mask]
            
            if 'length' in period_data.columns:
                total_bytes = period_data['length'].sum()
                throughput_mbps = (total_bytes * 8) / 1e6  # Convert to Mbps
            else:
                throughput_mbps = 0
            
            node_throughput.append(throughput_mbps)
        
        throughput_data.append(node_throughput)
    
    # Create heatmap
    if throughput_data:
        throughput_array = np.array(throughput_data)
        im = ax.imshow(throughput_array, cmap='YlOrRd', aspect='auto', interpolation='nearest')
        
        # Set labels
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Node ID')
        ax.set_title('Throughput Heatmap (Mbps)')
        
        # Set tick labels
        tick_step = max(1, len(time_bins)//10)
        ax.set_xticks(range(0, len(time_bins)-1, tick_step))
        ax.set_xticklabels([f'{int(t)}' for t in time_bins[::tick_step][:len(range(0, len(time_bins)-1, tick_step))]])
        ax.set_yticks(range(len(throughput_data)))
        ax.set_yticklabels([f'Node {i}' for i in sorted(traces_df['node'].dropna().unique())])
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Throughput (Mbps)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'throughput_heatmap.png'), dpi=300, bbox_inches='tight')
    plt.close()

def main():
    """Main function to run the enhanced visualizer."""
    print("Running Enhanced Visualizer...")
    
    # Create analysis report
    create_analysis_report()
    
    print("Enhanced visualizer completed successfully!")

if __name__ == "__main__":
    main()
