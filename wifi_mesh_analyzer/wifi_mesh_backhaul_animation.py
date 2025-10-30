#!/usr/bin/env python3
"""
WiFi Mesh Backhaul Network Animation with Moving Buildings
Creates an animated visualization of the WiFi mesh backhaul simulation with moving buildings.
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import os
import sys
from datetime import datetime

class WiFiMeshBackhaulAnimator:
    def __init__(self, output_dir="wifi_mesh_backhaul_outputs"):
        self.output_dir = output_dir
        self.field_size = 450.0
        
        # Network topology parameters (matching C++ code)
        self.n_mesh_hops = 9  # 3x3 grid of APs
        self.n_sta_per_mesh = 0
        self.n_total_stas = 0  # No STAs
        self.n_total_nodes = 1 + self.n_mesh_hops + self.n_total_stas + 2  # backhaul + 9 APs + 0 STAs + Sayed/Sadia = 12
        
        # Node positions (will be updated during animation)
        self.initial_node_positions = self._generate_node_positions()
        self.node_positions = self.initial_node_positions.copy()
        
        # Building movement schedule (matches the C++ code - adjusted for 10s sim)
        self.building_movements = self._create_building_schedule()
        
        # Building heights for 3D visualization
        self.building_heights = {
            "cluster250a": 15.0,  # 15m high
            "cluster250b": 12.0,  # 12m high  
            "cluster50": 18.0,    # 18m high (tallest)
        }
        
        # Static buildings (corner buildings that don't move) - matching C++ lines 155-165
        self.static_buildings = [
            {"name": "leftBelow", "x": 0.0, "y": 96.0, "w": 60.0, "h": 8.0, "height": 10.0},
            {"name": "rightBelow", "x": 340.0, "y": 96.0, "w": 60.0, "h": 8.0, "height": 10.0},
            {"name": "leftAbove", "x": 0.0, "y": 296.0, "w": 60.0, "h": 8.0, "height": 10.0},
            {"name": "rightAbove", "x": 340.0, "y": 296.0, "w": 60.0, "h": 8.0, "height": 10.0},
        ]
        
        # Mobile buildings
        self.mobile_buildings = [
            {"name": "cluster250a", "w": 60.0, "h": 8.0},
            {"name": "cluster250b", "w": 80.0, "h": 8.0},
            {"name": "cluster50", "w": 80.0, "h": 8.0},
        ]
        
        # Animation parameters
        self.duration = 15.0  # seconds (updated to match C++ code)
        self.fps = 2  # frames per second
        self.total_frames = int(self.duration * self.fps)
        
        # Node movement simulation (RandomWalk2d parameters from C++ code)
        self.node_speed = 15.0  # m/s (from C++ code - updated to static nodes)
        self.node_bounds = (0, 450, 0, 450)  # Rectangle bounds
        self.node_time_step = 1.0  # seconds (from C++ code)
        
        # Node trails for movement visualization
        self.node_trails = [[] for _ in range(self.n_total_nodes)]
        
        # Node types and colors
        self.node_types = self._define_node_types()
        self.node_colors = self._define_node_colors()
        
    def _generate_node_positions(self):
        """Generate node positions matching C++ code layout"""
        positions = []
        
        # Backhaul node (node 0) - at center
        positions.append((self.field_size/2, self.field_size/2))  # (225, 225)
        
        # 9 Mesh APs in 3x3 grid (nodes 1-9)
        grid_size = 3
        ap_spacing = 150.0
        offset = ap_spacing / 2.0  # = 75.0
        
        for row in range(grid_size):
            for col in range(grid_size):
                x = offset + col * ap_spacing
                y = offset + row * ap_spacing
                positions.append((x, y))
        
        # Results:
        # AP0: (75, 75), AP1: (225, 75), AP2: (375, 75)
        # AP3: (75, 225), AP4: (225, 225), AP5: (375, 225)
        # AP6: (75, 375), AP7: (225, 375), AP8: (375, 375)
        
        # No STA nodes
        
        # Sayed and Sadia (nodes 10-11)
        positions.append((80.0, 80.0))     # Sayed - near AP0
        positions.append((370.0, 370.0))   # Sadia - near AP8
        
        return positions
    
    def _define_node_types(self):
        """Define node types for visualization"""
        types = []
        types.append("Backhaul")  # node 0
        for i in range(9):
            types.append(f"AP{i}")  # nodes 1-9 (9 APs)
        # No STA nodes
        types.append("Sayed")  # node 10
        types.append("Sadia")  # node 11
        return types
    
    def _define_node_colors(self):
        """Define colors for different node types"""
        colors = []
        colors.append('blue')  # Backhaul - blue
        for i in range(9):
            colors.append('red')  # 9 APs - red
        # No STA nodes
        colors.append('cyan')  # Sayed - cyan
        colors.append('orange')  # Sadia - orange
        return colors
    
    def _create_building_schedule(self):
        """Create building movement schedule matching C++ code (15s simulation)"""
        movements = {
            "cluster250a": [
                {"time": 0.0, "x": 80.0, "y": 220.0},   # Initial position
                {"time": 5.0, "x": 150.0, "y": 180.0},  # Move at 5s
                {"time": 8.0, "x": 250.0, "y": 130.0},  # Move at 8s
                {"time": 12.0, "x": 100.0, "y": 280.0}, # Move at 12s
            ],
            "cluster250b": [
                {"time": 0.0, "x": 170.0, "y": 220.0},  # Initial position
                {"time": 6.0, "x": 200.0, "y": 180.0},  # Move at 6s
                {"time": 10.0, "x": 130.0, "y": 300.0}, # Move at 10s
            ],
            "cluster50": [
                {"time": 0.0, "x": 255.0, "y": 20.0},   # Initial position
                {"time": 7.0, "x": 255.0, "y": 80.0},   # Move at 7s
                {"time": 11.0, "x": 215.0, "y": 180.0}, # Move at 11s
            ]
        }
        return movements
    
    def _simulate_node_movement(self, time):
        """Simulate node movement - ALL NODES ARE STATIC in this simulation"""
        # No movement - Sayed, Sadia, all APs, and backhaul are static
        # Buildings move but nodes don't
        pass
    
    def _get_building_positions(self, time):
        """Get building positions at given time"""
        buildings = []
        
        # Static buildings
        for building in self.static_buildings:
            buildings.append({
                "name": building["name"],
                "x": building["x"],
                "y": building["y"],
                "w": building["w"],
                "h": building["h"],
                "height": building.get("height", 10.0)
            })
        
        # Mobile buildings
        for building in self.mobile_buildings:
            movements = self.building_movements[building["name"]]
            current_pos = movements[0]  # Default to first position
            
            # Find current position based on time
            for i, movement in enumerate(movements):
                if time >= movement["time"]:
                    if i + 1 < len(movements):
                        # Interpolate between current and next position
                        next_movement = movements[i + 1]
                        if time < next_movement["time"]:
                            # Linear interpolation
                            t_ratio = (time - movement["time"]) / (next_movement["time"] - movement["time"])
                            x = movement["x"] + t_ratio * (next_movement["x"] - movement["x"])
                            y = movement["y"] + t_ratio * (next_movement["y"] - movement["y"])
                            current_pos = {"x": x, "y": y}
                        else:
                            current_pos = movement
                    else:
                        current_pos = movement
                else:
                    break
            
            buildings.append({
                "name": building["name"],
                "x": current_pos["x"],
                "y": current_pos["y"],
                "w": building["w"],
                "h": building["h"],
                "height": self.building_heights[building["name"]]
            })
        
        return buildings
    
    def _draw_network_connections(self, ax):
        """Draw network connections for 3x3 mesh grid"""
        backhaul_pos = self.node_positions[0]
        
        # Draw backhaul to center AP (AP4 at index 5)
        center_ap_pos = self.node_positions[5]  # AP4 is at index 5 (1 backhaul + 4 APs in grid order)
        ax.plot([backhaul_pos[0], center_ap_pos[0]], 
               [backhaul_pos[1], center_ap_pos[1]], 
               'r-', alpha=0.8, linewidth=4, label='Backhaul Link')
        
        # Draw mesh connections (neighboring APs in 3x3 grid)
        grid_size = 3
        for row in range(grid_size):
            for col in range(grid_size):
                ap_idx = 1 + row * grid_size + col  # +1 for backhaul offset
                
                # Connect to right neighbor
                if col < grid_size - 1:
                    right_idx = ap_idx + 1
                    ax.plot([self.node_positions[ap_idx][0], self.node_positions[right_idx][0]],
                           [self.node_positions[ap_idx][1], self.node_positions[right_idx][1]],
                           'b-', alpha=0.4, linewidth=1.5)
                
                # Connect to bottom neighbor
                if row < grid_size - 1:
                    bottom_idx = ap_idx + grid_size
                    ax.plot([self.node_positions[ap_idx][0], self.node_positions[bottom_idx][0]],
                           [self.node_positions[ap_idx][1], self.node_positions[bottom_idx][1]],
                           'b-', alpha=0.4, linewidth=1.5)
        
        # No STA connections (no STAs in this simulation)
        # Note: Sayed and Sadia communicate through the mesh network
    
    def animate_frame(self, frame):
        """Animation frame update function"""
        time = frame / self.fps
        
        # Clear the plot
        self.ax.clear()
        
        # Update node positions (only STA nodes move)
        self._simulate_node_movement(time)
        
        # Get building positions
        buildings = self._get_building_positions(time)
        
        # Draw field (extended to show internet server)
        self.ax.set_xlim(-20, self.field_size + 20)
        self.ax.set_ylim(-20, self.field_size + 100)  # Extra space for internet server
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_title(f'WiFi Mesh Backhaul Network - Time: {time:.1f}s\n'
                         f'9 APs (3×3 Grid) + Static Nodes + Moving Buildings')
        
        # Draw buildings
        for building in buildings:
            rect = plt.Rectangle((building["x"], building["y"]), 
                               building["w"], building["h"],
                               facecolor='#8B4513', alpha=0.8,  # Dark brown color
                               edgecolor='black', linewidth=1)
            self.ax.add_patch(rect)
            
            # Add building height indicator
            if building["height"] > 10:
                height_text = f"{building['name']}\n({building['height']:.0f}m)"
                self.ax.text(building["x"] + building["w"]/2, 
                           building["y"] + building["h"]/2, 
                           height_text, ha='center', va='center', 
                           fontsize=8, weight='bold')
        
        # Draw network connections
        self._draw_network_connections(self.ax)
        
        # Draw nodes (no trails since all nodes are static)
        for i, (pos, node_type, color) in enumerate(zip(self.node_positions, self.node_types, self.node_colors)):
            # Draw node
            if node_type == "Backhaul":
                self.ax.scatter(pos[0], pos[1], c=color, s=200, marker='^', 
                              edgecolors='black', linewidth=2, label='Backhaul' if i == 0 else "")
            elif node_type.startswith("AP"):
                self.ax.scatter(pos[0], pos[1], c=color, s=150, marker='s', 
                              edgecolors='black', linewidth=2, label='Mesh APs' if i == 1 else "")
            elif node_type == "Sayed":
                self.ax.scatter(pos[0], pos[1], c=color, s=180, marker='D', 
                              edgecolors='black', linewidth=2, label='Sayed')
            elif node_type == "Sadia":
                self.ax.scatter(pos[0], pos[1], c=color, s=180, marker='D', 
                              edgecolors='black', linewidth=2, label='Sadia')
            
            # Add node labels
            if i == 0:  # Backhaul
                self.ax.annotate('Backhaul', pos, xytext=(5, 10), 
                               textcoords='offset points', fontsize=8, weight='bold')
            elif i >= 1 and i <= 9:  # APs
                self.ax.annotate(f'AP{i-1}', pos, xytext=(5, 5), 
                               textcoords='offset points', fontsize=7)
            elif node_type in ["Sayed", "Sadia"]:
                self.ax.annotate(node_type, pos, xytext=(10, 10), 
                               textcoords='offset points', fontsize=10, weight='bold')
        
        # Add internet server indicator (outside the playground)
        internet_x, internet_y = 30.0, self.field_size + 50  # Outside the 400x400 field
        self.ax.scatter(internet_x, internet_y, c='green', s=120, marker='*', 
                       edgecolors='black', linewidth=2, label='Internet Server')
        self.ax.annotate('Internet\nServer', (internet_x, internet_y), 
                        xytext=(10, 10), textcoords='offset points', 
                        fontsize=8, weight='bold')
        
        # Draw connection from internet server to backhaul
        backhaul_pos = self.node_positions[0]
        self.ax.plot([internet_x, backhaul_pos[0]], [internet_y, backhaul_pos[1]], 
                    'g--', alpha=0.8, linewidth=3, label='Internet Link')
        
        # Add legend
        self.ax.legend(loc='upper right', fontsize=8, framealpha=0.8)
        
        # Add time and statistics
        stats_text = f"Time: {time:.1f}s | Total Nodes: {self.n_total_nodes} | " \
                    f"Mesh APs: {self.n_mesh_hops} (3×3 grid) | Static Nodes"
        self.ax.text(0.02, 0.98, stats_text, transform=self.ax.transAxes, 
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
    
    def create_animation(self):
        """Create and save the animation"""
        # Create figure and axis
        self.fig, self.ax = plt.subplots(figsize=(14, 12))
        
        # Create animation
        anim = animation.FuncAnimation(self.fig, self.animate_frame, 
                                     frames=self.total_frames, 
                                     interval=1000/self.fps, 
                                     blit=False, repeat=True)
        
        # Save animation
        output_file = os.path.join(self.output_dir, "wifi_mesh_backhaul_animation.mp4")
        print(f"Creating animation: {output_file}")
        
        try:
            anim.save(output_file, writer='ffmpeg', fps=self.fps, bitrate=1800)
            print(f"Animation saved: {output_file}")
        except Exception as e:
            print(f"Error saving animation: {e}")
            print("Saving as GIF instead...")
            output_file = os.path.join(self.output_dir, "wifi_mesh_backhaul_animation.gif")
            anim.save(output_file, writer='pillow', fps=self.fps)
            print(f"Animation saved as GIF: {output_file}")
        
        # Also create a static overview
        self.create_static_overview()
        
        return anim
    
    def create_static_overview(self):
        """Create a static overview of the network topology"""
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Set up the plot (extended to show internet server)
        ax.set_xlim(-20, self.field_size + 20)
        ax.set_ylim(-20, self.field_size + 100)  # Extra space for internet server
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title('WiFi Mesh Backhaul Network - 9 APs (3×3) with Optimized Ranges', 
                    fontsize=14, weight='bold')
        
        # AP Ranges (matching the optimized ranges from C++ code)
        ap_ranges = [
            145.0,  # AP0 - Sayed corner (bottom-left)
            120.0,  # AP1 - Edge
            100.0,  # AP2 - Far corner
            120.0,  # AP3 - Edge
            170.0,  # AP4 - Center (key relay)
            120.0,  # AP5 - Edge
            100.0,  # AP6 - Far corner
            120.0,  # AP7 - Edge
            145.0   # AP8 - Sadia corner (top-right)
        ]
        
        # Color mapping for different ranges (visual hierarchy)
        range_colors = {
            100.0: {'color': '#00CED1', 'name': 'Cyan'},      # Smallest - cyan
            120.0: {'color': '#FFD700', 'name': 'Gold'},      # Medium - gold/yellow
            145.0: {'color': '#FF8C00', 'name': 'Orange'},    # Large - orange
            170.0: {'color': '#FF1493', 'name': 'DeepPink'}   # Largest - deep pink
        }
        
        # Draw AP coverage circles first (before buildings)
        for i in range(9):
            ap_idx = i + 1  # APs are at indices 1-9
            pos = self.initial_node_positions[ap_idx]
            range_radius = ap_ranges[i]
            range_color = range_colors[range_radius]['color']
            
            # Draw coverage circle with range-specific color
            circle = plt.Circle(pos, range_radius, color=range_color, alpha=0.15, 
                              linestyle='--', fill=True, linewidth=2)
            ax.add_patch(circle)
            
            # Add range label with matching color
            ax.text(pos[0], pos[1] - range_radius - 5, f'{range_radius:.0f}m', 
                   ha='center', va='top', fontsize=8, color=range_color, weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor=range_color, linewidth=2))
        
        # Draw buildings at time 0
        buildings = self._get_building_positions(0.0)
        for building in buildings:
            rect = plt.Rectangle((building["x"], building["y"]), 
                               building["w"], building["h"],
                               facecolor='#8B4513', alpha=0.8,  # Dark brown color
                               edgecolor='black', linewidth=1)
            ax.add_patch(rect)
            
            if building["height"] > 10:
                height_text = f"{building['name']}\n({building['height']:.0f}m)"
                ax.text(building["x"] + building["w"]/2, 
                       building["y"] + building["h"]/2, 
                       height_text, ha='center', va='center', 
                       fontsize=8, weight='bold')
        
        # Draw all nodes with initial positions
        for i, (pos, node_type, color) in enumerate(zip(self.initial_node_positions, self.node_types, self.node_colors)):
            if node_type == "Backhaul":
                ax.scatter(pos[0], pos[1], c=color, s=200, marker='^', 
                          edgecolors='black', linewidth=2, label='Backhaul Gateway', zorder=10)
            elif node_type.startswith("AP"):
                ax.scatter(pos[0], pos[1], c=color, s=150, marker='s', 
                          edgecolors='black', linewidth=2, label='9 Mesh APs (3×3)' if i == 1 else "", zorder=10)
            elif node_type == "Sayed":
                ax.scatter(pos[0], pos[1], c=color, s=180, marker='D', 
                          edgecolors='black', linewidth=2, label='Sayed (Static)', zorder=10)
            elif node_type == "Sadia":
                ax.scatter(pos[0], pos[1], c=color, s=180, marker='D', 
                          edgecolors='black', linewidth=2, label='Sadia (Static)', zorder=10)
            
            # Add node labels
            if i == 0:
                ax.annotate('Backhaul', pos, xytext=(5, 10), 
                           textcoords='offset points', fontsize=9, weight='bold')
            elif i >= 1 and i <= 9:
                # Add AP label with range info
                ap_num = i - 1
                ax.annotate(f'AP{ap_num}\n({ap_ranges[ap_num]:.0f}m)', pos, xytext=(5, 5), 
                           textcoords='offset points', fontsize=7, weight='bold')
            elif node_type in ["Sayed", "Sadia"]:
                ax.annotate(node_type, pos, xytext=(10, 10), 
                           textcoords='offset points', fontsize=10, weight='bold')
        
        # Draw network connections
        self._draw_network_connections(ax)
        
        # Add internet server (outside the playground)
        internet_x, internet_y = 30.0, self.field_size + 50  # Outside the 400x400 field
        ax.scatter(internet_x, internet_y, c='green', s=120, marker='*', 
                  edgecolors='black', linewidth=2, label='Internet Server')
        ax.annotate('Internet\nServer', (internet_x, internet_y), 
                   xytext=(10, 10), textcoords='offset points', 
                   fontsize=10, weight='bold')
        
        # Draw connection from internet server to backhaul
        backhaul_pos = self.node_positions[0]
        ax.plot([internet_x, backhaul_pos[0]], [internet_y, backhaul_pos[1]], 
               'g--', alpha=0.8, linewidth=3, label='Internet Link')
        
        # Add legend with range color information
        # Create custom legend entries for AP ranges
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='blue', edgecolor='black', label='Backhaul Gateway'),
            Patch(facecolor='red', edgecolor='black', label='9 Mesh APs (3×3)'),
            Patch(facecolor='cyan', edgecolor='black', label='Sayed (Static)'),
            Patch(facecolor='orange', edgecolor='black', label='Sadia (Static)'),
            Patch(facecolor='green', edgecolor='black', label='Internet Server'),
            Patch(facecolor='white', edgecolor='black', label='─────────'),  # Separator
            Patch(facecolor='#00CED1', alpha=0.5, label='100m Range (Far Corners)'),
            Patch(facecolor='#FFD700', alpha=0.5, label='120m Range (Edges)'),
            Patch(facecolor='#FF8C00', alpha=0.5, label='145m Range (Endpoints)'),
            Patch(facecolor='#FF1493', alpha=0.5, label='170m Range (Center)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9, title='Network Elements & AP Ranges')
        
        
        # Save static overview
        output_file = os.path.join(self.output_dir, "wifi_mesh_backhaul_topology.png")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Static overview saved: {output_file}")
        plt.close()

def main():
    """Main function to run the animation"""
    print("WiFi Mesh Backhaul Network Animator")
    print("=" * 50)
    
    # Check if output directory exists
    output_dir = "wifi_mesh_backhaul_outputs"
    if not os.path.exists(output_dir):
        print(f"Error: Output directory '{output_dir}' not found!")
        print("Please run the WiFi mesh backhaul simulation first.")
        return
    
    # Create animator
    animator = WiFiMeshBackhaulAnimator(output_dir)
    
    # Create animation
    print(f"Creating animation for {animator.duration}s simulation...")
    print(f"Network topology: {animator.n_total_nodes} nodes")
    print(f"- Backhaul: 1")
    print(f"- Mesh APs: {animator.n_mesh_hops} (3×3 grid)")
    print(f"- STA nodes: {animator.n_total_stas} (none)")
    print(f"- Sayed & Sadia: 2 (static)")
    print(f"- Buildings: 7 (4 static + 3 moving)")
    
    anim = animator.create_animation()
    
    print("\nAnimation complete!")
    print(f"Files saved in: {output_dir}/")
    print("- wifi_mesh_backhaul_animation.mp4 (or .gif)")
    print("- wifi_mesh_backhaul_topology.png")

if __name__ == "__main__":
    main()
