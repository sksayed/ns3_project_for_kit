#!/usr/bin/env python3
"""
LTE Network Animation with Moving Buildings
Creates an animated visualization of the LTE simulation with moving buildings.
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import os
import sys
from datetime import datetime

class LTEAnimator:
    def __init__(self, output_dir="Lte_outputs"):
        self.output_dir = output_dir
        self.field_size = 400.0
        self.n_ues = 10
        self.n_enbs = 2
        
        # Node positions (will be updated during animation)
        self.ue_positions = self._generate_ue_positions()
        self.enb_positions = self._generate_enb_positions()
        
        # Building movement schedule (matches the C++ code)
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
        self.duration = 15.0  # seconds
        self.fps = 2  # frames per second
        self.total_frames = int(self.duration * self.fps)
        
        # UE movement simulation (RandomWalk2d parameters from C++ code)
        self.ue_speed = 50.0  # m/s (from C++ code)
        self.ue_bounds = (0, 400, 0, 400)  # Rectangle bounds
        self.ue_time_step = 1.0  # seconds (from C++ code)
        
        # UE trails for movement visualization
        self.ue_trails = [[] for _ in range(self.n_ues)]
        
    def _generate_ue_positions(self):
        """Generate UE positions along diagonal"""
        positions = []
        for i in range(self.n_ues):
            if i == 0:  # Sayed
                positions.append((0.0, 0.0))
            elif i == self.n_ues - 1:  # Sadia
                positions.append((self.field_size, self.field_size))
            else:  # Middle UEs
                frac = i / (self.n_ues - 1)
                x = frac * self.field_size
                y = frac * self.field_size
                positions.append((x, y))
        return positions
    
    def _generate_enb_positions(self):
        """Generate eNB positions"""
        return [
            (self.field_size * 0.25, self.field_size * 0.5),  # eNB 1
            (self.field_size * 0.75, self.field_size * 0.5),  # eNB 2
        ]
    
    def _create_building_schedule(self):
        """Create building movement schedule matching C++ code"""
        movements = {
            "cluster250a": [
                {"time": 0.0, "x": 80.0, "y": 220.0},  # Initial position (moved left)
                {"time": 5.0, "x": 150.0, "y": 180.0},
                {"time": 8.0, "x": 250.0, "y": 130.0},
                {"time": 12.0, "x": 100.0, "y": 280.0},
            ],
            "cluster250b": [
                {"time": 0.0, "x": 170.0, "y": 220.0},  # Initial position (moved left)
                {"time": 6.0, "x": 200.0, "y": 180.0},
                {"time": 10.0, "x": 130.0, "y": 300.0},
            ],
            "cluster50": [
                {"time": 0.0, "x": 255.0, "y": 20.0},  # Initial position (moved 15m more left)
                {"time": 7.0, "x": 255.0, "y": 80.0},
                {"time": 11.0, "x": 215.0, "y": 180.0},
            ]
        }
        return movements
    
    def _simulate_ue_movement(self, time):
        """Simulate RandomWalk2d movement for middle UEs (1-8)"""
        # Sayed (UE 0) and Sadia (UE 9) are static
        # Only UEs 1-8 move with RandomWalk2d
        
        # Reset to initial positions at start
        if time == 0:
            self.ue_positions = self._generate_ue_positions()
            return
        
        for i in range(1, self.n_ues - 1):  # UEs 1-8
            # More realistic random walk simulation
            # Use time-based seed for consistent movement
            np.random.seed(i * 1000 + int(time * 10))
            
            # Random direction change (not every frame)
            if np.random.random() < 0.3:  # 30% chance to change direction
                angle = np.random.uniform(0, 2 * np.pi)
                distance = self.ue_speed * 0.5  # Half the speed for smoother movement
                
                dx = distance * np.cos(angle)
                dy = distance * np.sin(angle)
                
                # Update position
                new_x = self.ue_positions[i][0] + dx
                new_y = self.ue_positions[i][1] + dy
                
                # Apply boundary constraints (bounce back)
                x_min, x_max, y_min, y_max = self.ue_bounds
                if new_x < x_min or new_x > x_max:
                    new_x = self.ue_positions[i][0] - dx
                if new_y < y_min or new_y > y_max:
                    new_y = self.ue_positions[i][1] - dy
                
                # Keep within bounds
                new_x = max(x_min, min(x_max, new_x))
                new_y = max(y_min, min(y_max, new_y))
                
                self.ue_positions[i] = (new_x, new_y)
    
    def _get_building_position_at_time(self, building_name, time):
        """Get building position at specific time"""
        movements = self.building_movements[building_name]
        
        # Find the appropriate position based on time
        for i in range(len(movements) - 1):
            if movements[i]["time"] <= time < movements[i + 1]["time"]:
                return movements[i]["x"], movements[i]["y"]
        
        # Return last position if time is beyond last movement
        return movements[-1]["x"], movements[-1]["y"]
    
    def _interpolate_building_position(self, building_name, time):
        """Interpolate building position between movement points"""
        movements = self.building_movements[building_name]
        
        # Find surrounding movement points
        for i in range(len(movements) - 1):
            if movements[i]["time"] <= time <= movements[i + 1]["time"]:
                t1, t2 = movements[i]["time"], movements[i + 1]["time"]
                x1, y1 = movements[i]["x"], movements[i]["y"]
                x2, y2 = movements[i + 1]["x"], movements[i + 1]["y"]
                
                # Linear interpolation
                if t2 == t1:
                    return x1, y1
                
                alpha = (time - t1) / (t2 - t1)
                x = x1 + alpha * (x2 - x1)
                y = y1 + alpha * (y2 - y1)
                return x, y
        
        # Return last position if time is beyond last movement
        return movements[-1]["x"], movements[-1]["y"]
    
    def create_animation(self):
        """Create the animated visualization"""
        print("Creating LTE animation with moving buildings...")
        
        # Set up the figure and axis
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Initialize plot elements
        ue_scatter = ax.scatter([], [], c='blue', s=100, label='Mobile UEs', zorder=4)
        sayed_scatter = ax.scatter([], [], c='cyan', s=150, marker='s', label='Sayed (Static)', zorder=5)
        sadia_scatter = ax.scatter([], [], c='orange', s=150, marker='s', label='Sadia (Static)', zorder=5)
        enb_scatter = ax.scatter([], [], c='red', s=200, marker='^', label='eNBs', zorder=5)
        
        # Trail lines for mobile UEs
        trail_lines = []
        for i in range(1, self.n_ues - 1):  # Only for mobile UEs
            line, = ax.plot([], [], 'b-', alpha=0.3, linewidth=1)
            trail_lines.append(line)
        
        # Static buildings
        static_rects = []
        for building in self.static_buildings:
            rect = plt.Rectangle((building["x"], building["y"]), 
                               building["w"], building["h"], 
                               facecolor='gray', alpha=0.7, zorder=2)
            ax.add_patch(rect)
            static_rects.append(rect)
        
        # Mobile buildings (will be updated in animation)
        mobile_rects = []
        mobile_height_texts = []
        for i, building in enumerate(self.mobile_buildings):
            rect = plt.Rectangle((0, 0), building["w"], building["h"], 
                               facecolor='red', alpha=0.8, zorder=3)
            ax.add_patch(rect)
            mobile_rects.append(rect)
            
            # Add height labels for buildings
            height_text = ax.text(0, 0, '', fontsize=8, ha='center', va='bottom',
                                bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.7))
            mobile_height_texts.append(height_text)
        
        # Time text
        time_text = ax.text(0.02, 0.98, '', transform=ax.transAxes, 
                           fontsize=12, verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Set up the plot
        ax.set_xlim(-20, self.field_size + 20)
        ax.set_ylim(-20, self.field_size + 20)
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.set_title('LTE Network with Moving Buildings')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        def animate(frame):
            """Animation function called for each frame"""
            time = frame / self.fps
            
            # Simulate UE movement for middle UEs (1-8)
            self._simulate_ue_movement(time)
            
            # Update UE positions
            ue_x = [pos[0] for pos in self.ue_positions[1:-1]]
            ue_y = [pos[1] for pos in self.ue_positions[1:-1]]
            
            # Update scatter plots
            ue_scatter.set_offsets(list(zip(ue_x, ue_y)))
            sayed_scatter.set_offsets([self.ue_positions[0]])
            sadia_scatter.set_offsets([self.ue_positions[-1]])
            
            # Update eNB positions (static)
            enb_x = [pos[0] for pos in self.enb_positions]
            enb_y = [pos[1] for pos in self.enb_positions]
            enb_scatter.set_offsets(list(zip(enb_x, enb_y)))
            
            # Update trails for mobile UEs
            for i, line in enumerate(trail_lines):
                ue_idx = i + 1  # UEs 1-8
                self.ue_trails[ue_idx].append(self.ue_positions[ue_idx])
                
                # Keep only last 20 positions for trail
                if len(self.ue_trails[ue_idx]) > 20:
                    self.ue_trails[ue_idx] = self.ue_trails[ue_idx][-20:]
                
                if len(self.ue_trails[ue_idx]) > 1:
                    trail_x = [pos[0] for pos in self.ue_trails[ue_idx]]
                    trail_y = [pos[1] for pos in self.ue_trails[ue_idx]]
                    line.set_data(trail_x, trail_y)
            
            # Update mobile building positions
            for i, building in enumerate(self.mobile_buildings):
                x, y = self._interpolate_building_position(building["name"], time)
                mobile_rects[i].set_xy((x, y))
                
                # Update height labels
                height = self.building_heights[building["name"]]
                mobile_height_texts[i].set_position((x + building["w"]/2, y + building["h"] + 5))
                mobile_height_texts[i].set_text(f'{height:.0f}m')
            
            # Update time display
            time_text.set_text(f'Time: {time:.1f}s')
            
            return [ue_scatter, sayed_scatter, sadia_scatter, enb_scatter, time_text] + mobile_rects
        
        # Create animation
        anim = animation.FuncAnimation(fig, animate, frames=self.total_frames,
                                     interval=1000/self.fps, blit=False, repeat=True)
        
        # Save animation
        os.makedirs(self.output_dir, exist_ok=True)
        output_file = os.path.join(self.output_dir, 'lte_animation.gif')
        print(f"Saving animation to {output_file}...")
        
        # Save as GIF
        anim.save(output_file, writer='pillow', fps=self.fps)
        
        # Also save as MP4 if ffmpeg is available
        try:
            mp4_file = os.path.join(self.output_dir, 'lte_animation.mp4')
            anim.save(mp4_file, writer='ffmpeg', fps=self.fps)
            print(f"Also saved as MP4: {mp4_file}")
        except:
            print("MP4 format not available (ffmpeg not found)")
        
        plt.show()
        print("Animation complete!")
        
        return anim
    
    def create_static_plot(self):
        """Create a static plot showing the network layout"""
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Plot UEs
        ue_x = [pos[0] for pos in self.ue_positions]
        ue_y = [pos[1] for pos in self.ue_positions]
        
        ax.scatter(ue_x[1:-1], ue_y[1:-1], c='blue', s=100, label='Mobile UEs', zorder=4)
        ax.scatter([ue_x[0]], [ue_y[0]], c='cyan', s=150, marker='s', label='Sayed', zorder=5)
        ax.scatter([ue_x[-1]], [ue_y[-1]], c='orange', s=150, marker='s', label='Sadia', zorder=5)
        
        # Plot eNBs
        enb_x = [pos[0] for pos in self.enb_positions]
        enb_y = [pos[1] for pos in self.enb_positions]
        ax.scatter(enb_x, enb_y, c='red', s=200, marker='^', label='eNBs', zorder=5)
        
        # Plot static buildings
        for building in self.static_buildings:
            rect = plt.Rectangle((building["x"], building["y"]), 
                               building["w"], building["h"], 
                               facecolor='gray', alpha=0.7, zorder=2)
            ax.add_patch(rect)
        
        # Plot initial positions of mobile buildings
        for building in self.mobile_buildings:
            x, y = self._get_building_position_at_time(building["name"], 0.0)
            rect = plt.Rectangle((x, y), building["w"], building["h"], 
                               facecolor='red', alpha=0.8, zorder=3)
            ax.add_patch(rect)
        
        # Add connections (UEs to nearest eNB)
        for i in range(len(self.ue_positions)):
            ue_x, ue_y = self.ue_positions[i]
            # Find nearest eNB
            min_dist = float('inf')
            nearest_enb = 0
            for j, (enb_x, enb_y) in enumerate(self.enb_positions):
                dist = np.sqrt((ue_x - enb_x)**2 + (ue_y - enb_y)**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_enb = j
            
            enb_x, enb_y = self.enb_positions[nearest_enb]
            ax.plot([ue_x, enb_x], [ue_y, enb_y], 
                   'k--', alpha=0.3, linewidth=1)
        
        # Label special nodes
        ax.annotate('Sayed', (self.ue_positions[0][0], self.ue_positions[0][1]), 
                   xytext=(10, 10), textcoords='offset points', 
                   fontsize=10, fontweight='bold')
        ax.annotate('Sadia', (self.ue_positions[-1][0], self.ue_positions[-1][1]), 
                   xytext=(10, 10), textcoords='offset points', 
                   fontsize=10, fontweight='bold')
        
        ax.set_xlim(-20, self.field_size + 20)
        ax.set_ylim(-20, self.field_size + 20)
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.set_title('LTE Network Layout')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        plt.tight_layout()
        output_file = os.path.join(self.output_dir, 'lte_static_layout.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Static layout saved to {output_file}")
        plt.show()

def main():
    """Main function"""
    print("LTE Network Animator")
    print("=" * 40)
    
    # Create animator
    animator = LTEAnimator()
    
    # Create static layout first
    print("\n1. Creating static network layout...")
    animator.create_static_plot()
    
    # Create animation
    print("\n2. Creating animated visualization...")
    animator.create_animation()
    
    print("\nAnimation generation complete!")
    print(f"Check the '{animator.output_dir}' directory for output files.")

if __name__ == "__main__":
    main()
