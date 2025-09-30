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
        self.field_size = 400.0
        
        # Network topology parameters (matching C++ code)
        self.n_mesh_hops = 4
        self.n_sta_per_mesh = 2
        self.n_total_stas = self.n_mesh_hops * self.n_sta_per_mesh
        self.n_total_nodes = 1 + self.n_mesh_hops + self.n_total_stas + 2  # backhaul + mesh + STA + Sayed/Sadia
        
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
        
        # Static buildings (corner buildings that don't move)
        self.static_buildings = [
            {"name": "leftBelow", "x": 0.0, "y": 96.0, "w": 60.0, "h": 8.0},
            {"name": "rightBelow", "x": 340.0, "y": 96.0, "w": 60.0, "h": 8.0},
            {"name": "leftAbove", "x": 0.0, "y": 296.0, "w": 60.0, "h": 8.0},
            {"name": "rightAbove", "x": 340.0, "y": 296.0, "w": 60.0, "h": 8.0},
        ]
        
        # Mobile buildings
        self.mobile_buildings = [
            {"name": "cluster250a", "w": 60.0, "h": 8.0},
            {"name": "cluster250b", "w": 80.0, "h": 8.0},
            {"name": "cluster50", "w": 80.0, "h": 8.0},
        ]
        
        # Animation parameters
        self.duration = 10.0  # seconds (updated to match C++ code)
        self.fps = 2  # frames per second
        self.total_frames = int(self.duration * self.fps)
        
        # Node movement simulation (RandomWalk2d parameters from C++ code)
        self.node_speed = 50.0  # m/s (from C++ code)
        self.node_bounds = (0, 400, 0, 400)  # Rectangle bounds
        self.node_time_step = 1.0  # seconds (from C++ code)
        
        # Node trails for movement visualization
        self.node_trails = [[] for _ in range(self.n_total_nodes)]
        
        # Node types and colors
        self.node_types = self._define_node_types()
        self.node_colors = self._define_node_colors()
        
    def _generate_node_positions(self):
        """Generate node positions matching C++ code layout"""
        positions = []
        
        # Backhaul node (node 0)
        positions.append((30.0, self.field_size/2))
        
        # Mesh hop nodes (nodes 1-4) - exact positions from C++ code
        mesh_positions = [
            (50.0, 10.0),    # Mesh0
            (150.0, 200.0),  # Mesh1
            (300.0, 390.0),  # Mesh2
            (370.0, 160.0),  # Mesh3
        ]
        for pos in mesh_positions:
            positions.append(pos)
        
        # STA nodes (nodes 5-12) - positioned around mesh nodes
        for i in range(self.n_total_stas):
            mesh_idx = i // self.n_sta_per_mesh
            sta_idx = i % self.n_sta_per_mesh
            
            # Get mesh node position (exact coordinates from C++ code)
            mesh_positions = [
                (50.0, 10.0),    # Mesh0
                (150.0, 200.0),  # Mesh1
                (300.0, 390.0),  # Mesh2
                (370.0, 160.0),  # Mesh3
            ]
            mesh_x, mesh_y = mesh_positions[mesh_idx]
            
            # Position STA around mesh node
            angle = (sta_idx * 2 * np.pi) / self.n_sta_per_mesh
            distance = 40.0  # Distance from mesh node
            x = mesh_x + distance * np.cos(angle)
            y = mesh_y + distance * np.sin(angle)
            
            # Ensure within bounds
            x = max(10.0, min(self.field_size - 10.0, x))
            y = max(10.0, min(self.field_size - 10.0, y))
            
            positions.append((x, y))
        
        # Sayed and Sadia (nodes 13-14)
        positions.append((0.0, 0.0))  # Sayed
        positions.append((self.field_size, self.field_size))  # Sadia
        
        return positions
    
    def _define_node_types(self):
        """Define node types for visualization"""
        types = []
        types.append("Backhaul")  # node 0
        for i in range(self.n_mesh_hops):
            types.append(f"Mesh{i}")  # nodes 1-4
        for i in range(self.n_total_stas):
            types.append(f"STA{i}")  # nodes 5-12
        types.append("Sayed")  # node 13
        types.append("Sadia")  # node 14
        return types
    
    def _define_node_colors(self):
        """Define colors for different node types"""
        colors = []
        colors.append('blue')  # Backhaul - blue
        for i in range(self.n_mesh_hops):
            colors.append('red')  # Mesh nodes - red
        for i in range(self.n_total_stas):
            colors.append('yellow')  # STA nodes - yellow
        colors.append('cyan')  # Sayed - cyan (original blue)
        colors.append('orange')  # Sadia - orange
        return colors
    
    def _create_building_schedule(self):
        """Create building movement schedule matching C++ code (adjusted for 10s sim)"""
        movements = {
            "cluster250a": [
                {"time": 0.0, "x": 80.0, "y": 220.0},  # Initial position (moved left)
                {"time": 2.0, "x": 150.0, "y": 180.0},
                {"time": 4.0, "x": 250.0, "y": 130.0},
                {"time": 7.0, "x": 100.0, "y": 280.0},
            ],
            "cluster250b": [
                {"time": 0.0, "x": 170.0, "y": 220.0},  # Initial position (moved left)
                {"time": 2.5, "x": 200.0, "y": 180.0},
                {"time": 5.0, "x": 130.0, "y": 300.0},
            ],
            "cluster50": [
                {"time": 0.0, "x": 255.0, "y": 20.0},  # Initial position (moved 15m more left)
                {"time": 3.0, "x": 255.0, "y": 80.0},
                {"time": 6.0, "x": 215.0, "y": 180.0},
            ]
        }
        return movements
    
    def _simulate_node_movement(self, time):
        """Simulate node movement based on RandomWalk2d parameters"""
        # Only STA nodes (nodes 5-12) are mobile
        for i in range(5, 13):  # STA nodes
            if i < len(self.node_positions):
                # Simple random walk simulation
                step_size = self.node_speed * (1.0 / self.fps)  # Distance per frame
                angle = np.random.uniform(0, 2 * np.pi)
                
                dx = step_size * np.cos(angle)
                dy = step_size * np.sin(angle)
                
                new_x = self.node_positions[i][0] + dx
                new_y = self.node_positions[i][1] + dy
                
                # Keep within bounds
                new_x = max(0, min(self.field_size, new_x))
                new_y = max(0, min(self.field_size, new_y))
                
                self.node_positions[i] = (new_x, new_y)
                
                # Add to trail
                self.node_trails[i].append((new_x, new_y))
                
                # Limit trail length
                if len(self.node_trails[i]) > 20:
                    self.node_trails[i].pop(0)
    
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
                "height": 10.0  # Default height
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
        """Draw network connections"""
        # Draw backhaul connection to first mesh node only (Mesh0) - RED
        backhaul_pos = self.node_positions[0]
        mesh0_pos = self.node_positions[1]  # Mesh0 is node 1
        ax.plot([backhaul_pos[0], mesh0_pos[0]], [backhaul_pos[1], mesh0_pos[1]], 
               'r-', alpha=0.8, linewidth=4, label='Backhaul Link')
        
        # Draw mesh hop chain connections (Mesh0 -> Mesh1 -> Mesh2 -> Mesh3)
        for i in range(1, self.n_mesh_hops):
            pos1 = self.node_positions[i]
            pos2 = self.node_positions[i + 1]
            ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], 
                   'r-', alpha=0.6, linewidth=2, label='Mesh Chain' if i == 1 else "")
        
        # Draw STA to mesh connections
        for i in range(5, 5 + self.n_total_stas):
            sta_pos = self.node_positions[i]
            mesh_idx = (i - 5) // self.n_sta_per_mesh + 1
            mesh_pos = self.node_positions[mesh_idx]
            ax.plot([sta_pos[0], mesh_pos[0]], [sta_pos[1], mesh_pos[1]], 
                   'g--', alpha=0.2, linewidth=0.5)
        
        # Note: Sayed and Sadia communicate through the mesh network, no direct link
    
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
                         f'Backhaul→Mesh→STA + Sayed↔Sadia + Internet Server')
        
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
        
        # Draw nodes with trails
        for i, (pos, node_type, color) in enumerate(zip(self.node_positions, self.node_types, self.node_colors)):
            # Draw trail for mobile nodes
            if i >= 5 and i < 13 and len(self.node_trails[i]) > 1:  # STA nodes
                trail_x = [p[0] for p in self.node_trails[i]]
                trail_y = [p[1] for p in self.node_trails[i]]
                self.ax.plot(trail_x, trail_y, color=color, alpha=0.3, linewidth=1)
            
            # Draw node
            if node_type == "Backhaul":
                self.ax.scatter(pos[0], pos[1], c=color, s=200, marker='^', 
                              edgecolors='black', linewidth=2, label='Backhaul' if i == 0 else "")
            elif node_type.startswith("Mesh"):
                self.ax.scatter(pos[0], pos[1], c=color, s=150, marker='s', 
                              edgecolors='black', linewidth=2, label='Mesh Hops' if i == 1 else "")
            elif node_type.startswith("STA"):
                self.ax.scatter(pos[0], pos[1], c=color, s=100, marker='o', 
                              edgecolors='black', linewidth=1, label='STA Nodes' if i == 5 else "")
            elif node_type == "Sayed":
                self.ax.scatter(pos[0], pos[1], c=color, s=180, marker='D', 
                              edgecolors='black', linewidth=2, label='Sayed')
            elif node_type == "Sadia":
                self.ax.scatter(pos[0], pos[1], c=color, s=180, marker='D', 
                              edgecolors='black', linewidth=2, label='Sadia')
            
            # Add node labels
            if i == 0:  # Backhaul
                self.ax.annotate('Backhaul\n(Gateway)', pos, xytext=(10, 10), 
                               textcoords='offset points', fontsize=8, weight='bold')
            elif i >= 1 and i <= self.n_mesh_hops:  # Mesh nodes
                self.ax.annotate(f'Mesh{i-1}', pos, xytext=(5, 5), 
                               textcoords='offset points', fontsize=8)
            elif i >= 5 and i < 5 + self.n_total_stas:  # STA nodes
                self.ax.annotate(f'STA{i-5}', pos, xytext=(5, -15), 
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
        stats_text = f"Time: {time:.1f}s | Nodes: {self.n_total_nodes} | " \
                    f"Mesh Hops: {self.n_mesh_hops} | STA Nodes: {self.n_total_stas}"
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
        ax.set_title('WiFi Mesh Backhaul Network - Topology Overview', fontsize=14, weight='bold')
        
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
                          edgecolors='black', linewidth=2, label='Backhaul Gateway')
            elif node_type.startswith("Mesh"):
                ax.scatter(pos[0], pos[1], c=color, s=150, marker='s', 
                          edgecolors='black', linewidth=2, label='Mesh Hops' if i == 1 else "")
            elif node_type.startswith("STA"):
                ax.scatter(pos[0], pos[1], c=color, s=100, marker='o', 
                          edgecolors='black', linewidth=1, label='STA Nodes' if i == 5 else "")
            elif node_type == "Sayed":
                ax.scatter(pos[0], pos[1], c=color, s=180, marker='D', 
                          edgecolors='black', linewidth=2, label='Sayed')
            elif node_type == "Sadia":
                ax.scatter(pos[0], pos[1], c=color, s=180, marker='D', 
                          edgecolors='black', linewidth=2, label='Sadia')
            
            # Add node labels
            if i == 0:
                ax.annotate('Backhaul', pos, xytext=(10, 10), 
                           textcoords='offset points', fontsize=10, weight='bold')
            elif i >= 1 and i <= self.n_mesh_hops:
                ax.annotate(f'Mesh{i-1}', pos, xytext=(5, 5), 
                           textcoords='offset points', fontsize=9)
            elif i >= 5 and i < 5 + self.n_total_stas:
                ax.annotate(f'STA{i-5}', pos, xytext=(5, -15), 
                           textcoords='offset points', fontsize=7)
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
        
        # Add legend
        ax.legend(loc='upper right', fontsize=10)
        
        
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
    print(f"- Mesh hops: {animator.n_mesh_hops}")
    print(f"- STA nodes: {animator.n_total_stas}")
    print(f"- Sayed & Sadia: 2")
    
    anim = animator.create_animation()
    
    print("\nAnimation complete!")
    print(f"Files saved in: {output_dir}/")
    print("- wifi_mesh_backhaul_animation.mp4 (or .gif)")
    print("- wifi_mesh_backhaul_topology.png")

if __name__ == "__main__":
    main()
