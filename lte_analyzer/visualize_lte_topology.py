#!/usr/bin/env python3
"""
LTE Network Topology Visualizer
Shows UEs, eNBs, EPC components, and buildings with proper positions
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np
import os
from io import BytesIO
try:
    import imageio.v2 as imageio
except Exception:
    imageio = None

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
    
    # eNB positions (UPDATED with new eNB1 position and added eNB2)
    positions['enb_0'] = (FIELD_SIZE * 0.25, FIELD_SIZE * 0.5, 15.0)  # (100, 200, 15)
    positions['enb_1'] = (100.0, 50.0, 15.0)  # NEW POSITION
    positions['enb_2'] = (300.0, 300.0, 15.0)  # Added third eNB for better coverage
    
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

# Time-scheduled wall (building) movement to match C++ schedules
def buildings_at_time(t_seconds: float):
    # Start with defaults
    base = {b["name"]: list(b["bounds"]) for b in get_buildings()}
    # Movements per C++ (approx at 5,6,7,8,10,11,12s)
    # cluster250a moves at 5s, 8s, 12s
    if t_seconds >= 5.0:
        base["cluster250a"] = [150.0, 210.0, 180.0, 188.0, 0.0, 8.0]  # (x:150-210, y:180-188, z:0-8)
    if t_seconds >= 8.0:
        base["cluster250a"] = [250.0, 310.0, 130.0, 138.0, 0.0, 8.0]
    if t_seconds >= 12.0:
        base["cluster250a"] = [100.0, 160.0, 280.0, 288.0, 0.0, 8.0]
    # cluster250b moves at 6s, 10s
    if t_seconds >= 6.0:
        base["cluster250b"] = [200.0, 280.0, 180.0, 188.0, 0.0, 8.0]
    if t_seconds >= 10.0:
        base["cluster250b"] = [130.0, 210.0, 300.0, 308.0, 0.0, 8.0]
    # cluster50 moves at 7s, 11s
    if t_seconds >= 7.0:
        base["cluster50"] = [255.0, 335.0, 80.0, 88.0, 0.0, 8.0]
    if t_seconds >= 11.0:
        base["cluster50"] = [215.0, 295.0, 180.0, 188.0, 0.0, 8.0]
    # Return list like get_buildings()
    out = []
    for name, b in base.items():
        out.append({"name": name, "bounds": tuple(b)})
    return out

# Persistent RandomWalk state for UEs (except Sayed and Sadia)
_MOBILE_RW_STATE = {
    'initialized': False,
    'positions': {},  # key -> (x,y,z)
}

def _init_mobile_positions():
    base = get_node_positions()
    positions = {}
    for i in range(1, N_UES - 1):  # UE1..UE8 are mobile
        key = f'ue_{i}'
        positions[key] = (base[key][0], base[key][1], base[key][2])
    _MOBILE_RW_STATE['positions'] = positions
    _MOBILE_RW_STATE['initialized'] = True

def _advance_randomwalk_positions(dt_seconds: float, speed_mps: float = 5.0):
    # Move each mobile UE by speed*dt in a random direction, clamp to bounds
    for i in range(1, N_UES - 1):
        key = f'ue_{i}'
        x, y, z = _MOBILE_RW_STATE['positions'][key]
        angle = np.random.uniform(0, 2 * np.pi)
        step = speed_mps * dt_seconds
        nx = max(0.0, min(FIELD_SIZE, x + step * np.cos(angle)))
        ny = max(0.0, min(FIELD_SIZE, y + step * np.sin(angle)))
        _MOBILE_RW_STATE['positions'][key] = (nx, ny, z)

# Draw function now takes buildings input
def plot_topology(use_tower_image=False, positions_override=None, buildings_override=None):
    """Create LTE network topology visualization"""
    
    fig, ax = plt.subplots(figsize=(14, 16))
    
    positions = positions_override if positions_override else get_node_positions()
    buildings = buildings_override if buildings_override else get_buildings()
    
    # Draw buildings (walls) in red
    for building in buildings:
        xmin, xmax, ymin, ymax, zmin, zmax = building["bounds"]
        width = xmax - xmin
        height = ymax - ymin
        color = '#cc0000'  # red walls
        rect = Rectangle((xmin, ymin), width, height,
                         facecolor=color, alpha=0.65,
                         edgecolor='darkred', linewidth=2.0)
        ax.add_patch(rect)
        ax.text(xmin + width/2, ymin + height/2, 
               f"{building['name']}\n{zmax}m", 
               fontsize=7, ha='center', va='center', color='white', weight='bold')

    # Draw connections
    # PGW to eNBs (backhaul)
    pgw_pos = positions['pgw']
    for i in range(3):
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
    for i in range(3):
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
    for i in range(3):
        pos = positions[f'enb_{i}']
        if use_tower_image:
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
            triangle = plt.Polygon([
                (pos[0], pos[1] + tower_height/2 + 15),
                (pos[0] - 10, pos[1] + tower_height/2),
                (pos[0] + 10, pos[1] + tower_height/2)
            ], facecolor='red', edgecolor='black', linewidth=1, zorder=4)
            ax.add_patch(triangle)
        else:
            ax.scatter(pos[0], pos[1], c='darkgray', s=400, marker='^', 
                      edgecolors='black', linewidth=3, zorder=4)
        ax.annotate(f'eNB{i}\n({pos[0]:.0f},{pos[1]:.0f})', 
                   (pos[0], pos[1]), xytext=(25, 5), 
                   textcoords='offset points', fontsize=11, weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Draw EPC nodes
    ax.scatter(pgw_pos[0], pgw_pos[1], c='purple', s=300, marker='s', 
              edgecolors='black', linewidth=2, zorder=5, label='PGW')
    ax.annotate('PGW\n(Gateway)', (pgw_pos[0], pgw_pos[1]), 
               xytext=(10, 10), textcoords='offset points', 
               fontsize=10, weight='bold')
    ax.scatter(sgw_pos[0], sgw_pos[1], c='magenta', s=300, marker='s', 
              edgecolors='black', linewidth=2, zorder=5, label='SGW')
    ax.annotate('SGW\n(Gateway)', (sgw_pos[0], sgw_pos[1]), 
               xytext=(10, 10), textcoords='offset points', 
               fontsize=10, weight='bold')
    ax.scatter(rh_pos[0], rh_pos[1], c='green', s=300, marker='*', 
              edgecolors='black', linewidth=2, zorder=5, label='Remote Host')
    ax.annotate('Remote\nHost', (rh_pos[0], rh_pos[1]), 
               xytext=(10, 10), textcoords='offset points', 
               fontsize=10, weight='bold')
    
    ax.set_xlim(-50, FIELD_SIZE + 50)
    ax.set_ylim(-50, FIELD_SIZE + 200)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlabel('X Position (meters)', fontsize=12, weight='bold')
    ax.set_ylabel('Y Position (meters)', fontsize=12, weight='bold')
    ax.set_title('LTE Network Topology - Playfield Simulation\n' + 
                'Updated eNB Positions with EPC Infrastructure', 
                fontsize=16, weight='bold', pad=20)
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
    info_text = f"""Network Configuration:
• Field: {FIELD_SIZE}m × {FIELD_SIZE}m
• UEs: {N_UES} (Sayed, Sadia + 8 mobile [RandomWalk])
• eNBs: 3 base stations
  - eNB0: (100, 200, 15)
  - eNB1: (100, 50, 15) ← Updated!
  - eNB2: (300, 300, 15) ← Added
• EPC: PGW, SGW, Remote Host
• Buildings: 7 red walls (moving per schedule)
• Coverage: ~150m radius per eNB
"""
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
           fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    plt.tight_layout()
    return fig

# Generate animated GIF with moving walls and RandomWalk-like UEs
def save_static_and_gif():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not _MOBILE_RW_STATE['initialized']:
        _init_mobile_positions()
    # Static PNG (initial state)
    base = get_node_positions()
    fig = plot_topology(use_tower_image=True, buildings_override=get_buildings(), positions_override=base)
    png_path = os.path.join(OUTPUT_DIR, 'lte_topology_visualization.png')
    fig.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"✓ Topology visualization saved: {png_path}")

    if imageio is None:
        print("imageio not available; skipping GIF generation")
        return
    frames = []
    total_frames = 20
    total_sim_secs = 12.0
    prev_t = 0.0
    for fidx in range(total_frames):
        t = total_sim_secs * (fidx / max(1, total_frames - 1))
        dt = t - prev_t
        prev_t = t
        # advance RW positions
        _advance_randomwalk_positions(dt_seconds=dt, speed_mps=5.0)
        # compose positions: fixed endpoints + mobile from state
        pos = get_node_positions()
        for key, xyz in _MOBILE_RW_STATE['positions'].items():
            pos[key] = xyz
        walls = buildings_at_time(t)
        fig = plot_topology(use_tower_image=False, positions_override=pos, buildings_override=walls)
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        try:
            img = imageio.imread(buf)
            frames.append(img)
        finally:
            buf.close()
        plt.close(fig)
    gif_path = os.path.join(OUTPUT_DIR, 'lte_topology_animation.gif')
    imageio.mimsave(gif_path, frames, duration=0.25, loop=0)
    print(f"✓ Topology animation saved: {gif_path}")


def main():
    print("Creating LTE network topology visualization...")
    print("=" * 60)
    save_static_and_gif()
    print("\n✓ Visualization complete!")
    print(f"  Output: {OUTPUT_DIR}/lte_topology_visualization.png")
    print(f"  Output: {OUTPUT_DIR}/lte_topology_animation.gif")

if __name__ == "__main__":
    main()

