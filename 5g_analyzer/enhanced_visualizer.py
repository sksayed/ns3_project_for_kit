#!/usr/bin/env python3
"""
Enhanced 5G Network Analysis and Visualization
Generates comprehensive reports and visualizations for 5G simulation results.
"""

import os
import glob
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

# Set style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

OUT_DIR = "5g_outputs"

def load_flowmon_data():
    """Load FlowMonitor analysis data."""
    csv_path = os.path.join(OUT_DIR, "flowmon_analysis.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

def load_trace_data():
    """Load trace analysis data."""
    csv_path = os.path.join(OUT_DIR, "traces_parsed.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

def create_network_topology_plot(flow_df, trace_df, out_dir):
    """Create network topology visualization."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Extract unique nodes from trace data
    if not trace_df.empty and 'node' in trace_df.columns:
        nodes = sorted(trace_df['node'].dropna().unique())
        n_nodes = len(nodes)
        
        # Create circular layout for nodes
        angles = np.linspace(0, 2*np.pi, n_nodes, endpoint=False)
        radius = 3
        x_pos = radius * np.cos(angles)
        y_pos = radius * np.sin(angles)
        
        # Plot nodes
        ax.scatter(x_pos, y_pos, s=200, c='lightblue', edgecolors='black', linewidth=2, zorder=3)
        
        # Label nodes
        for i, (x, y, node) in enumerate(zip(x_pos, y_pos, nodes)):
            ax.annotate(f'Node {int(node)}', (x, y), xytext=(5, 5), 
                       textcoords='offset points', fontsize=10, fontweight='bold')
        
        # Draw connections based on flow data
        if not flow_df.empty:
            for _, flow in flow_df.iterrows():
                # Simple connection visualization
                if flow['txBytes'] > 0 and flow['rxBytes'] > 0:
                    # Draw a line to indicate connectivity
                    ax.plot([-3, 3], [0, 0], 'k--', alpha=0.3, linewidth=1)
    
    ax.set_xlim(-4, 4)
    ax.set_ylim(-4, 4)
    ax.set_aspect('equal')
    ax.set_title('5G Network Topology', fontsize=16, fontweight='bold')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'network_topology.png'), dpi=300, bbox_inches='tight')
    plt.close()

def create_performance_dashboard(flow_df, trace_df, out_dir):
    """Create comprehensive performance dashboard."""
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    
    # 1. Throughput Distribution
    ax1 = fig.add_subplot(gs[0, 0])
    if not flow_df.empty and 'throughput_mbps' in flow_df.columns:
        flow_df['throughput_mbps'].hist(bins=10, ax=ax1, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.set_title('5G Throughput Distribution', fontweight='bold')
        ax1.set_xlabel('Throughput (Mbps)')
        ax1.set_ylabel('Number of Flows')
        ax1.grid(True, alpha=0.3)
    
    # 2. Delay vs Jitter Scatter
    ax2 = fig.add_subplot(gs[0, 1])
    if not flow_df.empty and 'avg_delay' in flow_df.columns and 'avg_jitter' in flow_df.columns:
        scatter = ax2.scatter(flow_df['avg_delay'], flow_df['avg_jitter'], 
                            c=flow_df['throughput_mbps'] if 'throughput_mbps' in flow_df.columns else 'blue',
                            s=100, alpha=0.7, cmap='viridis')
        ax2.set_xlabel('Average Delay (ms)')
        ax2.set_ylabel('Average Jitter (ms)')
        ax2.set_title('5G Delay vs Jitter', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        if 'throughput_mbps' in flow_df.columns:
            plt.colorbar(scatter, ax=ax2, label='Throughput (Mbps)')
    
    # 3. Packet Loss Analysis
    ax3 = fig.add_subplot(gs[0, 2])
    if not flow_df.empty and 'loss_rate' in flow_df.columns:
        loss_categories = pd.cut(flow_df['loss_rate'], bins=[0, 1, 5, 10, 100], 
                               labels=['<1%', '1-5%', '5-10%', '>10%'])
        loss_counts = loss_categories.value_counts()
        loss_counts.plot(kind='bar', ax=ax3, color='coral', alpha=0.7)
        ax3.set_title('5G Packet Loss Categories', fontweight='bold')
        ax3.set_xlabel('Loss Rate Range')
        ax3.set_ylabel('Number of Flows')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
    
    # 4. Data Volume Analysis
    ax4 = fig.add_subplot(gs[0, 3])
    if not flow_df.empty and 'txBytes' in flow_df.columns and 'rxBytes' in flow_df.columns:
        x = np.arange(len(flow_df))
        width = 0.35
        ax4.bar(x - width/2, flow_df['txBytes']/1e6, width, label='Transmitted', alpha=0.8, color='lightcoral')
        ax4.bar(x + width/2, flow_df['rxBytes']/1e6, width, label='Received', alpha=0.8, color='lightgreen')
        ax4.set_xlabel('Flow ID')
        ax4.set_ylabel('Data Volume (MB)')
        ax4.set_title('5G Data Volume by Flow', fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    
    # 5. Time Series Analysis (if trace data available)
    ax5 = fig.add_subplot(gs[1, :2])
    if not trace_df.empty and 'time' in trace_df.columns and 'event' in trace_df.columns:
        # Create time series of packet events
        time_bins = np.arange(trace_df['time'].min(), trace_df['time'].max() + 1, 0.5)
        tx_events = trace_df[trace_df['event'] == 't']['time']
        rx_events = trace_df[trace_df['event'] == 'r']['time']
        
        ax5.hist(tx_events, bins=time_bins, alpha=0.7, label='Transmitted', color='red', density=True)
        ax5.hist(rx_events, bins=time_bins, alpha=0.7, label='Received', color='green', density=True)
        ax5.set_xlabel('Time (seconds)')
        ax5.set_ylabel('Packet Density')
        ax5.set_title('5G Packet Activity Over Time', fontweight='bold')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
    
    # 6. Protocol Distribution
    ax6 = fig.add_subplot(gs[1, 2:])
    if not trace_df.empty and 'l4' in trace_df.columns:
        protocol_counts = trace_df['l4'].value_counts()
        protocol_counts.plot(kind='pie', ax=ax6, autopct='%1.1f%%', startangle=90)
        ax6.set_title('5G Protocol Distribution', fontweight='bold')
        ax6.set_ylabel('')
    
    # 7. Node Activity Heatmap
    ax7 = fig.add_subplot(gs[2, :2])
    if not trace_df.empty and 'node' in trace_df.columns and 'time' in trace_df.columns:
        # Create a heatmap of node activity over time
        time_bins = np.arange(trace_df['time'].min(), trace_df['time'].max() + 1, 1.0)
        node_activity = []
        for node in sorted(trace_df['node'].dropna().unique()):
            node_data = trace_df[trace_df['node'] == node]
            activity = np.histogram(node_data['time'], bins=time_bins)[0]
            node_activity.append(activity)
        
        if node_activity:
            node_activity = np.array(node_activity)
            im = ax7.imshow(node_activity, cmap='YlOrRd', aspect='auto')
            ax7.set_xlabel('Time (seconds)')
            ax7.set_ylabel('Node ID')
            ax7.set_title('5G Node Activity Heatmap', fontweight='bold')
            ax7.set_yticks(range(len(sorted(trace_df['node'].dropna().unique()))))
            ax7.set_yticklabels([f'Node {int(n)}' for n in sorted(trace_df['node'].dropna().unique())])
            plt.colorbar(im, ax=ax7, label='Packet Count')
    
    # 8. Performance Summary Table
    ax8 = fig.add_subplot(gs[2, 2:])
    ax8.axis('off')
    
    if not flow_df.empty:
        summary_data = {
            'Metric': ['Total Flows', 'Avg Throughput (Mbps)', 'Avg Delay (ms)', 
                      'Avg Jitter (ms)', 'Total Loss Rate (%)', 'Total Data (MB)'],
            'Value': [
                len(flow_df),
                f"{flow_df['throughput_mbps'].mean():.2f}" if 'throughput_mbps' in flow_df.columns else "N/A",
                f"{flow_df['avg_delay'].mean():.2f}" if 'avg_delay' in flow_df.columns else "N/A",
                f"{flow_df['avg_jitter'].mean():.2f}" if 'avg_jitter' in flow_df.columns else "N/A",
                f"{flow_df['loss_rate'].mean():.2f}" if 'loss_rate' in flow_df.columns else "N/A",
                f"{(flow_df['txBytes'].sum() / 1e6):.2f}" if 'txBytes' in flow_df.columns else "N/A"
            ]
        }
        
        table_data = pd.DataFrame(summary_data)
        table = ax8.table(cellText=table_data.values, colLabels=table_data.columns,
                         cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        ax8.set_title('5G Performance Summary', fontweight='bold', pad=20)
    
    plt.suptitle('5G Network Performance Dashboard', fontsize=20, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'performance_dashboard.png'), dpi=300, bbox_inches='tight')
    plt.close()

def create_throughput_heatmap(flow_df, out_dir):
    """Create throughput heatmap visualization."""
    if flow_df.empty or 'throughput_mbps' not in flow_df.columns:
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create a matrix representation of flows
    n_flows = len(flow_df)
    matrix_size = int(np.ceil(np.sqrt(n_flows)))
    
    # Pad with zeros if needed
    throughput_matrix = flow_df['throughput_mbps'].values
    if len(throughput_matrix) < matrix_size * matrix_size:
        throughput_matrix = np.pad(throughput_matrix, (0, matrix_size * matrix_size - len(throughput_matrix)))
    
    throughput_matrix = throughput_matrix.reshape(matrix_size, matrix_size)
    
    im = ax.imshow(throughput_matrix, cmap='viridis', aspect='auto')
    ax.set_title('5G Flow Throughput Heatmap', fontsize=16, fontweight='bold')
    ax.set_xlabel('Flow Index (X)')
    ax.set_ylabel('Flow Index (Y)')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Throughput (Mbps)', rotation=270, labelpad=20)
    
    # Add text annotations for each cell
    for i in range(matrix_size):
        for j in range(matrix_size):
            if i * matrix_size + j < n_flows:
                text = ax.text(j, i, f'{throughput_matrix[i, j]:.1f}',
                             ha="center", va="center", color="white", fontsize=8)
    
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'throughput_heatmap.png'), dpi=300, bbox_inches='tight')
    plt.close()

def generate_html_report(flow_df, trace_df, out_dir):
    """Generate comprehensive HTML report."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>5G Network Analysis Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 10px; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 5px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #2c5aa0; }}
            .metric-label {{ font-size: 14px; color: #666; }}
            img {{ max-width: 100%; height: auto; margin: 10px 0; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>5G Network Analysis Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="section">
            <h2>Performance Summary</h2>
    """
    
    if not flow_df.empty:
        html_content += f"""
            <div class="metric">
                <div class="metric-value">{len(flow_df)}</div>
                <div class="metric-label">Total Flows</div>
            </div>
        """
        
        if 'throughput_mbps' in flow_df.columns:
            html_content += f"""
            <div class="metric">
                <div class="metric-value">{flow_df['throughput_mbps'].mean():.2f}</div>
                <div class="metric-label">Avg Throughput (Mbps)</div>
            </div>
            """
        
        if 'avg_delay' in flow_df.columns:
            html_content += f"""
            <div class="metric">
                <div class="metric-value">{flow_df['avg_delay'].mean():.2f}</div>
                <div class="metric-label">Avg Delay (ms)</div>
            </div>
            """
        
        if 'loss_rate' in flow_df.columns:
            html_content += f"""
            <div class="metric">
                <div class="metric-value">{flow_df['loss_rate'].mean():.2f}%</div>
                <div class="metric-label">Avg Loss Rate</div>
            </div>
            """
    
    html_content += """
        </div>
        
        <div class="section">
            <h2>Visualizations</h2>
            <h3>Network Topology</h3>
            <img src="network_topology.png" alt="Network Topology">
            
            <h3>Performance Dashboard</h3>
            <img src="performance_dashboard.png" alt="Performance Dashboard">
            
            <h3>Throughput Heatmap</h3>
            <img src="throughput_heatmap.png" alt="Throughput Heatmap">
        </div>
        
        <div class="section">
            <h2>Detailed Analysis</h2>
            <p>For detailed analysis results, please refer to the CSV files in the output directory:</p>
            <ul>
                <li>flowmon_analysis.csv - Flow-level statistics</li>
                <li>traces_parsed.csv - Packet-level trace data</li>
                <li>tr_summary.csv - Trace summary statistics</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    with open(os.path.join(out_dir, 'analysis_report.html'), 'w') as f:
        f.write(html_content)

def main():
    """Main function to generate all visualizations and reports."""
    print("Generating 5G network analysis visualizations...")
    
    # Ensure output directory exists
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Load data
    flow_df = load_flowmon_data()
    trace_df = load_trace_data()
    
    print(f"Loaded {len(flow_df)} flow records and {len(trace_df)} trace records")
    
    # Generate visualizations
    create_network_topology_plot(flow_df, trace_df, OUT_DIR)
    print("✓ Network topology plot created")
    
    create_performance_dashboard(flow_df, trace_df, OUT_DIR)
    print("✓ Performance dashboard created")
    
    create_throughput_heatmap(flow_df, OUT_DIR)
    print("✓ Throughput heatmap created")
    
    generate_html_report(flow_df, trace_df, OUT_DIR)
    print("✓ HTML report generated")
    
    print(f"\nAll visualizations saved to: {OUT_DIR}/")
    print("Open analysis_report.html in a web browser to view the complete report.")

if __name__ == "__main__":
    main()
