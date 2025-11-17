#!/usr/bin/env python3
"""
3D Stage Visualization for WiFi Mesh Network
Visualizes the 400m × 400m × 30m stage with:
- 4 Mesh APs (wifi-router.png icons)
- Buildings
- Dimension labels
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import os
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.patches as mpatches

# ============================================================================
# Configuration from wifi-test-2-adhoc-grid-six.cc
# ============================================================================
STAGE_WIDTH = 400.0   # meters
STAGE_HEIGHT = 400.0  # meters
STAGE_DEPTH = 30.0    # meters (Z dimension)

# Mesh AP positions (4 nodes) - confirmed from code
MESH_AP_HEIGHT = 1.5  # meters
mesh_ap_positions = [
    (100.0, 100.0, MESH_AP_HEIGHT),
    (300.0, 100.0, MESH_AP_HEIGHT),
    (300.0, 300.0, MESH_AP_HEIGHT),
    (100.0, 300.0, MESH_AP_HEIGHT)
]

# Building definitions (from code lines 498-532)
buildings = [
    {"name": "leftBelow", "box": (0.0, 60.0, 96.0, 104.0, 0.0, 10.0), "type": "Residential"},
    {"name": "rightBelow", "box": (340.0, 400.0, 96.0, 104.0, 0.0, 10.0), "type": "Residential"},
    {"name": "leftAbove", "box": (0.0, 60.0, 296.0, 304.0, 0.0, 10.0), "type": "Residential"},
    {"name": "rightAbove", "box": (340.0, 400.0, 296.0, 304.0, 0.0, 10.0), "type": "Residential"},
    {"name": "cluster250a", "box": (80.0, 140.0, 320.0, 328.0, 0.0, 15.0), "type": "Office"},
    {"name": "cluster250b", "box": (170.0, 250.0, 300.0, 308.0, 0.0, 12.0), "type": "Office"},
    {"name": "cluster50", "box": (255.0, 335.0, 20.0, 28.0, 0.0, 18.0), "type": "Commercial"}
]

# Icon paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up from: wifi_test_research/six_node_layout/visualize_3d_stage.py
# To: ns3_project_for_kit/
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
ICON_DIR = os.path.join(PROJECT_ROOT, "icons")

ICON_PATHS = {
    "wifi_router": os.path.join(ICON_DIR, "wifi-router.png"),
    "mobile": os.path.join(ICON_DIR, "cell-phone.png"),
    "drone": os.path.join(ICON_DIR, "camera-drone.png")
}

# Generate 10 STA positions randomly (avoiding buildings)
import random
random.seed(42)  # For reproducibility

def is_inside_building(x, y, z, buildings):
    """Check if a point is inside any building"""
    for building in buildings:
        x_min, x_max, y_min, y_max, z_min, z_max = building["box"]
        if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
            return True
    return False

# Generate 10 random STA positions (avoiding buildings)
sta_positions = []
max_attempts = 1000
attempts = 0

while len(sta_positions) < 10 and attempts < max_attempts:
    x = random.uniform(10, STAGE_WIDTH - 10)  # Margin from edges
    y = random.uniform(10, STAGE_HEIGHT - 10)
    z = random.uniform(1, 10)  # Ground level to 10m height
    if not is_inside_building(x, y, z, buildings):
        sta_positions.append((x, y, z))
    attempts += 1

# Distribute some STAs at different heights for visual variety
# Increase z-axis (height) and move horizontally for some STAs
if len(sta_positions) >= 4:
    x, y, z = sta_positions[3]
    # Move STA 4 further horizontally (toward top-right corner)
    new_x = min(STAGE_WIDTH - 20, x + 150)  # Move right, but stay within bounds
    new_y = min(STAGE_HEIGHT - 20, y + 150)  # Move up, but stay within bounds
    sta_positions[3] = (new_x, new_y, z + 10)  # Increase height by 10m and move horizontally
    
if len(sta_positions) >= 5:
    x, y, z = sta_positions[4]
    # Move STA 5 further horizontally (toward bottom-left corner)
    new_x = max(20, x - 150)  # Move left, but stay within bounds
    new_y = max(20, y - 150)  # Move down, but stay within bounds
    sta_positions[4] = (new_x, new_y, z + 10)  # Increase height by 10m and move horizontally

if len(sta_positions) < 10:
    print(f"Warning: Only generated {len(sta_positions)} STA positions after {attempts} attempts")

# ============================================================================
# Icon Loading Functions
# ============================================================================
def load_icon(icon_path, size=(40, 40)):
    """Load and resize icon image"""
    if not os.path.exists(icon_path):
        print(f"Warning: Icon not found at {icon_path}")
        return None
    
    try:
        img = Image.open(icon_path)
        # Convert RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        img = img.resize(size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"Error loading icon {icon_path}: {e}")
        return None

def plot_icon_at_position_3d(ax, x, y, z, icon_path, icon_type, size=50):
    """Plot an icon at 3D coordinates using 2D projection overlay"""
    # Load icon
    icon_img = load_icon(icon_path, size=(size, size))
    
    # Draw colored marker at position (always show marker)
    colors = {"wifi_router": "red", "mobile": "blue", "drone": "green"}
    markers = {"wifi_router": "^", "mobile": "o", "drone": "D"}
    ax.scatter([x], [y], [z], c=colors.get(icon_type, "gray"), 
              s=700, marker=markers.get(icon_type, "o"),
              edgecolors='black', linewidths=2.5, alpha=0.8, zorder=5)
    
    # Project 3D coordinates to 2D screen coordinates and place icon
    if icon_img is not None:
        # Get current view angles
        elev = ax.elev
        azim = ax.azim
        
        # Convert 3D point to 2D projection
        # This is a simplified projection - matplotlib handles this internally
        # We'll use a workaround: place icon slightly offset in Z to make it visible
        # and use text annotation with icon as background
        
        # Alternative: Use OffsetImage in 2D projection
        # For 3D, we place the icon using a custom approach
        try:
            # Convert icon to array
            icon_array = np.array(icon_img)
            
            # Create a small surface patch with the icon texture
            # This is a workaround - matplotlib 3D doesn't directly support images
            # We'll use the marker approach with icon info in label instead
            
            # Place icon reference in the label (shown below)
            pass
        except Exception as e:
            print(f"Could not process icon for {icon_type}: {e}")
    
    return icon_img is not None

# ============================================================================
# Create 3D Visualization
# ============================================================================
def create_3d_stage_visualization(figsize=(16, 12)):
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
    # Draw Mesh APs (4 nodes) - Eiffel tower shape (triangle marker)
    # ========================================================================
    wifi_icon_path = ICON_PATHS["wifi_router"]
    
    for i, (x, y, z) in enumerate(mesh_ap_positions):
        # Draw AP with triangle marker (Eiffel tower shape), red color - larger size
        ax.scatter([x], [y], [z], c='red', s=800, marker='^', 
                  edgecolors='darkred', linewidths=3, alpha=0.9, zorder=10)
        
        # Label - adjusted position for larger marker
        ax.text(x, y, z + 5, f'AP{i+1}', fontsize=14, ha='center', va='bottom',
               weight='bold', color='red',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                        edgecolor='red', alpha=0.9, linewidth=1))
    
    # Add Mesh AP to legend (smaller size for legend, triangle marker)
    ax.scatter([], [], c='red', s=300, marker='^', 
              edgecolors='darkred', linewidths=2, label='Mesh AP', alpha=0.9)
    
    # ========================================================================
    # Draw STAs (10 stations) - purple color, star marker (matching 5G UEs)
    # ========================================================================
    for i, (x, y, z) in enumerate(sta_positions):
        # Draw STA with star marker (matching 5G UEs), purple color
        ax.scatter([x], [y], [z], c='purple', s=300, marker='*', 
                  edgecolors='darkviolet', linewidths=1.5, alpha=0.9, zorder=10)
        
        # Simple label - just STA number, positioned above
        ax.text(x, y, z + 2, f'STA{i+1}', 
               fontsize=10, ha='center', va='bottom',
               weight='bold', color='purple',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                        edgecolor='purple', alpha=0.9, linewidth=1))
    
    # Add STA to legend (matching 5G UEs style)
    if sta_positions:
        ax.scatter([], [], c='purple', s=150, marker='*', 
                  edgecolors='darkviolet', linewidths=1.5, label='STA', alpha=0.9)
    
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
    ax.set_title('3D Stage Visualization: WiFi Mesh Network', 
                fontsize=14, fontweight='bold', pad=15)
    
    # Set axis limits with padding
    ax.set_xlim(-80, STAGE_WIDTH + 80)
    ax.set_ylim(-80, STAGE_HEIGHT + 80)
    ax.set_zlim(-5, STAGE_DEPTH + 15)
    
    # Set viewing angle for better perspective - higher elevation for clearer view
    ax.view_init(elev=35, azim=45)
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add legend (smaller, cleaner) - only Mesh AP, no STAs
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9, 
             edgecolor='gray', fancybox=True, shadow=False)
    
    # Add simplified info box (smaller, less intrusive)
    info_text = (
        f"Stage: {STAGE_WIDTH}×{STAGE_HEIGHT}×{STAGE_DEPTH}m | "
        f"APs: {len(mesh_ap_positions)} | STAs: {len(sta_positions)} | Buildings: {len(buildings)}"
    )
    ax.text2D(0.5, 0.02, info_text, transform=ax.transAxes,
             fontsize=10, ha='center', verticalalignment='bottom',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                      edgecolor='gray', alpha=0.8, linewidth=1))
    
    plt.tight_layout()
    return fig, ax

# ============================================================================
# Create Icon Legend (removed - no icons to show)
# ============================================================================
def create_icon_legend(fig):
    """Icon legend removed - no icons to display"""
    # No icon legend needed
    pass

# ============================================================================
# Main Execution
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("3D Stage Visualization for WiFi Mesh Network")
    print("=" * 70)
    print(f"Stage Dimensions: {STAGE_WIDTH}m × {STAGE_HEIGHT}m × {STAGE_DEPTH}m")
    print(f"Mesh APs: {len(mesh_ap_positions)} nodes")
    print(f"  Positions: {mesh_ap_positions}")
    print(f"STAs: {len(sta_positions)} devices")
    print(f"  Positions: {sta_positions}")
    print(f"Buildings: {len(buildings)} structures")
    print(f"Icon Directory: {ICON_DIR}")
    print("=" * 70)
    
    # Verify icons exist
    print("\nChecking icons...")
    for icon_type, icon_path in ICON_PATHS.items():
        if os.path.exists(icon_path):
            print(f"  ✓ {icon_type}: {icon_path}")
        else:
            print(f"  ✗ {icon_type}: NOT FOUND at {icon_path}")
    
    print("\nCreating visualization...")
    # Create visualization with size optimized for PDF reports
    # A4 page width is ~8.27 inches, so 16 inches gives good detail when scaled
    fig, ax = create_3d_stage_visualization(figsize=(16, 12))
    
    # Add icon legend
    create_icon_legend(fig)
    
    # Save figure as high-quality PNG for PDF report inclusion
    output_dir = os.path.dirname(__file__)
    output_file = os.path.join(output_dir, "3d_stage_visualization.png")
    
    # Save with high DPI and proper settings for PDF inclusion
    # Use 300 DPI for high quality, and ensure white background
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white', 
                edgecolor='none', pad_inches=0.2, format='png')
    print(f"\n✓ High-quality PNG saved to: {output_file}")
    print(f"  - Resolution: 300 DPI (suitable for PDF reports)")
    print(f"  - Format: PNG with transparent background where applicable")
    print(f"  - Ready for inclusion in PDF report")
    
    # Optionally save as PDF (vector format, but 3D plots are rasterized anyway)
    # Uncomment if needed:
    # output_file_pdf = os.path.join(output_dir, "3d_stage_visualization.pdf")
    # plt.savefig(output_file_pdf, bbox_inches='tight', facecolor='white')
    # print(f"✓ PDF saved to: {output_file_pdf}")
    
    # Don't show interactive plot (comment out for batch processing)
    # plt.show()
    plt.close()  # Close figure to free memory
    
    print("\n" + "=" * 70)
    print("Visualization Complete!")
    print("=" * 70)
    print("Features:")
    print("  ✓ 3D stage boundaries (400m × 400m × 30m)")
    print("  ✓ 4 Mesh APs (red triangles - Eiffel tower shape)")
    print(f"  ✓ {len(sta_positions)} STAs (purple stars - matching 5G UEs)")
    print("  ✓ 7 Buildings (Residential/Office/Commercial)")
    print("  ✓ Dimension labels with arrows")
    print("  ✓ High-quality PNG output (300 DPI) - ready for PDF report")
    print("=" * 70)
    print(f"\nPNG file location: {output_file}")
    print("You can now include this PNG image in your PDF report.")
    print("=" * 70)

