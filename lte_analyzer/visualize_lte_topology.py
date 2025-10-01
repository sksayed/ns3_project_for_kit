#!/usr/bin/env python3
"""
LTE Network Topology Visualizer
Shows UEs, eNBs, EPC components, and buildings with proper positions
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np
import os

# Network configuration (matching lte_playfield_traces.cc)
FIELD_SIZE = 400.0
N_UES = 10
OUTPUT_DIR = "Lte_outputs"

# Node positions
def get_node_positions():
    positions = {}
    
    # UE positions (from C++ code)
    positions['ue_0_sayed'] = (0.0, 0.0, 1.5)  # Sayed
    positions['ue_9_sadia'] = (FIELD_SIZE, FIELD_SIZE, 1.5)  # Sadia
    
    # Middle UEs (diagonal distribution with RandomWalk)
    for i in range(1, N_UES - 1):
        frac = i / (N_UES - 1)
        x = frac * FIELD_SIZE
        y = frac * FIELD_SIZE
        positions[f'ue_{i}'] = (x, y, 1.5)
    
    # eNB positions (UPDATED with new eNB1 position)
    positions['enb_0'] = (FIELD_SIZE * 0.25, FIELD_SIZE * 0.5, 15.0)  # (100, 200, 15)
    positions['enb_1'] = (100.0, 50.0, 15.0)  # NEW POSITION
    
    # EPC nodes (from C++ code)
    positions['pgw'] = (FIELD_SIZE * 0.5, FIELD_SIZE + 100.0, 0.0)
    positions['sgw'] = (FIELD_SIZE * 0.3, FIELD_SIZE + 100.0, 0.0)
    positions['remote_host'] = (FIELD_SIZE * 0.5, FIELD_SIZE + 50.0, 0.0)
    
    return positions

# Building positions (from C++ code)
def get_buildings():
    buildings = [
        {"name": "leftBelow", "bounds": (0.0, 60.0, 96.0, 104.0, 0.0, 10.0)},
        {"name": "rightBelow", "bounds": (340.0, 400.0, 96.0, 104.0, 0.0, 10.0)},
        {"name": "leftAbove", "bounds": (0.0, 60.0, 296.0, 304.0, 0.0, 10.0)},
        {"name": "rightAbove", "bounds": (340.0, 400.0, 296.0, 304.0, 0.0, 10.0)},
        {"name": "cluster250a", "bounds": (80.0, 140.0, 220.0, 228.0, 0.0, 15.0)},
        {"name": "cluster250b", "bounds": (170.0, 250.0, 220.0, 228.0, 0.0, 12.0)},
        {"name": "cluster50", "bounds": (255.0, 335.0, 20.0, 28.0, 0.0, 18.0)},
    ]
    return buildings

def plot_topology(use_tower_image=False):
    """Create LTE network topology visualization"""
    
    fig, ax = plt.subplots(figsize=(14, 16))
    
    positions = get_node_positions()
    buildings = get_buildings()
    
    # Draw buildings
    for building in buildings:
        xmin, xmax, ymin, ymax, zmin, zmax = building["bounds"]
        width = xmax - xmin
        height = ymax - ymin
        
        # Color based on height
        if zmax >= 15:
            color = '#654321'  # Dark brown for tall buildings
        else:
            color = '#8B7355'  # Lighter brown
            
        rect = Rectangle((xmin, ymin), width, height,
                         facecolor=color, alpha=0.8,
                         edgecolor='black', linewidth=1.5)
        ax.add_patch(rect)
        
        # Add building label
        ax.text(xmin + width/2, ymin + height/2, 
               f"{building['name']}\n{zmax}m", 
               fontsize=7, ha='center', va='center', color='white', weight='bold')
    
    # Draw connections
    # PGW to eNBs (backhaul)
    pgw_pos = positions['pgw']
    for i in range(2):
        enb_pos = positions[f'enb_{i}']
        ax.plot([pgw_pos[0], enb_pos[0]], [pgw_pos[1], enb_pos[1]], 
               'g--', linewidth=2, alpha=0.6, label='Backhaul' if i == 0 else '')
    
    # SGW to PGW
    sgw_pos = positions['sgw']
    ax.plot([sgw_pos[0], pgw_pos[0]], [sgw_pos[1], pgw_pos[1]], 
           'purple', linewidth=3, alpha=0.7, label='S1 Interface')
    
    # Remote Host to PGW
    rh_pos = positions['remote_host']
    ax.plot([rh_pos[0], pgw_pos[0]], [rh_pos[1], pgw_pos[1]], 
           'orange', linewidth=3, alpha=0.7, label='Internet Link')
    
    # Coverage circles for eNBs (illustrative)
    for i in range(2):
        enb_pos = positions[f'enb_{i}']
        circle = plt.Circle((enb_pos[0], enb_pos[1]), 150, 
                          color='cyan', alpha=0.15, linestyle='--', fill=True)
        ax.add_patch(circle)
    
    # Draw UEs
    for i in range(N_UES):
        if i == 0:
            key = 'ue_0_sayed'
            color = 'blue'
            marker = 'D'
            size = 200
            label = 'Sayed (UE0)'
        elif i == N_UES - 1:
            key = 'ue_9_sadia'
            color = 'red'
            marker = 'D'
            size = 200
            label = 'Sadia (UE9)'
        else:
            key = f'ue_{i}'
            color = 'lightblue'
            marker = 'o'
            size = 100
            label = f'UE{i}' if i == 1 else ''
        
        pos = positions[key]
        ax.scatter(pos[0], pos[1], c=color, s=size, marker=marker, 
                  edgecolors='black', linewidth=2, zorder=5,
                  label=label if i in [0, 1, N_UES-1] else '')
        
        # Add label
        offset = 15 if i in [0, N_UES-1] else 10
        ax.annotate(f'UE{i}' if i not in [0, N_UES-1] else label.split()[0], 
                   (pos[0], pos[1]), xytext=(5, offset), 
                   textcoords='offset points', fontsize=9, weight='bold')
    
    # Draw eNBs
    for i in range(2):
        pos = positions[f'enb_{i}']
        
        if use_tower_image:
            # Draw a simple tower shape
            # Tower base
            tower_width = 20
            tower_height = 30
            tower_rect = FancyBboxPatch(
                (pos[0] - tower_width/2, pos[1] - tower_height/2),
                tower_width, tower_height,
                boxstyle="round,pad=0.05",
                facecolor='darkgray', edgecolor='black', linewidth=2,
                zorder=4
            )
            ax.add_patch(tower_rect)
            
            # Tower antenna (triangle on top)
            triangle = plt.Polygon([
                (pos[0], pos[1] + tower_height/2 + 15),
                (pos[0] - 10, pos[1] + tower_height/2),
                (pos[0] + 10, pos[1] + tower_height/2)
            ], facecolor='red', edgecolor='black', linewidth=1, zorder=4)
            ax.add_patch(triangle)
        else:
            # Simple marker
            ax.scatter(pos[0], pos[1], c='darkgray', s=400, marker='^', 
                      edgecolors='black', linewidth=3, zorder=4)
        
        ax.annotate(f'eNB{i}\n({pos[0]:.0f},{pos[1]:.0f})', 
                   (pos[0], pos[1]), xytext=(25, 5), 
                   textcoords='offset points', fontsize=11, weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Draw EPC nodes
    # PGW
    ax.scatter(pgw_pos[0], pgw_pos[1], c='purple', s=300, marker='s', 
              edgecolors='black', linewidth=2, zorder=5, label='PGW')
    ax.annotate('PGW\n(Gateway)', (pgw_pos[0], pgw_pos[1]), 
               xytext=(10, 10), textcoords='offset points', 
               fontsize=10, weight='bold')
    
    # SGW
    ax.scatter(sgw_pos[0], sgw_pos[1], c='magenta', s=300, marker='s', 
              edgecolors='black', linewidth=2, zorder=5, label='SGW')
    ax.annotate('SGW\n(Gateway)', (sgw_pos[0], sgw_pos[1]), 
               xytext=(10, 10), textcoords='offset points', 
               fontsize=10, weight='bold')
    
    # Remote Host
    ax.scatter(rh_pos[0], rh_pos[1], c='green', s=300, marker='*', 
              edgecolors='black', linewidth=2, zorder=5, label='Internet Server')
    ax.annotate('Remote\nHost', (rh_pos[0], rh_pos[1]), 
               xytext=(10, 10), textcoords='offset points', 
               fontsize=10, weight='bold')
    
    # Styling
    ax.set_xlim(-50, FIELD_SIZE + 50)
    ax.set_ylim(-50, FIELD_SIZE + 200)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlabel('X Position (meters)', fontsize=12, weight='bold')
    ax.set_ylabel('Y Position (meters)', fontsize=12, weight='bold')
    ax.set_title('LTE Network Topology - Playfield Simulation\n' + 
                'Updated eNB Positions with EPC Infrastructure', 
                fontsize=16, weight='bold', pad=20)
    
    # Legend
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
    
    # Add info box
    info_text = f"""Network Configuration:
• Field: {FIELD_SIZE}m × {FIELD_SIZE}m
• UEs: {N_UES} (Sayed, Sadia + 8 mobile)
• eNBs: 2 base stations
  - eNB0: (100, 200, 15)
  - eNB1: (100, 50, 15) ← Updated!
• EPC: PGW, SGW, Remote Host
• Buildings: 7 obstacles (10-18m height)
• Coverage: ~150m radius per eNB
"""
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
           fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    plt.tight_layout()
    
    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, 'lte_topology_visualization.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Topology visualization saved: {output_file}")
    
    # Also save with tower icons
    plt.close()

def main():
    print("Creating LTE network topology visualization...")
    print("=" * 60)
    
    # Create visualization with tower-like icons
    plot_topology(use_tower_image=True)
    
    print("\n✓ Visualization complete!")
    print(f"  Output: {OUTPUT_DIR}/lte_topology_visualization.png")
    print("\nFeatures shown:")
    print("  ✓ Updated eNB positions (eNB1 now at 100, 50)")
    print("  ✓ EPC components (PGW, SGW, Remote Host)")
    print("  ✓ All 10 UEs with Sayed and Sadia highlighted")
    print("  ✓ Buildings with heights")
    print("  ✓ Coverage areas and connections")
    print("  ✓ Tower-style eNB icons")

if __name__ == "__main__":
    main()

