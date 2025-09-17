#!/usr/bin/env python3
"""
Enhanced WiFi Mesh Network Visualizer
Creates professional, informative visualizations for ns-3 simulation results
"""

import os
import re
import glob
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, Circle
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set modern styling
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class WiFiMeshVisualizer:
    def __init__(self, output_dir="wifi_mesh_outputs"):
        self.output_dir = output_dir
        self.fig_size = (16, 12)
        self.dpi = 300
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Color schemes
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72', 
            'accent': '#F18F01',
            'success': '#C73E1D',
            'info': '#6A994E',
            'warning': '#F77F00',
            'light': '#F8F9FA',
            'dark': '#212529'
        }
        
        # Set matplotlib rcParams for better styling
        plt.rcParams.update({
            'font.size': 12,
            'font.family': 'sans-serif',
            'axes.titlesize': 16,
            'axes.labelsize': 14,
            'xtick.labelsize': 12,
            'ytick.labelsize': 12,
            'legend.fontsize': 12,
            'figure.titlesize': 18,
            'axes.spines.top': False,
            'axes.spines.right': False,
            'axes.grid': True,
            'grid.alpha': 0.3
        })

    def parse_flowmon_xml(self, xml_file):
        """Parse FlowMonitor XML and return enhanced DataFrame"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            def parse_time_to_seconds(value):
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

            flows = []
            for flow in root.findall('.//Flow'):
                flow_id = int(flow.get('flowId', -1))
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
                    'txBytes': int(flow.get('txBytes', 0)),
                    'rxBytes': int(flow.get('rxBytes', 0)),
                    'txPackets': int(flow.get('txPackets', 0)),
                    'rxPackets': int(flow.get('rxPackets', 0)),
                    'lostPackets': int(flow.get('lostPackets', 0)),
                    'timesForwarded': int(flow.get('timesForwarded', 0))
                }
                
                # Calculate derived metrics
                duration = flow_data['timeLastTxPacket'] - flow_data['timeFirstTxPacket']
                flow_data['duration'] = max(duration, 0.001)  # Avoid division by zero
                flow_data['throughput_mbps'] = (flow_data['rxBytes'] * 8) / (flow_data['duration'] * 1e6)
                flow_data['avg_delay_ms'] = (flow_data['delaySum'] / max(flow_data['rxPackets'], 1)) * 1000
                flow_data['packet_loss_rate'] = flow_data['lostPackets'] / max(flow_data['txPackets'], 1) * 100
                
                flows.append(flow_data)
            
            return pd.DataFrame(flows)
        except Exception as e:
            print(f"Error parsing FlowMonitor XML: {e}")
            return pd.DataFrame()

    def parse_trace_files(self):
        """Parse ASCII trace files and return enhanced DataFrame"""
        trace_files = glob.glob(os.path.join(self.output_dir, "wifi_mesh_playfield_ascii_traces-*.tr"))
        
        if not trace_files:
            print("No trace files found")
            return pd.DataFrame()
        
        line_re = re.compile(
            r"^(?P<event>[tr])\s+"
            r"(?P<time>\d+\.\d+)\s+"
            r"(?P<rate>\S+)\s+"
            r"ns3::WifiMacHeader\s+\((?P<mac>[^)]*)\)"
        )
        
        records = []
        for file_path in trace_files:
            node_id = int(re.search(r'ascii_traces-(\d+)-', file_path).group(1))
            
            with open(file_path, 'r', errors='ignore') as f:
                for line in f:
                    match = line_re.search(line)
                    if match:
                        records.append({
                            'node': node_id,
                            'event': match.group('event'),
                            'time': float(match.group('time')),
                            'rate': match.group('rate'),
                            'mac': match.group('mac')
                        })
        
        df = pd.DataFrame(records)
        if not df.empty:
            df['rate_mbps'] = df['rate'].str.extract(r'(\d+)Mbps').astype(float)
            df['rate_mbps'] = df['rate_mbps'].fillna(0)
        
        return df

    def create_network_topology_plot(self, flows_df):
        """Create network topology visualization"""
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Create a grid layout for nodes
        num_nodes = flows_df['flowId'].nunique() if not flows_df.empty else 10
        grid_size = int(np.ceil(np.sqrt(num_nodes)))
        
        # Position nodes in a grid
        positions = {}
        for i in range(grid_size):
            for j in range(grid_size):
                node_id = i * grid_size + j
                if node_id < num_nodes:
                    positions[node_id] = (j * 3, i * 3)
        
        # Draw nodes
        for node_id, (x, y) in positions.items():
            circle = Circle((x, y), 0.3, color=self.colors['primary'], alpha=0.8)
            ax.add_patch(circle)
            ax.text(x, y, str(node_id), ha='center', va='center', 
                   fontweight='bold', color='white', fontsize=10)
        
        # Draw connections based on flows
        if not flows_df.empty:
            for _, flow in flows_df.iterrows():
                src = flow['flowId'] % num_nodes
                dst = (flow['flowId'] + 1) % num_nodes
                
                if src in positions and dst in positions:
                    x1, y1 = positions[src]
                    x2, y2 = positions[dst]
                    
                    # Color based on throughput
                    throughput = flow['throughput_mbps']
                    if throughput > 10:
                        color = self.colors['success']
                        width = 3
                    elif throughput > 5:
                        color = self.colors['warning']
                        width = 2
                    else:
                        color = self.colors['info']
                        width = 1
                    
                    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                          arrowstyle='->', mutation_scale=20,
                                          color=color, alpha=0.7, linewidth=width)
                    ax.add_patch(arrow)
        
        ax.set_xlim(-1, grid_size * 3)
        ax.set_ylim(-1, grid_size * 3)
        ax.set_aspect('equal')
        ax.set_title('WiFi Mesh Network Topology', fontsize=18, fontweight='bold', pad=20)
        ax.set_xlabel('Network Layout', fontsize=14)
        ax.set_ylabel('Node Positions', fontsize=14)
        ax.grid(True, alpha=0.3)
        
        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], color=self.colors['success'], lw=3, label='High Throughput (>10 Mbps)'),
            plt.Line2D([0], [0], color=self.colors['warning'], lw=2, label='Medium Throughput (5-10 Mbps)'),
            plt.Line2D([0], [0], color=self.colors['info'], lw=1, label='Low Throughput (<5 Mbps)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'network_topology.png'), 
                   dpi=self.dpi, bbox_inches='tight')
        plt.close()

    def create_throughput_heatmap(self, flows_df):
        """Create throughput heatmap over time"""
        if flows_df.empty:
            return
            
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Filter flows with actual data
        active_flows = flows_df[flows_df['rxBytes'] > 0].copy()
        
        if active_flows.empty:
            # If no flows have received data, create a different visualization
            ax.text(0.5, 0.5, 'No Data Received\nAll flows show 0 received bytes', 
                   ha='center', va='center', fontsize=16, 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=self.colors['warning'], alpha=0.7))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_title('Throughput Analysis - No Data Received', fontsize=18, fontweight='bold')
            ax.axis('off')
        else:
            # Create time bins
            time_bins = np.linspace(active_flows['timeFirstTxPacket'].min(), 
                                   active_flows['timeLastTxPacket'].max(), 20)
            
            # Create throughput matrix
            throughput_matrix = np.zeros((len(active_flows), len(time_bins)-1))
            
            for idx, (_, flow) in enumerate(active_flows.iterrows()):
                for j in range(len(time_bins)-1):
                    start_time = time_bins[j]
                    end_time = time_bins[j+1]
                    
                    # Calculate throughput for this time bin
                    if (flow['timeFirstTxPacket'] <= end_time and 
                        flow['timeLastTxPacket'] >= start_time):
                        duration = min(end_time, flow['timeLastTxPacket']) - max(start_time, flow['timeFirstTxPacket'])
                        if duration > 0:
                            throughput_matrix[idx, j] = flow['throughput_mbps']
            
            # Create heatmap
            if throughput_matrix.max() > 0:
                im = ax.imshow(throughput_matrix, cmap='YlOrRd', aspect='auto', interpolation='nearest')
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax)
                cbar.set_label('Throughput (Mbps)', fontsize=12)
            else:
                ax.text(0.5, 0.5, 'No Throughput Data Available', 
                       ha='center', va='center', fontsize=16)
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
            
            # Customize plot
            ax.set_title(f'Throughput Heatmap Over Time\n({len(active_flows)} active flows out of {len(flows_df)} total)', 
                        fontsize=18, fontweight='bold', pad=20)
            ax.set_xlabel('Time Bins', fontsize=14)
            ax.set_ylabel('Flow ID', fontsize=14)
            
            # Set ticks
            if throughput_matrix.max() > 0:
                ax.set_xticks(range(0, len(time_bins)-1, 2))
                ax.set_xticklabels([f'{t:.1f}s' for t in time_bins[::2]])
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'throughput_heatmap.png'), 
                   dpi=self.dpi, bbox_inches='tight')
        plt.close()

    def create_transmission_analysis(self, flows_df):
        """Create analysis of data transmission issues"""
        if flows_df.empty:
            return
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Bytes transmitted vs received
        ax1.scatter(flows_df['txBytes'], flows_df['rxBytes'], 
                   c=flows_df['flowId'], cmap='viridis', s=100, alpha=0.7)
        ax1.plot([0, flows_df['txBytes'].max()], [0, flows_df['txBytes'].max()], 
                'r--', alpha=0.5, label='Perfect Delivery')
        ax1.set_xlabel('Bytes Transmitted')
        ax1.set_ylabel('Bytes Received')
        ax1.set_title('Data Transmission Efficiency')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Packet loss analysis
        flows_df['packet_loss_count'] = flows_df['txPackets'] - flows_df['rxPackets']
        flows_df['packet_loss_count'] = flows_df['packet_loss_count'].clip(lower=0)
        
        ax2.bar(flows_df['flowId'], flows_df['packet_loss_count'], 
               color=self.colors['warning'], alpha=0.7)
        ax2.set_xlabel('Flow ID')
        ax2.set_ylabel('Lost Packets')
        ax2.set_title('Packet Loss by Flow')
        ax2.grid(True, alpha=0.3)
        
        # 3. Transmission duration analysis
        flows_df['duration'] = flows_df['timeLastTxPacket'] - flows_df['timeFirstTxPacket']
        ax3.hist(flows_df['duration'], bins=20, color=self.colors['info'], alpha=0.7, edgecolor='black')
        ax3.set_xlabel('Transmission Duration (seconds)')
        ax3.set_ylabel('Number of Flows')
        ax3.set_title('Flow Duration Distribution')
        ax3.grid(True, alpha=0.3)
        
        # 4. Success rate analysis
        success_rates = (flows_df['rxPackets'] / flows_df['txPackets'] * 100).fillna(0)
        success_rates = success_rates.clip(0, 100)
        
        ax4.bar(flows_df['flowId'], success_rates, 
               color=[self.colors['success'] if rate > 50 else self.colors['warning'] for rate in success_rates],
               alpha=0.7)
        ax4.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50% Success Rate')
        ax4.set_xlabel('Flow ID')
        ax4.set_ylabel('Success Rate (%)')
        ax4.set_title('Flow Success Rate')
        ax4.set_ylim(0, 100)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # Add summary statistics
        total_tx = flows_df['txBytes'].sum()
        total_rx = flows_df['rxBytes'].sum()
        overall_success = (total_rx / total_tx * 100) if total_tx > 0 else 0
        
        fig.suptitle(f'Data Transmission Analysis\n'
                    f'Total Transmitted: {total_tx/1e6:.2f} MB | '
                    f'Total Received: {total_rx/1e6:.2f} MB | '
                    f'Overall Success: {overall_success:.1f}%', 
                    fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'transmission_analysis.png'), 
                   dpi=self.dpi, bbox_inches='tight')
        plt.close()

    def create_performance_dashboard(self, flows_df, traces_df):
        """Create comprehensive performance dashboard"""
        fig = plt.figure(figsize=(20, 16))
        
        # Create subplots
        gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
        
        # 1. Throughput Distribution
        ax1 = fig.add_subplot(gs[0, 0])
        if not flows_df.empty:
            sns.histplot(flows_df['throughput_mbps'], bins=20, kde=True, ax=ax1, 
                        color=self.colors['primary'], alpha=0.7)
            ax1.set_title('Throughput Distribution', fontweight='bold')
            ax1.set_xlabel('Throughput (Mbps)')
            ax1.set_ylabel('Frequency')
        
        # 2. Delay vs Throughput Scatter
        ax2 = fig.add_subplot(gs[0, 1])
        if not flows_df.empty:
            scatter = ax2.scatter(flows_df['avg_delay_ms'], flows_df['throughput_mbps'], 
                                c=flows_df['packet_loss_rate'], cmap='viridis', 
                                s=100, alpha=0.7, edgecolors='black', linewidth=0.5)
            ax2.set_title('Delay vs Throughput', fontweight='bold')
            ax2.set_xlabel('Average Delay (ms)')
            ax2.set_ylabel('Throughput (Mbps)')
            plt.colorbar(scatter, ax=ax2, label='Packet Loss Rate (%)')
        
        # 3. Packet Loss Analysis
        ax3 = fig.add_subplot(gs[0, 2])
        if not flows_df.empty:
            loss_data = flows_df['packet_loss_rate']
            ax3.boxplot([loss_data], patch_artist=True, 
                       boxprops=dict(facecolor=self.colors['warning'], alpha=0.7))
            ax3.set_title('Packet Loss Rate Distribution', fontweight='bold')
            ax3.set_ylabel('Packet Loss Rate (%)')
            ax3.set_xticklabels(['All Flows'])
        
        # 4. Rate Distribution over Time
        ax4 = fig.add_subplot(gs[1, :])
        if not traces_df.empty:
            time_bins = pd.cut(traces_df['time'], bins=20)
            rate_over_time = traces_df.groupby([time_bins, 'node'])['rate_mbps'].mean().unstack(fill_value=0)
            
            for node in rate_over_time.columns:
                ax4.plot(range(len(rate_over_time)), rate_over_time[node], 
                        marker='o', linewidth=2, label=f'Node {node}', alpha=0.8)
            
            ax4.set_title('Data Rate Evolution Over Time', fontweight='bold')
            ax4.set_xlabel('Time Bins')
            ax4.set_ylabel('Data Rate (Mbps)')
            ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax4.grid(True, alpha=0.3)
        
        # 5. Flow Statistics Summary
        ax5 = fig.add_subplot(gs[2, 0])
        if not flows_df.empty:
            stats = {
                'Total Flows': len(flows_df),
                'Avg Throughput': f"{flows_df['throughput_mbps'].mean():.2f} Mbps",
                'Avg Delay': f"{flows_df['avg_delay_ms'].mean():.2f} ms",
                'Total Bytes': f"{flows_df['rxBytes'].sum() / 1e6:.2f} MB"
            }
            
            y_pos = np.arange(len(stats))
            ax5.barh(y_pos, [1]*len(stats), color=self.colors['info'], alpha=0.7)
            ax5.set_yticks(y_pos)
            ax5.set_yticklabels(list(stats.keys()))
            ax5.set_xlim(0, 1)
            ax5.set_title('Network Statistics', fontweight='bold')
            
            # Add text labels
            for i, (key, value) in enumerate(stats.items()):
                ax5.text(0.5, i, value, ha='center', va='center', fontweight='bold')
        
        # 6. Event Distribution
        ax6 = fig.add_subplot(gs[2, 1])
        if not traces_df.empty:
            event_counts = traces_df['event'].value_counts()
            colors = [self.colors['success'] if event == 'r' else self.colors['primary'] 
                     for event in event_counts.index]
            wedges, texts, autotexts = ax6.pie(event_counts.values, labels=['Receive', 'Transmit'], 
                                              colors=colors, autopct='%1.1f%%', startangle=90)
            ax6.set_title('Event Distribution', fontweight='bold')
        
        # 7. Node Activity
        ax7 = fig.add_subplot(gs[2, 2])
        if not traces_df.empty:
            node_activity = traces_df.groupby('node').size()
            bars = ax7.bar(node_activity.index, node_activity.values, 
                          color=self.colors['accent'], alpha=0.7)
            ax7.set_title('Node Activity', fontweight='bold')
            ax7.set_xlabel('Node ID')
            ax7.set_ylabel('Number of Events')
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax7.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
        
        # 8. Performance Metrics Table
        ax8 = fig.add_subplot(gs[3, :])
        ax8.axis('off')
        
        if not flows_df.empty:
            # Create summary table
            summary_data = {
                'Metric': ['Total Flows', 'Average Throughput (Mbps)', 'Average Delay (ms)', 
                          'Total Data Transferred (MB)', 'Average Packet Loss Rate (%)',
                          'Simulation Duration (s)', 'Peak Throughput (Mbps)'],
                'Value': [
                    len(flows_df),
                    f"{flows_df['throughput_mbps'].mean():.2f}",
                    f"{flows_df['avg_delay_ms'].mean():.2f}",
                    f"{flows_df['rxBytes'].sum() / 1e6:.2f}",
                    f"{flows_df['packet_loss_rate'].mean():.2f}",
                    f"{flows_df['timeLastTxPacket'].max() - flows_df['timeFirstTxPacket'].min():.2f}",
                    f"{flows_df['throughput_mbps'].max():.2f}"
                ]
            }
            
            table = ax8.table(cellText=list(zip(summary_data['Metric'], summary_data['Value'])),
                             colLabels=['Performance Metric', 'Value'],
                             cellLoc='center', loc='center',
                             colWidths=[0.7, 0.3])
            table.auto_set_font_size(False)
            table.set_fontsize(12)
            table.scale(1, 2)
            
            # Style the table
            for i in range(len(summary_data['Metric']) + 1):
                for j in range(2):
                    cell = table[(i, j)]
                    if i == 0:  # Header
                        cell.set_facecolor(self.colors['primary'])
                        cell.set_text_props(weight='bold', color='white')
                    else:
                        cell.set_facecolor(self.colors['light'] if i % 2 == 0 else 'white')
        
        # Add main title
        fig.suptitle('WiFi Mesh Network Performance Dashboard', 
                    fontsize=24, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'performance_dashboard.png'), 
                   dpi=self.dpi, bbox_inches='tight')
        plt.close()

    def generate_html_report(self, flows_df, traces_df):
        """Generate interactive HTML report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WiFi Mesh Network Analysis Report</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f8f9fa; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                h1 {{ color: #2E86AB; text-align: center; margin-bottom: 30px; }}
                h2 {{ color: #A23B72; border-bottom: 2px solid #A23B72; padding-bottom: 10px; }}
                .metric {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #2E86AB; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #2E86AB; }}
                .metric-label {{ color: #6c757d; font-size: 14px; }}
                .image-container {{ text-align: center; margin: 20px 0; }}
                .image-container img {{ max-width: 100%; height: auto; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
                .timestamp {{ color: #6c757d; font-size: 12px; text-align: right; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>WiFi Mesh Network Analysis Report</h1>
                <p class="timestamp">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h2>Network Overview</h2>
                <div class="stats-grid">
        """
        
        if not flows_df.empty:
            html_content += f"""
                    <div class="metric">
                        <div class="metric-value">{len(flows_df)}</div>
                        <div class="metric-label">Total Flows</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{flows_df['throughput_mbps'].mean():.2f} Mbps</div>
                        <div class="metric-label">Average Throughput</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{flows_df['avg_delay_ms'].mean():.2f} ms</div>
                        <div class="metric-label">Average Delay</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{flows_df['rxBytes'].sum() / 1e6:.2f} MB</div>
                        <div class="metric-label">Total Data Transferred</div>
                    </div>
            """
        
        html_content += """
                </div>
                
                <h2>Network Topology</h2>
                <div class="image-container">
                    <img src="network_topology.png" alt="Network Topology">
                </div>
                
                <h2>Performance Dashboard</h2>
                <div class="image-container">
                    <img src="performance_dashboard.png" alt="Performance Dashboard">
                </div>
                
                <h2>Throughput Analysis</h2>
                <div class="image-container">
                    <img src="throughput_heatmap.png" alt="Throughput Heatmap">
                </div>
                
                <h2>Data Transmission Analysis</h2>
                <div class="image-container">
                    <img src="transmission_analysis.png" alt="Transmission Analysis">
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(os.path.join(self.output_dir, 'analysis_report.html'), 'w') as f:
            f.write(html_content)

    def run_enhanced_analysis(self):
        """Run complete enhanced analysis"""
        print("🔍 Starting enhanced WiFi Mesh analysis...")
        
        # Parse data
        print("📊 Parsing FlowMonitor data...")
        flows_df = self.parse_flowmon_xml(os.path.join(self.output_dir, 'flowmon-wifi-mesh-playfield-rw.xml'))
        
        print("📈 Parsing trace files...")
        traces_df = self.parse_trace_files()
        
        # Generate visualizations
        print("🎨 Creating network topology visualization...")
        self.create_network_topology_plot(flows_df)
        
        print("🔥 Creating throughput heatmap...")
        self.create_throughput_heatmap(flows_df)
        
        print("🔍 Creating data transmission analysis...")
        self.create_transmission_analysis(flows_df)
        
        print("📊 Creating performance dashboard...")
        self.create_performance_dashboard(flows_df, traces_df)
        
        print("📄 Generating HTML report...")
        self.generate_html_report(flows_df, traces_df)
        
        print("✅ Enhanced analysis complete!")
        print(f"📁 Results saved in: {self.output_dir}")
        print("🌐 Open analysis_report.html in your browser for interactive results")

if __name__ == "__main__":
    visualizer = WiFiMeshVisualizer()
    visualizer.run_enhanced_analysis()
