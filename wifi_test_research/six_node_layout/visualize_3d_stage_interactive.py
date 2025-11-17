#!/usr/bin/env python3
"""
Interactive 3D Stage Visualization for WiFi Mesh Network
Allows you to rotate, zoom, and adjust the view before saving
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import os
from PIL import Image

# ============================================================================
# Configuration from wifi-test-2-adhoc-grid-six.cc
# ============================================================================
STAGE_WIDTH = 400.0
STAGE_HEIGHT = 400.0
STAGE_DEPTH = 30.0
MESH_AP_HEIGHT = 1.5

mesh_ap_positions = [
    (100.0, 100.0, MESH_AP_HEIGHT),
    (300.0, 100.0, MESH_AP_HEIGHT),
    (300.0, 300.0, MESH_AP_HEIGHT),
    (100.0, 300.0, MESH_AP_HEIGHT)
]

buildings = [
    {"name": "leftBelow", "box": (0.0, 60.0, 96.0, 104.0, 0.0, 10.0), "type": "Residential"},
    {"name": "rightBelow", "box": (340.0, 400.0, 96.0, 104.0, 0.0, 10.0), "type": "Residential"},
    {"name": "leftAbove", "box": (0.0, 60.0, 296.0, 304.0, 0.0, 10.0), "type": "Residential"},
    {"name": "rightAbove", "box": (340.0, 400.0, 296.0, 304.0, 0.0, 10.0), "type": "Residential"},
    {"name": "cluster250a", "box": (80.0, 140.0, 320.0, 328.0, 0.0, 15.0), "type": "Office"},
    {"name": "cluster250b", "box": (170.0, 250.0, 300.0, 308.0, 0.0, 12.0), "type": "Office"},
    {"name": "cluster50", "box": (255.0, 335.0, 20.0, 28.0, 0.0, 18.0), "type": "Commercial"}
]

sta_positions = [
    (200.0, 200.0, 5.0),  # Mobile
    (150.0, 250.0, 15.0),  # Drone
]

# Icon paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
ICON_DIR = os.path.join(PROJECT_ROOT, "icons")

# ============================================================================
# Create Clean 3D Visualization
# ============================================================================
def create_clean_visualization(elevation=35, azimuth=45, show_labels=True):
    """Create a clean, uncluttered visualization"""
    fig = plt.figure(figsize=(16, 12), facecolor='white')
    ax = fig.add_subplot(111, projection='3d')
    
    # Ground plane (very subtle)
    x_ground = np.array([0, STAGE_WIDTH, STAGE_WIDTH, 0])
    y_ground = np.array([0, 0, STAGE_HEIGHT, STAGE_HEIGHT])
    z_ground = np.array([0, 0, 0, 0])
    ax.plot_trisurf(x_ground, y_ground, z_ground, alpha=0.1, 
                    color='lightgray', edgecolor='none')
    
    # Stage boundaries (subtle wireframe)
    ax.plot([0, STAGE_WIDTH, STAGE_WIDTH, 0, 0], 
            [0, 0, STAGE_HEIGHT, STAGE_HEIGHT, 0],
            [0, 0, 0, 0, 0], 'k-', linewidth=1, alpha=0.2)
    ax.plot([0, STAGE_WIDTH, STAGE_WIDTH, 0, 0], 
            [0, 0, STAGE_HEIGHT, STAGE_HEIGHT, 0],
            [STAGE_DEPTH, STAGE_DEPTH, STAGE_DEPTH, STAGE_DEPTH, STAGE_DEPTH], 
            'k-', linewidth=1, alpha=0.2)
    for x, y in [(0, 0), (STAGE_WIDTH, 0), (STAGE_WIDTH, STAGE_HEIGHT), (0, STAGE_HEIGHT)]:
        ax.plot([x, x], [y, y], [0, STAGE_DEPTH], 'k-', linewidth=1, alpha=0.2)
    
    # Buildings (very transparent)
    building_colors = {
        "Residential": "#87CEEB",
        "Office": "#FFB6C1",
        "Commercial": "#98FB98"
    }
    
    for building in buildings:
        x_min, x_max, y_min, y_max, z_min, z_max = building["box"]
        color = building_colors.get(building["type"], "gray")
        vertices = [
            [x_min, y_min, z_min], [x_max, y_min, z_min],
            [x_max, y_max, z_min], [x_min, y_max, z_min],
            [x_min, y_min, z_max], [x_max, y_min, z_max],
            [x_max, y_max, z_max], [x_min, y_max, z_max]
        ]
        faces = [
            [vertices[0], vertices[1], vertices[2], vertices[3]],
            [vertices[4], vertices[5], vertices[6], vertices[7]],
            [vertices[0], vertices[1], vertices[5], vertices[4]],
            [vertices[2], vertices[3], vertices[7], vertices[6]],
            [vertices[1], vertices[2], vertices[6], vertices[5]],
            [vertices[0], vertices[3], vertices[7], vertices[4]]
        ]
        ax.add_collection3d(Poly3DCollection(faces, alpha=0.15, facecolor=color, 
                                           edgecolor='lightgray', linewidths=0.3))
    
    # Mesh APs - large, clear markers
    for i, (x, y, z) in enumerate(mesh_ap_positions):
        ax.scatter([x], [y], [z], c='red', s=1200, marker='^', 
                  edgecolors='darkred', linewidths=3, alpha=1.0, zorder=10)
        if show_labels:
            ax.text(x, y, z + 4, f'AP{i+1}', fontsize=13, ha='center', va='bottom',
                   weight='bold', color='red',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                            edgecolor='red', alpha=0.95, linewidth=1.5))
    
    # STAs
    sta_types = ['mobile', 'drone']
    for i, (x, y, z) in enumerate(sta_positions):
        sta_type = sta_types[i % len(sta_types)]
        color = 'blue' if sta_type == 'mobile' else 'green'
        marker = 'o' if sta_type == 'mobile' else 'D'
        ax.scatter([x], [y], [z], c=color, s=1000, marker=marker,
                  edgecolors='black', linewidths=3, alpha=1.0, zorder=10)
        if show_labels:
            ax.text(x, y, z + 3, f'STA{i+1}', fontsize=12, ha='center', va='bottom',
                   weight='bold', color=color,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                            edgecolor=color, alpha=0.95, linewidth=1.5))
    
    # Minimal dimension labels (only if requested)
    if show_labels:
        ax.text(STAGE_WIDTH/2, -20, 0, f'{STAGE_WIDTH}m', 
               fontsize=9, ha='center', color='gray', weight='bold')
        ax.text(-20, STAGE_HEIGHT/2, 0, f'{STAGE_HEIGHT}m', 
               fontsize=9, ha='center', color='gray', weight='bold')
        ax.text(-30, -30, STAGE_DEPTH/2, f'{STAGE_DEPTH}m', 
               fontsize=9, ha='center', color='gray', weight='bold')
    
    # Configure axes
    ax.set_xlabel('X (m)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Y (m)', fontsize=11, fontweight='bold')
    ax.set_zlabel('Z (m)', fontsize=11, fontweight='bold')
    ax.set_title('3D Stage: WiFi Mesh Network (400m × 400m × 30m)', 
                fontsize=13, fontweight='bold', pad=12)
    
    ax.set_xlim(-50, STAGE_WIDTH + 50)
    ax.set_ylim(-50, STAGE_HEIGHT + 50)
    ax.set_zlim(-2, STAGE_DEPTH + 10)
    
    ax.view_init(elev=elevation, azim=azimuth)
    ax.grid(True, alpha=0.2, linestyle=':')
    
    # Simple legend
    ax.scatter([], [], c='red', s=1200, marker='^', 
              edgecolors='darkred', linewidths=3, label='Mesh AP', alpha=1.0)
    ax.scatter([], [], c='blue', s=1000, marker='o', 
              edgecolors='black', linewidths=3, label='Mobile STA', alpha=1.0)
    ax.scatter([], [], c='green', s=1000, marker='D', 
              edgecolors='black', linewidths=3, label='Drone STA', alpha=1.0)
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
    
    plt.tight_layout()
    return fig, ax

# ============================================================================
# Interactive Mode
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("Interactive 3D Stage Visualization")
    print("=" * 70)
    print("\nInstructions:")
    print("  1. Rotate: Click and drag")
    print("  2. Zoom: Scroll wheel")
    print("  3. Pan: Right-click and drag")
    print("  4. Adjust view until satisfied")
    print("  5. Close window when done")
    print("\nAfter closing, you'll be asked if you want to save the current view.")
    print("=" * 70)
    
    # Create visualization
    fig, ax = create_clean_visualization(elevation=35, azimuth=45, show_labels=True)
    
    # Show interactive plot
    plt.show()
    
    # After window closes, ask if user wants to save
    print("\n" + "=" * 70)
    save = input("Do you want to save this view as PNG? (y/n): ").strip().lower()
    
    if save == 'y':
        # Get current view angles
        elev = ax.elev
        azim = ax.azim
        print(f"\nSaving with view: elevation={elev:.1f}°, azimuth={azim:.1f}°")
        
        # Recreate with same view
        plt.close(fig)
        fig, ax = create_clean_visualization(elevation=elev, azimuth=azim, show_labels=True)
        
        output_file = os.path.join(SCRIPT_DIR, "3d_stage_visualization.png")
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✓ Saved to: {output_file}")
        plt.close()
    else:
        print("Not saving. Exiting.")
        plt.close()

