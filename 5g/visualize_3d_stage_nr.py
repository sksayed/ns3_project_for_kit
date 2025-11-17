#!/usr/bin/env python3
"""
3D Stage Visualization for 5G NR Network
Visualizes the 400m × 400m × 30m stage with:
- 1 gNB (base station)
- UEs (user equipment)
- Buildings
- Dimension labels
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import os
import random

# ============================================================================
# Configuration from nr_playfield_traces.cc
# ============================================================================
STAGE_WIDTH = 400.0   # meters
STAGE_HEIGHT = 400.0  # meters
STAGE_DEPTH = 30.0    # meters (Z dimension)

# gNB position (from ConfigureGnbMobility)
GNB_POSITION = (200.0, 200.0, 30.0)  # Single gNB at center, 30m height

# Building definitions (from CreateBuildingObstacles - same as WiFi)
buildings = [
    {"name": "leftBelow", "box": (0.0, 60.0, 96.0, 104.0, 0.0, 10.0), "type": "Residential"},
    {"name": "rightBelow", "box": (340.0, 400.0, 96.0, 104.0, 0.0, 10.0), "type": "Residential"},
    {"name": "leftAbove", "box": (0.0, 60.0, 296.0, 304.0, 0.0, 10.0), "type": "Residential"},
    {"name": "rightAbove", "box": (340.0, 400.0, 296.0, 304.0, 0.0, 10.0), "type": "Residential"},
    {"name": "cluster250a", "box": (80.0, 140.0, 320.0, 328.0, 0.0, 15.0), "type": "Office"},
    {"name": "cluster250b", "box": (170.0, 250.0, 300.0, 308.0, 0.0, 12.0), "type": "Office"},
    {"name": "cluster50", "box": (255.0, 335.0, 20.0, 28.0, 0.0, 18.0), "type": "Commercial"}
]

def is_inside_building(x, y, z, buildings):
    """Check if a point is inside any building"""
    for building in buildings:
        x_min, x_max, y_min, y_max, z_min, z_max = building["box"]
        if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
            return True
    return False

def generate_ue_positions(num_ues, seed=None):
    """Generate random UE positions (avoiding buildings)"""
    if seed is not None:
        random.seed(seed)
    
    ue_positions = []
    max_attempts = 1000
    attempts = 0

    while len(ue_positions) < num_ues and attempts < max_attempts:
        x = random.uniform(0, STAGE_WIDTH)  # Full range 0-400
        y = random.uniform(0, STAGE_HEIGHT)  # Full range 0-400
        z = random.uniform(0, 30.0)  # Ground level to 30m height (minHeight=0, maxHeight=30)
        if not is_inside_building(x, y, z, buildings):
            ue_positions.append((x, y, z))
        attempts += 1

    if len(ue_positions) < num_ues:
        print(f"Warning: Only generated {len(ue_positions)} UE positions after {attempts} attempts")
    
    return ue_positions

def generate_manual_ue_positions_lte():
    """
    Manually set UE positions distributed all around the stage for LTE network.
    Positions are placed around the perimeter and distributed across the stage.
    """
    # Manually defined positions - distributed around the stage
    # Format: (x, y, z) - avoiding buildings
    # Buildings: leftBelow(0-60,96-104), rightBelow(340-400,96-104), 
    #            leftAbove(0-60,296-304), rightAbove(340-400,296-304),
    #            cluster250a(80-140,300-308), cluster250b(170-250,300-308),
    #            cluster50(255-335,20-28)
    manual_positions = [
        # Corners (4 positions) - away from buildings
        (20.0, 10.0, 5.0),      # Bottom-left corner (y=10 avoids cluster50)
        (380.0, 10.0, 8.0),     # Bottom-right corner (y=10 avoids cluster50)
        (20.0, 380.0, 6.0),     # Top-left corner (away from leftAbove)
        (380.0, 380.0, 7.0),    # Top-right corner (away from rightAbove)
        
        # Edge centers (4 positions) - distributed along edges
        (200.0, 10.0, 10.0),    # Bottom edge center (y=10 avoids cluster50)
        (200.0, 350.0, 12.0),   # Top edge center (y=350 avoids cluster250a/b)
        (10.0, 200.0, 9.0),     # Left edge center (x=10 avoids leftBelow/leftAbove)
        (390.0, 200.0, 11.0),   # Right edge center (x=390 avoids rightBelow/rightAbove)
        
        # Distributed in quadrants (2 positions) - avoiding buildings
        (70.0, 150.0, 15.0),    # Lower-left quadrant (x=70 avoids leftBelow, y=150 avoids buildings)
        (340.0, 250.0, 18.0),   # Upper-right quadrant (x=340 avoids cluster250b, y=250 avoids cluster250a/b)
    ]
    
    # Verify positions don't overlap with buildings
    valid_positions = []
    for pos in manual_positions:
        x, y, z = pos
        if not is_inside_building(x, y, z, buildings):
            valid_positions.append(pos)
        else:
            # If inside building, adjust slightly
            # Try nearby positions
            adjusted = False
            for dx in [-15, 15, -25, 25]:
                for dy in [-15, 15, -25, 25]:
                    new_x = max(10, min(STAGE_WIDTH - 10, x + dx))
                    new_y = max(10, min(STAGE_HEIGHT - 10, y + dy))
                    if not is_inside_building(new_x, new_y, z, buildings):
                        valid_positions.append((new_x, new_y, z))
                        adjusted = True
                        break
                if adjusted:
                    break
    
    return valid_positions

# ============================================================================
# Create 3D Visualization
# ============================================================================
def create_3d_stage_visualization(figsize=(16, 12), is_lte=False, ue_positions=None):
    """
    Create 3D stage visualization optimized for PDF report inclusion.
    
    Args:
        figsize: Tuple of (width, height) in inches. Default (16, 12) for report.
    
    Returns:
        fig, ax: Matplotlib figure and axes objects
    """
    fig = plt.figure(figsize=figsize, facecolor='white')
    ax = fig.add_subplot(111, projection='3d')
    
    # ========================================================================
    # Draw the Stage (400m × 400m × 30m)
    # ========================================================================
    # Ground plane (semi-transparent)
    x_ground = np.array([0, STAGE_WIDTH, STAGE_WIDTH, 0])
    y_ground = np.array([0, 0, STAGE_HEIGHT, STAGE_HEIGHT])
    z_ground = np.array([0, 0, 0, 0])
    ax.plot_trisurf(x_ground, y_ground, z_ground, alpha=0.15, 
                    color='lightgray', edgecolor='gray', linewidth=0.5)
    
    # Stage boundaries (wireframe box)
    # Bottom face
    ax.plot([0, STAGE_WIDTH, STAGE_WIDTH, 0, 0], 
            [0, 0, STAGE_HEIGHT, STAGE_HEIGHT, 0],
            [0, 0, 0, 0, 0], 'k-', linewidth=1.5, alpha=0.4, label='Stage Boundary')
    
    # Top face
    ax.plot([0, STAGE_WIDTH, STAGE_WIDTH, 0, 0], 
            [0, 0, STAGE_HEIGHT, STAGE_HEIGHT, 0],
            [STAGE_DEPTH, STAGE_DEPTH, STAGE_DEPTH, STAGE_DEPTH, STAGE_DEPTH], 
            'k-', linewidth=1.5, alpha=0.4)
    
    # Vertical edges
    for x, y in [(0, 0), (STAGE_WIDTH, 0), (STAGE_WIDTH, STAGE_HEIGHT), (0, STAGE_HEIGHT)]:
        ax.plot([x, x], [y, y], [0, STAGE_DEPTH], 'k-', linewidth=1.5, alpha=0.4)
    
    # ========================================================================
    # Draw Buildings (more transparent, less intrusive)
    # ========================================================================
    building_colors = {
        "Residential": "#87CEEB",  # Sky blue
        "Office": "#FFB6C1",       # Light pink
        "Commercial": "#98FB98"    # Pale green
    }
    
    building_legend_added = {"Residential": False, "Office": False, "Commercial": False}
    
    for building in buildings:
        x_min, x_max, y_min, y_max, z_min, z_max = building["box"]
        btype = building["type"]
        color = building_colors.get(btype, "gray")
        
        # Create building box vertices
        vertices = [
            [x_min, y_min, z_min], [x_max, y_min, z_min],
            [x_max, y_max, z_min], [x_min, y_max, z_min],
            [x_min, y_min, z_max], [x_max, y_min, z_max],
            [x_max, y_max, z_max], [x_min, y_max, z_max]
        ]
        
        # Define faces
        faces = [
            [vertices[0], vertices[1], vertices[2], vertices[3]],  # bottom
            [vertices[4], vertices[5], vertices[6], vertices[7]],  # top
            [vertices[0], vertices[1], vertices[5], vertices[4]],   # front
            [vertices[2], vertices[3], vertices[7], vertices[6]],   # back
            [vertices[1], vertices[2], vertices[6], vertices[5]],   # right
            [vertices[0], vertices[3], vertices[7], vertices[4]]     # left
        ]
        
        # Draw building with lower alpha for less clutter
        label = btype if not building_legend_added[btype] else ""
        building_legend_added[btype] = True
        ax.add_collection3d(Poly3DCollection(faces, alpha=0.25, facecolor=color, 
                                           edgecolor='gray', linewidths=0.5, label=label))
    
    # ========================================================================
    # Draw gNB/eNB (base station) - red tower shape (Eiffel tower-like)
    # ========================================================================
    x, y, z = GNB_POSITION
    station_name = 'eNB' if is_lte else 'gNB'
    station_label = 'eNB (LTE Base Station)' if is_lte else 'gNB (Base Station)'
    
    # Draw base station with triangle marker (tower shape), red color - size 1100
    ax.scatter([x], [y], [z], c='red', s=1100, marker='^', 
              edgecolors='darkred', linewidths=3, alpha=0.9, zorder=10)
    
    # Label - adjusted position for larger marker
    ax.text(x, y, z + 5, station_name, fontsize=14, ha='center', va='bottom',
           weight='bold', color='red',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                    edgecolor='red', alpha=0.9, linewidth=1))
    
    # Add coordinates - adjusted position for larger marker
    ax.text(x, y, z - 2.5, f'({x:.0f},{y:.0f},{z:.0f}m)', 
           fontsize=9, ha='center', va='top',
           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
    
    # Add base station to legend - proportional size
    ax.scatter([], [], c='red', s=200, marker='^', 
              edgecolors='darkred', linewidths=2, label=station_label, alpha=0.9)
    
    # ========================================================================
    # Draw UEs (user equipment) - different from WiFi STAs
    # ========================================================================
    if ue_positions is None:
        ue_positions = []
    for i, (x, y, z) in enumerate(ue_positions):
        # Draw UE with star marker (different from WiFi hexagon), purple color
        ax.scatter([x], [y], [z], c='purple', s=300, marker='*', 
                  edgecolors='darkviolet', linewidths=1.5, alpha=0.9, zorder=10)
        
        # Simple label - just UE number, positioned above
        ax.text(x, y, z + 2, f'UE{i+1}', 
               fontsize=10, ha='center', va='bottom',
               weight='bold', color='purple',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                        edgecolor='purple', alpha=0.9, linewidth=1))
    
    # Add UE to legend
    if ue_positions:
        ax.scatter([], [], c='purple', s=150, marker='*', 
                  edgecolors='darkviolet', linewidths=1.5, label='UE (User Equipment)', alpha=0.9)
    
    # ========================================================================
    # Add Dimension Labels (Simplified - smaller, cleaner)
    # ========================================================================
    # X-axis dimension (400m Width) - smaller arrow
    ax.quiver(0, -15, 0, STAGE_WIDTH, 0, 0, color='red', arrow_length_ratio=0.1,
             linewidth=1.5, alpha=0.6, length=STAGE_WIDTH)
    ax.text(STAGE_WIDTH/2, -25, 0, f'{STAGE_WIDTH}m', 
           fontsize=10, ha='center', color='red', weight='bold')
    
    # Y-axis dimension (400m Height) - smaller arrow
    ax.quiver(-15, 0, 0, 0, STAGE_HEIGHT, 0, color='green', arrow_length_ratio=0.1,
             linewidth=1.5, alpha=0.6, length=STAGE_HEIGHT)
    ax.text(-25, STAGE_HEIGHT/2, 0, f'{STAGE_HEIGHT}m', 
           fontsize=10, ha='center', color='green', weight='bold')
    
    # Z-axis dimension (30m Depth) - smaller arrow
    ax.quiver(-15, -15, 0, 0, 0, STAGE_DEPTH, color='blue', arrow_length_ratio=0.1,
             linewidth=1.5, alpha=0.6, length=STAGE_DEPTH)
    ax.text(-35, -35, STAGE_DEPTH/2, f'{STAGE_DEPTH}m', 
           fontsize=10, ha='center', color='blue', weight='bold')
    
    # ========================================================================
    # Configure Axes and View
    # ========================================================================
    ax.set_xlabel('X (meters)', fontsize=13, fontweight='bold', labelpad=10)
    ax.set_ylabel('Y (meters)', fontsize=13, fontweight='bold', labelpad=10)
    ax.set_zlabel('Z (meters)', fontsize=13, fontweight='bold', labelpad=10)
    title = '3D Stage Visualization: LTE Network' if is_lte else '3D Stage Visualization: 5G NR Network'
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    # Set axis limits with padding
    ax.set_xlim(-80, STAGE_WIDTH + 80)
    ax.set_ylim(-80, STAGE_HEIGHT + 80)
    ax.set_zlim(-5, STAGE_DEPTH + 15)
    
    # Set viewing angle for better perspective - higher elevation for clearer view
    ax.view_init(elev=35, azim=45)
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add legend (smaller, cleaner)
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9, 
             edgecolor='gray', fancybox=True, shadow=False)
    
    # Add simplified info box (smaller, less intrusive)
    station_type = "eNB" if is_lte else "gNB"
    info_text = (
        f"Stage: {STAGE_WIDTH}×{STAGE_HEIGHT}×{STAGE_DEPTH}m | "
        f"{station_type}: 1 | UEs: {len(ue_positions) if ue_positions else 0} | Buildings: {len(buildings)}"
    )
    ax.text2D(0.5, 0.02, info_text, transform=ax.transAxes,
             fontsize=10, ha='center', verticalalignment='bottom',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                      edgecolor='gray', alpha=0.8, linewidth=1))
    
    plt.tight_layout()
    return fig, ax

# ============================================================================
# Main Execution
# ============================================================================
if __name__ == "__main__":
    # Generate UE positions for 5G NR (seed 42)
    num_ues = 10
    ue_positions_nr = generate_ue_positions(num_ues, seed=42)
    
    # Generate UE positions for LTE (manually set, distributed all around)
    ue_positions_lte = generate_manual_ue_positions_lte()
    
    # ========================================================================
    # Generate 5G NR Visualization
    # ========================================================================
    print("=" * 70)
    print("3D Stage Visualization for 5G NR Network")
    print("=" * 70)
    print(f"Stage Dimensions: {STAGE_WIDTH}m × {STAGE_HEIGHT}m × {STAGE_DEPTH}m")
    print(f"gNB: 1 base station")
    print(f"  Position: {GNB_POSITION}")
    print(f"UEs: {len(ue_positions_nr)} devices")
    print(f"  Positions: {ue_positions_nr[:3]}... (showing first 3)")
    print(f"Buildings: {len(buildings)} structures")
    print("=" * 70)
    
    print("\nCreating 5G NR visualization...")
    fig, ax = create_3d_stage_visualization(figsize=(16, 12), is_lte=False, ue_positions=ue_positions_nr)
    
    output_dir = os.path.dirname(__file__)
    output_file_nr = os.path.join(output_dir, "3d_stage_visualization_nr.png")
    
    plt.savefig(output_file_nr, dpi=300, bbox_inches='tight', facecolor='white', 
                edgecolor='none', pad_inches=0.2, format='png')
    print(f"\n✓ High-quality PNG saved to: {output_file_nr}")
    plt.close()
    
    # ========================================================================
    # Generate LTE Visualization
    # ========================================================================
    print("\n" + "=" * 70)
    print("3D Stage Visualization for LTE Network")
    print("=" * 70)
    print(f"Stage Dimensions: {STAGE_WIDTH}m × {STAGE_HEIGHT}m × {STAGE_DEPTH}m")
    print(f"eNB: 1 base station (LTE tower)")
    print(f"  Position: {GNB_POSITION}")
    print(f"UEs: {len(ue_positions_lte)} devices")
    print(f"  Positions: {ue_positions_lte[:3]}... (showing first 3)")
    print(f"Buildings: {len(buildings)} structures")
    print("=" * 70)
    
    print("\nCreating LTE visualization...")
    fig, ax = create_3d_stage_visualization(figsize=(16, 12), is_lte=True, ue_positions=ue_positions_lte)
    
    output_file_lte = os.path.join(output_dir, "3d_stage_visualization_lte.png")
    
    plt.savefig(output_file_lte, dpi=300, bbox_inches='tight', facecolor='white', 
                edgecolor='none', pad_inches=0.2, format='png')
    print(f"\n✓ High-quality PNG saved to: {output_file_lte}")
    plt.close()
    
    print("\n" + "=" * 70)
    print("Visualization Complete!")
    print("=" * 70)
    print("Generated Files:")
    print(f"  ✓ 5G NR: {output_file_nr}")
    print(f"  ✓ LTE:   {output_file_lte}")
    print("\nFeatures (both visualizations):")
    print("  ✓ 3D stage boundaries (400m × 400m × 30m)")
    print("  ✓ 1 Base Station (red tower/triangle)")
    print(f"  ✓ {num_ues} UEs (purple stars)")
    print("  ✓ 7 Buildings (Residential/Office/Commercial)")
    print("  ✓ Dimension labels with arrows")
    print("  ✓ High-quality PNG output (300 DPI) - ready for PDF report")
    print("=" * 70)

