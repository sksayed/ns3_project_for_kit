#!/usr/bin/env python3
"""
WiFi Mesh Backhaul Network Analyzer
Analyzes the results from the WiFi mesh backhaul simulation.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

class WiFiMeshBackhaulAnalyzer:
    def __init__(self, output_dir="wifi_mesh_backhaul_outputs"):
        self.output_dir = output_dir
        self.field_size = 400.0
        self.n_total_nodes = 15  # 1 backhaul + 4 mesh + 8 STA + 2 Sayed/Sadia
        self.sim_time = 10.0  # seconds
        
        # Network topology
        self.node_types = {
            0: "Backhaul",
            1: "Mesh0", 2: "Mesh1", 3: "Mesh2", 4: "Mesh3",
            5: "STA0", 6: "STA1", 7: "STA2", 8: "STA3", 9: "STA4", 10: "STA5", 11: "STA6", 12: "STA7",
            13: "Sayed", 14: "Sadia"
        }
        
        self.flowmon_file = os.path.join(output_dir, "flowmon-wifi-mesh-backhaul.xml")
        self.ascii_file = os.path.join(output_dir, "wifi_mesh_backhaul_ascii_traces_mesh.tr")
        self.ipv4_file = os.path.join(output_dir, "ipv4-l3.tr")
        
    def analyze_flowmon_results(self):
        """Analyze FlowMonitor XML results"""
        if not os.path.exists(self.flowmon_file):
            print(f"FlowMonitor file not found: {self.flowmon_file}")
            return None
        
        print("Analyzing FlowMonitor results...")
        
        try:
            tree = ET.parse(self.flowmon_file)
            root = tree.getroot()
            
            flows = []
            # First, get protocol information from FlowClassifier
            protocol_map = {}
            for classifier in root.findall('.//Ipv4FlowClassifier'):
                for flow in classifier.findall('Flow'):
                    flow_id = flow.get('flowId')
                    protocol_num = int(flow.get('protocol', 0))
                    if protocol_num == 17:  # UDP
                        protocol_map[flow_id] = 'UDP'
                    elif protocol_num == 6:  # TCP
                        protocol_map[flow_id] = 'TCP'
                    else:
                        protocol_map[flow_id] = f'Protocol_{protocol_num}'
            
            # Then process FlowStats and add protocol information
            for flow in root.findall('.//FlowStats/Flow'):
                flow_data = {}
                # Get attributes directly from the Flow element
                for attr_name, attr_value in flow.attrib.items():
                    flow_data[attr_name] = attr_value
                # Also get child elements if any
                for child in flow:
                    flow_data[child.tag] = child.text
                
                # Add protocol information from classifier
                flow_id = flow_data.get('flowId')
                protocol = protocol_map.get(flow_id, 'Unknown')
                flow_data['protocol'] = protocol
                
                # Only include UDP and TCP flows
                if protocol in ['UDP', 'TCP']:
                    flows.append(flow_data)
            
            if not flows:
                print("No flow data found in FlowMonitor results")
                return None
            
            # Create DataFrame
            df = pd.DataFrame(flows)
            
            # Convert numeric columns - handle nanosecond time format
            def parse_ns_time(time_str):
                if not time_str or time_str == '0' or time_str == '+0ns':
                    return 0.0
                # Remove 'ns' suffix and '+' prefix, then convert to seconds
                if 'ns' in str(time_str):
                    time_str = str(time_str).replace('ns', '').replace('+', '')
                return float(time_str) / 1e9  # Convert nanoseconds to seconds
            
            # Parse time columns with nanosecond handling
            time_columns = ['timeFirstTxPacket', 'timeLastTxPacket', 'timeFirstRxPacket', 'timeLastRxPacket', 'delaySum']
            for col in time_columns:
                if col in df.columns:
                    df[col] = df[col].apply(parse_ns_time)
            
            # Convert other numeric columns normally
            numeric_columns = ['jitterSum', 'lastDelay', 
                             'txBytes', 'rxBytes', 'txPackets', 'rxPackets', 'lostPackets',
                             'timesForwarded', 'delayHistogram', 'jitterHistogram', 
                             'packetSizeHistogram', 'flowInterruptionsHistogram']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Calculate additional metrics
            # Handle cases where no packets were received (timeLastRxPacket = 0)
            df['duration'] = np.where(df['timeLastRxPacket'] > 0, 
                                    df['timeLastRxPacket'] - df['timeFirstTxPacket'],
                                    df['timeLastTxPacket'] - df['timeFirstTxPacket'])
            
            # Calculate throughput only for successful flows
            df['throughput'] = np.where(df['rxPackets'] > 0,
                                      (df['rxBytes'] * 8) / (df['duration'] * 1e6),  # Mbps
                                      0)
            
            # Calculate packet loss rate
            df['packet_loss_rate'] = np.where((df['txPackets'] + df['lostPackets']) > 0,
                                            df['lostPackets'] / (df['txPackets'] + df['lostPackets']),
                                            1.0)  # 100% loss if no packets sent
            
            # Calculate average delay only for received packets (delaySum is now in seconds)
            df['avg_delay'] = np.where(df['rxPackets'] > 0,
                                     df['delaySum'] / df['rxPackets'],
                                     0)
            
            print(f"Found {len(df)} flows (UDP and TCP only)")
            
            # Print flow analysis summary
            successful_flows = df[df['rxPackets'] > 0]
            failed_flows = df[df['rxPackets'] == 0]
            
            # Show protocol breakdown
            udp_flows = df[df['protocol'] == 'UDP']
            tcp_flows = df[df['protocol'] == 'TCP']
            print(f"  - UDP flows: {len(udp_flows)}")
            print(f"  - TCP flows: {len(tcp_flows)}")
            print(f"  - Successful flows: {len(successful_flows)}")
            print(f"  - Failed flows: {len(failed_flows)}")
            
            if len(failed_flows) > 0:
                print("  - Failed flows analysis:")
                for idx, flow in failed_flows.iterrows():
                    protocol = flow.get('protocol', 'Unknown')
                    print(f"    Flow {int(flow.get('flowId', idx))} ({protocol}): {int(flow['txPackets'])} packets sent, 0 received")
            
            return df
            
        except Exception as e:
            print(f"Error analyzing FlowMonitor results: {e}")
            return None
    
    def analyze_ascii_traces(self):
        """Analyze ASCII trace files"""
        if not os.path.exists(self.ascii_file):
            print(f"ASCII trace file not found: {self.ascii_file}")
            return None
        
        print("Analyzing ASCII traces...")
        
        try:
            # Read ASCII traces
            with open(self.ascii_file, 'r') as f:
                lines = f.readlines()
            
            trace_data = []
            for line in lines:
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 10:
                        try:
                            trace_data.append({
                                'time': float(parts[0]),
                                'node_id': int(parts[1]),
                                'device_id': int(parts[2]),
                                'packet_type': parts[3],
                                'packet_size': int(parts[4]),
                                'flags': parts[5],
                                'seq_num': parts[6],
                                'src_addr': parts[7],
                                'dst_addr': parts[8],
                                'protocol': parts[9] if len(parts) > 9 else 'unknown'
                            })
                        except (ValueError, IndexError):
                            continue
            
            if not trace_data:
                print("No valid trace data found")
                return None
            
            df = pd.DataFrame(trace_data)
            print(f"Found {len(df)} trace entries")
            return df
            
        except Exception as e:
            print(f"Error analyzing ASCII traces: {e}")
            return None
    
    def plot_network_topology(self):
        """Create network topology visualization"""
        print("Creating network topology plot...")
        
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Node positions (matching exact coordinates from C++ code)
        node_positions = {
            0: (30.0, 200.0),  # Backhaul
            1: (50.0, 10.0),   # Mesh0
            2: (150.0, 200.0), # Mesh1
            3: (300.0, 390.0), # Mesh2
            4: (370.0, 160.0), # Mesh3
            5: (85.0, 10.0),   # STA0 (orbit around Mesh0)
            6: (15.0, 10.0),   # STA1 (orbit around Mesh0)
            7: (185.0, 200.0), # STA2 (orbit around Mesh1)
            8: (115.0, 200.0), # STA3 (orbit around Mesh1)
            9: (335.0, 390.0), # STA4 (orbit around Mesh2)
            10: (265.0, 390.0), # STA5 (orbit around Mesh2)
            11: (405.0, 160.0), # STA6 (orbit around Mesh3)
            12: (335.0, 160.0), # STA7 (orbit around Mesh3)
            13: (0.0, 0.0),    # Sayed
            14: (400.0, 400.0) # Sadia
        }
        
        # Building positions
        buildings = [
            {"name": "leftBelow", "x": 0.0, "y": 96.0, "w": 60.0, "h": 8.0},
            {"name": "rightBelow", "x": 340.0, "y": 96.0, "w": 60.0, "h": 8.0},
            {"name": "leftAbove", "x": 0.0, "y": 296.0, "w": 60.0, "h": 8.0},
            {"name": "rightAbove", "x": 340.0, "y": 296.0, "w": 60.0, "h": 8.0},
            {"name": "cluster250a", "x": 80.0, "y": 220.0, "w": 60.0, "h": 8.0},
            {"name": "cluster250b", "x": 170.0, "y": 220.0, "w": 80.0, "h": 8.0},
            {"name": "cluster50", "x": 255.0, "y": 20.0, "w": 80.0, "h": 8.0},
        ]
        
        # Draw buildings
        for building in buildings:
            rect = plt.Rectangle((building["x"], building["y"]), 
                               building["w"], building["h"],
                               facecolor='#8B4513', alpha=0.8,  # Dark brown color
                               edgecolor='black', linewidth=1)
            ax.add_patch(rect)
        
        # Draw network connections
        # Backhaul connection to first mesh node only (Mesh0) - RED
        backhaul_pos = node_positions[0]
        mesh0_pos = node_positions[1]  # Mesh0 is node 1
        ax.plot([backhaul_pos[0], mesh0_pos[0]], [backhaul_pos[1], mesh0_pos[1]], 
               'r-', alpha=0.8, linewidth=4, label='Backhaul Link')
        
        # Mesh hop chain connections (Mesh0 -> Mesh1 -> Mesh2 -> Mesh3)
        for i in range(1, 4):
            pos1 = node_positions[i]
            pos2 = node_positions[i + 1]
            ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], 
                   'r-', alpha=0.7, linewidth=2, label='Mesh Chain' if i == 1 else "")
        
        # STA to mesh connections
        for i in range(5, 13):
            sta_pos = node_positions[i]
            mesh_idx = ((i - 5) // 2) + 1
            mesh_pos = node_positions[mesh_idx]
            ax.plot([sta_pos[0], mesh_pos[0]], [sta_pos[1], mesh_pos[1]], 
                   'g--', alpha=0.3, linewidth=1, label='STA Links' if i == 5 else "")
        
        # Note: Sayed and Sadia communicate through the mesh network, no direct link
        
        # Draw nodes
        colors = ['blue', 'red', 'red', 'red', 'red', 'yellow', 'yellow', 'yellow', 'yellow',
                 'yellow', 'yellow', 'yellow', 'yellow', 'cyan', 'orange']
        markers = ['^', 's', 's', 's', 's', 'o', 'o', 'o', 'o', 'o', 'o', 'o', 'o', 'D', 'D']
        sizes = [200, 150, 150, 150, 150, 100, 100, 100, 100, 100, 100, 100, 100, 180, 180]
        
        for i, (pos, color, marker, size) in enumerate(zip(node_positions.values(), colors, markers, sizes)):
            ax.scatter(pos[0], pos[1], c=color, s=size, marker=marker, 
                      edgecolors='black', linewidth=2)
            
            # Add labels
            if i == 0:
                ax.annotate('Backhaul\nGateway', pos, xytext=(10, 10), 
                           textcoords='offset points', fontsize=10, weight='bold')
            elif i >= 1 and i <= 4:
                ax.annotate(f'Mesh{i-1}', pos, xytext=(5, 5), 
                           textcoords='offset points', fontsize=9)
            elif i >= 5 and i <= 12:
                ax.annotate(f'STA{i-5}', pos, xytext=(5, -15), 
                           textcoords='offset points', fontsize=8)
            elif i == 13:
                ax.annotate('Sayed', pos, xytext=(10, 10), 
                           textcoords='offset points', fontsize=10, weight='bold')
            elif i == 14:
                ax.annotate('Sadia', pos, xytext=(10, 10), 
                           textcoords='offset points', fontsize=10, weight='bold')
        
        # Add internet server (outside the playground)
        internet_pos = (30.0, self.field_size + 50)  # Outside the 400x400 field
        ax.scatter(internet_pos[0], internet_pos[1], c='green', s=120, marker='*', 
                  edgecolors='black', linewidth=2, label='Internet Server')
        ax.annotate('Internet\nServer', internet_pos, xytext=(10, 10), 
                   textcoords='offset points', fontsize=10, weight='bold')
        
        # Draw connection from internet server to backhaul
        backhaul_pos = node_positions[0]
        ax.plot([internet_pos[0], backhaul_pos[0]], [internet_pos[1], backhaul_pos[1]], 
               'g--', alpha=0.8, linewidth=3, label='Internet Link')
        
        ax.set_xlim(-20, 420)
        ax.set_ylim(-20, 500)  # Extra space for internet server
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title('WiFi Mesh Backhaul Network Topology', fontsize=16, weight='bold')
        ax.set_xlabel('X Position (meters)', fontsize=12)
        ax.set_ylabel('Y Position (meters)', fontsize=12)
        
        # Add legend
        ax.legend(loc='upper right', fontsize=10)
        
        # Add statistics
        stats_text = f"Network Statistics:\n" \
                    f"• Total Nodes: {self.n_total_nodes}\n" \
                    f"• Backhaul Gateway: 1\n" \
                    f"• Mesh Hop Nodes: 4\n" \
                    f"• STA Nodes: 8\n" \
                    f"• Special Nodes: Sayed, Sadia\n" \
                    f"• Simulation Time: {self.sim_time}s"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
               fontsize=11, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        plt.tight_layout()
        output_file = os.path.join(self.output_dir, "network_topology_analysis.png")
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Network topology plot saved: {output_file}")
        plt.close()
    
    def plot_flow_analysis(self, flow_df):
        """Plot flow analysis results"""
        if flow_df is None or flow_df.empty:
            print("No flow data available for analysis")
            return
        
        print("Creating flow analysis plots...")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('WiFi Mesh Backhaul Network - Flow Analysis', fontsize=16, weight='bold')
        
        # Throughput distribution (only successful flows)
        successful_flows = flow_df[flow_df['throughput'] > 0]
        if not successful_flows.empty:
            axes[0, 0].hist(successful_flows['throughput'], bins=20, alpha=0.7, color='blue')
            axes[0, 0].set_title(f'Throughput Distribution\n({len(successful_flows)} successful flows)')
        else:
            axes[0, 0].text(0.5, 0.5, 'No successful flows', ha='center', va='center', transform=axes[0, 0].transAxes)
            axes[0, 0].set_title('Throughput Distribution\n(No successful flows)')
        axes[0, 0].set_xlabel('Throughput (Mbps)')
        axes[0, 0].set_ylabel('Number of Flows')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Delay distribution (only successful flows)
        if not successful_flows.empty:
            axes[0, 1].hist(successful_flows['avg_delay'].dropna(), bins=20, alpha=0.7, color='green')
            axes[0, 1].set_title(f'Average Delay Distribution\n({len(successful_flows)} successful flows)')
        else:
            axes[0, 1].text(0.5, 0.5, 'No successful flows', ha='center', va='center', transform=axes[0, 1].transAxes)
            axes[0, 1].set_title('Average Delay Distribution\n(No successful flows)')
        axes[0, 1].set_xlabel('Average Delay (seconds)')
        axes[0, 1].set_ylabel('Number of Flows')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Packet loss rate
        axes[0, 2].hist(flow_df['packet_loss_rate'].dropna(), bins=20, alpha=0.7, color='red')
        axes[0, 2].set_title('Packet Loss Rate Distribution')
        axes[0, 2].set_xlabel('Packet Loss Rate')
        axes[0, 2].set_ylabel('Number of Flows')
        axes[0, 2].grid(True, alpha=0.3)
        
        # Flow duration
        axes[1, 0].hist(flow_df['duration'].dropna(), bins=20, alpha=0.7, color='orange')
        axes[1, 0].set_title('Flow Duration Distribution')
        axes[1, 0].set_xlabel('Duration (seconds)')
        axes[1, 0].set_ylabel('Number of Flows')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Throughput vs Delay scatter plot (only successful flows)
        if not successful_flows.empty:
            axes[1, 1].scatter(successful_flows['throughput'], successful_flows['avg_delay'], alpha=0.6, color='purple')
            axes[1, 1].set_title(f'Throughput vs Average Delay\n({len(successful_flows)} successful flows)')
        else:
            axes[1, 1].text(0.5, 0.5, 'No successful flows', ha='center', va='center', transform=axes[1, 1].transAxes)
            axes[1, 1].set_title('Throughput vs Average Delay\n(No successful flows)')
        axes[1, 1].set_xlabel('Throughput (Mbps)')
        axes[1, 1].set_ylabel('Average Delay (seconds)')
        axes[1, 1].grid(True, alpha=0.3)
        
        # Traffic volume by flow with protocol colors
        colors = ['blue' if protocol == 'UDP' else 'red' for protocol in flow_df['protocol']]
        axes[1, 2].bar(range(len(flow_df)), flow_df['rxBytes'], alpha=0.7, color=colors)
        axes[1, 2].set_title('Traffic Volume by Flow (Blue=UDP, Red=TCP)')
        axes[1, 2].set_xlabel('Flow ID')
        axes[1, 2].set_ylabel('Received Bytes')
        axes[1, 2].grid(True, alpha=0.3)
        
        # Add summary statistics text box
        total_flows = len(flow_df)
        successful_count = len(successful_flows)
        failed_count = total_flows - successful_count
        udp_flows = len(flow_df[flow_df['protocol'] == 'UDP'])
        tcp_flows = len(flow_df[flow_df['protocol'] == 'TCP'])
        
        summary_text = f"Flow Statistics Summary (UDP & TCP only):\n" \
                      f"• Total Flows: {total_flows}\n" \
                      f"• UDP Flows: {udp_flows}\n" \
                      f"• TCP Flows: {tcp_flows}\n" \
                      f"• Successful: {successful_count}\n" \
                      f"• Failed: {failed_count}\n" \
                      f"• Success Rate: {(successful_count/total_flows)*100:.1f}%"
        
        fig.text(0.02, 0.02, summary_text, fontsize=10, 
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()
        output_file = os.path.join(self.output_dir, "flow_analysis.png")
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Flow analysis plot saved: {output_file}")
        plt.close()
    
    def generate_report(self, flow_df, trace_df):
        """Generate comprehensive analysis report"""
        print("Generating analysis report...")
        
        report_file = os.path.join(self.output_dir, "wifi_mesh_backhaul_analysis_report.html")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WiFi Mesh Backhaul Network Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; }}
                .summary {{ background-color: #ecf0f1; padding: 20px; border-radius: 5px; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
                .metric {{ background-color: #3498db; color: white; padding: 15px; border-radius: 5px; text-align: center; }}
                .metric h3 {{ margin: 0; }}
                .metric p {{ margin: 5px 0; font-size: 24px; font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                img {{ max-width: 100%; height: auto; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>WiFi Mesh Backhaul Network Analysis Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Network Overview</h2>
                <p>This report analyzes the performance of a WiFi mesh backhaul network simulation with the following topology:</p>
                <ul>
                    <li><strong>Backhaul Gateway:</strong> 1 node (internet connection point)</li>
                    <li><strong>Mesh Hop Nodes:</strong> 4 nodes forming a chain: Backhaul → Mesh0 → Mesh1 → Mesh2 → Mesh3</li>
                    <li><strong>STA Nodes:</strong> 8 mobile nodes connected to nearest mesh hops</li>
                    <li><strong>Special Nodes:</strong> Sayed and Sadia for communication testing</li>
                    <li><strong>Simulation Time:</strong> {self.sim_time} seconds</li>
                    <li><strong>Field Size:</strong> {self.field_size}m × {self.field_size}m</li>
                </ul>
                <p><strong>Network Architecture:</strong> The backhaul is connected only to Mesh0, which then forms a chain with the other mesh nodes. STA nodes connect to the nearest mesh hop, and all traffic flows through this mesh backbone to reach the internet.</p>
            </div>
        """
        
        if flow_df is not None and not flow_df.empty:
            # Calculate key metrics
            total_flows = len(flow_df)
            avg_throughput = flow_df['throughput'].mean()
            avg_delay = flow_df['avg_delay'].mean()
            avg_packet_loss = flow_df['packet_loss_rate'].mean()
            total_bytes = flow_df['rxBytes'].sum()
            
            html_content += f"""
            <div class="metrics">
                <div class="metric">
                    <h3>Total Flows</h3>
                    <p>{total_flows}</p>
                </div>
                <div class="metric">
                    <h3>Average Throughput</h3>
                    <p>{avg_throughput:.2f} Mbps</p>
                </div>
                <div class="metric">
                    <h3>Average Delay</h3>
                    <p>{avg_delay:.4f} s</p>
                </div>
                <div class="metric">
                    <h3>Packet Loss Rate</h3>
                    <p>{avg_packet_loss:.2%}</p>
                </div>
                <div class="metric">
                    <h3>Total Traffic</h3>
                    <p>{total_bytes / 1024 / 1024:.2f} MB</p>
                </div>
                <div class="metric">
                    <h3>Simulation Duration</h3>
                    <p>{self.sim_time} s</p>
                </div>
            </div>
            
            <h2>Flow Statistics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Flows</td><td>{total_flows}</td></tr>
                <tr><td>Average Throughput</td><td>{avg_throughput:.3f} Mbps</td></tr>
                <tr><td>Max Throughput</td><td>{flow_df['throughput'].max():.3f} Mbps</td></tr>
                <tr><td>Min Throughput</td><td>{flow_df['throughput'].min():.3f} Mbps</td></tr>
                <tr><td>Average Delay</td><td>{avg_delay:.6f} seconds</td></tr>
                <tr><td>Max Delay</td><td>{flow_df['avg_delay'].max():.6f} seconds</td></tr>
                <tr><td>Min Delay</td><td>{flow_df['avg_delay'].min():.6f} seconds</td></tr>
                <tr><td>Average Packet Loss</td><td>{avg_packet_loss:.2%}</td></tr>
                <tr><td>Max Packet Loss</td><td>{flow_df['packet_loss_rate'].max():.2%}</td></tr>
                <tr><td>Total Bytes Transferred</td><td>{total_bytes / 1024 / 1024:.2f} MB</td></tr>
                <tr><td>Total Packets Transmitted</td><td>{flow_df['txPackets'].sum()}</td></tr>
                <tr><td>Total Packets Received</td><td>{flow_df['rxPackets'].sum()}</td></tr>
            </table>
            """
        
        html_content += f"""
            <h2>Network Topology</h2>
            <img src="network_topology_analysis.png" alt="Network Topology">
            
            <h2>Flow Analysis</h2>
            <img src="flow_analysis.png" alt="Flow Analysis">
            
            <h2>Animation</h2>
            <p>The network animation shows the dynamic behavior of the mesh network:</p>
            <ul>
                <li>STA nodes moving with RandomWalk2d mobility model</li>
                <li>Building obstacles with scheduled movements</li>
                <li>Mesh network connectivity and routing</li>
                <li>Sayed-Sadia communication through the mesh</li>
                <li>STA nodes accessing internet through backhaul</li>
            </ul>
            
            <h2>Key Features Demonstrated</h2>
            <ul>
                <li><strong>Backhaul Connectivity:</strong> Internet gateway with point-to-point connection</li>
                <li><strong>Mesh Backbone:</strong> Chain of mesh hop nodes providing connectivity</li>
                <li><strong>STA Access:</strong> Mobile nodes connecting to nearest mesh hop</li>
                <li><strong>Special Communication:</strong> Sayed-Sadia direct communication</li>
                <li><strong>Dynamic Environment:</strong> Moving buildings affecting propagation</li>
                <li><strong>Multiple Traffic Patterns:</strong> UDP, TCP, and internet access flows</li>
            </ul>
            
            <h2>Files Generated</h2>
            <ul>
                <li>wifi_mesh_backhaul_animation.gif - Network animation</li>
                <li>wifi_mesh_backhaul_topology.png - Static topology overview</li>
                <li>network_topology_analysis.png - Topology analysis</li>
                <li>flow_analysis.png - Flow performance analysis</li>
                <li>flowmon-wifi-mesh-backhaul.xml - FlowMonitor results</li>
                <li>wifi_mesh_backhaul_ascii_traces_mesh.tr - Detailed traces</li>
                <li>netanim-wifi-mesh-backhaul.xml - NetAnim animation file</li>
            </ul>
        </body>
        </html>
        """
        
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        print(f"Analysis report saved: {report_file}")
    
    def run_analysis(self):
        """Run complete analysis"""
        print("WiFi Mesh Backhaul Network Analyzer")
        print("=" * 50)
        
        if not os.path.exists(self.output_dir):
            print(f"Error: Output directory '{self.output_dir}' not found!")
            return
        
        # Analyze FlowMonitor results
        flow_df = self.analyze_flowmon_results()
        
        # Analyze ASCII traces
        trace_df = self.analyze_ascii_traces()
        
        # Create plots
        self.plot_network_topology()
        if flow_df is not None and not flow_df.empty:
            self.plot_flow_analysis(flow_df)
        
        # Generate report
        self.generate_report(flow_df, trace_df)
        
        print("\nAnalysis complete!")
        print(f"Results saved in: {self.output_dir}/")
        print("- wifi_mesh_backhaul_analysis_report.html")
        print("- network_topology_analysis.png")
        if flow_df is not None and not flow_df.empty:
            print("- flow_analysis.png")

def main():
    """Main function"""
    analyzer = WiFiMeshBackhaulAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()
