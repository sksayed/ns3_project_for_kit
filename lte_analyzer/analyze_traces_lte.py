#!/usr/bin/env python3
import re
import glob
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.patches import FancyArrowPatch
import pandas as pd
import numpy as np

TR_DIR = "Lte_outputs"
TR_GLOB = os.path.join(TR_DIR, "lte_playfield_ascii_traces*.tr")
IPV4_L3_TR = os.path.join(TR_DIR, "ipv4-l3.tr")

line_re = re.compile(
    r"^(?P<event>[tr])\s+"  # transmit/receive
    r"(?P<time>\d+\.\d+)\s+"  # seconds
    r"(?P<rate>\S+)\s+"  # e.g., OfdmRate6Mbps
    r"ns3::WifiMacHeader\s+\((?P<mac>[^)]*)\)"  # MAC header summary
)

ipv4_re = re.compile(r"ns3::Ipv4Header .* protocol\s+(?P<proto>\d+) .* length:\s*(?P<len>\d+)\s+(?P<src>\d+\.\d+\.\d+\.\d+)\s*>\s*(?P<dst>\d+\.\d+\.\d+\.\d+)")
udp_re = re.compile(r"ns3::UdpHeader \(length: \s*\d+\s+(?P<src_port>\d+)\s*>\s*(?P<dst_port>\d+)\)")
tcp_re = re.compile(r"ns3::TcpHeader .*? SrcPort=\s*(?P<src_port>\d+), DstPort=\s*(?P<dst_port>\d+)")
retry_re = re.compile(r"Retry=([01])")
type_re = re.compile(r"^(?P<type>\w+)")
ipv4_id_re = re.compile(r"\bid\s+(?P<ip_id>\d+)\b")
node_from_file_re = re.compile(r"ascii_traces-(?P<node>\d+)-")

# IPv4 L3 trace line example:
# t 3 /NodeList/0/$ns3::Ipv4L3Protocol/Tx(1) ns3::Ipv4Header (... protocol 6 ... id 0 ... 10.0.0.1 > 10.0.0.10) ns3::TcpHeader (49153 > 6000 ...)
ipv4_l3_line_re = re.compile(
    r"^(?P<event>[tr])\s+(?P<time>\d+\.?\d*)\s+/NodeList/(?P<node>\d+)/\$ns3::Ipv4L3Protocol/\w+.*?ns3::Ipv4Header.*?protocol\s+(?P<proto>\d+).*?id\s+(?P<ip_id>\d+).*?length:\s*(?P<len>\d+)\s+(?P<src>\d+\.\d+\.\d+\.\d+)\s*>\s*(?P<dst>\d+\.\d+\.\d+\.\d+)\).*?(ns3::TcpHeader\s*\((?P<tcp_sport>\d+)\s*>\s*(?P<tcp_dport>\d+)[^)]*\))?",
    re.IGNORECASE)

def parse_tr_file(path: str) -> pd.DataFrame:
    records = []
    node_hint = os.path.basename(path)
    node_id = None
    mf = node_from_file_re.search(node_hint)
    if mf:
        try:
            node_id = int(mf.group('node'))
        except Exception:
            node_id = None
    for line in open(path, 'r', errors='ignore'):
        m = line_re.search(line)
        if not m:
            continue
        event = m.group('event')
        time_s = float(m.group('time'))
        rate = m.group('rate')
        mac_summary = m.group('mac')

        mac_type = None
        mt = type_re.search(mac_summary)
        if mt:
            mac_type = mt.group('type')
        retry = None
        mr = retry_re.search(mac_summary)
        if mr:
            retry = int(mr.group(1))

        length = None
        src = dst = None
        l4 = None
        src_port = dst_port = None
        iv4 = ipv4_re.search(line)
        if iv4:
            length = int(iv4.group('len'))
            src = iv4.group('src')
            dst = iv4.group('dst')
            proto = int(iv4.group('proto')) if iv4.group('proto') is not None else None
            l4 = 'IP'
            mid = ipv4_id_re.search(line)
            ip_id = int(mid.group('ip_id')) if mid else None
            mu = udp_re.search(line)
            if mu:
                l4 = 'UDP'
                src_port = int(mu.group('src_port'))
                dst_port = int(mu.group('dst_port'))
            else:
                mtcp = tcp_re.search(line)
                if mtcp:
                    l4 = 'TCP'
                    src_port = int(mtcp.group('src_port'))
                    dst_port = int(mtcp.group('dst_port'))
                elif proto == 6:
                    # TCP without explicit TcpHeader print; ports unknown
                    l4 = 'TCP'
        else:
            ip_id = None

        records.append({
            'file': node_hint,
            'node': node_id,
            'event': event,
            'time': time_s,
            'rate': rate,
            'mac_type': mac_type,
            'retry': retry,
            'length': length,
            'src_ip': src,
            'dst_ip': dst,
            'ip_id': ip_id,
            'l4': l4,
            'src_port': src_port,
            'dst_port': dst_port,
        })
    return pd.DataFrame.from_records(records)

def load_all_traces() -> pd.DataFrame:
    frames = []
    for path in glob.glob(TR_GLOB):
        frames.append(parse_tr_file(path))
    # Merge in IPv4 L3 trace if present (to capture TCP)
    if os.path.exists(IPV4_L3_TR):
        frames.append(parse_ipv4_l3_file(IPV4_L3_TR))
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    return df

def parse_ipv4_l3_file(path: str) -> pd.DataFrame:
    records = []
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            m = ipv4_l3_line_re.search(line)
            if not m:
                continue
            event = m.group('event')
            time_s = float(m.group('time'))
            node = int(m.group('node'))
            proto = int(m.group('proto'))
            ip_id = int(m.group('ip_id'))
            length = int(m.group('len'))
            src = m.group('src')
            dst = m.group('dst')
            l4 = None
            src_port = None
            dst_port = None
            if proto == 6:
                l4 = 'TCP'
                if m.group('tcp_sport') and m.group('tcp_dport'):
                    src_port = int(m.group('tcp_sport'))
                    dst_port = int(m.group('tcp_dport'))
            elif proto == 17:
                l4 = 'UDP'
            records.append({
                'file': os.path.basename(path),
                'node': node,
                'event': event,
                'time': time_s,
                'rate': None,
                'mac_type': None,
                'retry': None,
                'length': length,
                'src_ip': src,
                'dst_ip': dst,
                'ip_id': ip_id,
                'l4': l4,
                'src_port': src_port,
                'dst_port': dst_port,
            })
    return pd.DataFrame.from_records(records)

def plot_rate_distribution(df: pd.DataFrame, out_dir: str):
    # Filter out empty rate values and check if we have data
    rate_data = df['rate'].dropna()
    if rate_data.empty:
        print("No rate data available for plotting")
        return
    
    counts = rate_data.value_counts().sort_index()
    if counts.empty:
        print("No rate data available for plotting")
        return
        
    plt.figure(figsize=(8,5))
    counts.plot(kind='bar')
    plt.title('PHY rate usage (all frames)')
    plt.ylabel('Frames')
    plt.xlabel('Rate')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'tr_rate_distribution.png'), dpi=200)
    plt.close()

def plot_mac_throughput(df: pd.DataFrame, out_dir: str):
    data = df[(df['mac_type'] == 'QOSDATA') & df['length'].notna()]
    if data.empty:
        return
    # Bytes per second over time (tx vs rx across all nodes/files)
    bins = np.arange(data['time'].min(), data['time'].max() + 0.5, 0.5)
    g = data.groupby([pd.cut(data['time'], bins=bins), 'event'])['length'].sum().unstack(fill_value=0)
    g.index = g.index.map(lambda iv: iv.left)
    plt.figure(figsize=(10,5))
    if 't' in g:
        plt.plot(g.index, g['t']*8/1e6, label='TX Mbps')
    if 'r' in g:
        plt.plot(g.index, g['r']*8/1e6, label='RX Mbps')
    plt.legend()
    plt.xlabel('Time (s)')
    plt.ylabel('Throughput (Mbps)')
    plt.title('MAC throughput over time (QOSDATA)')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'tr_mac_throughput.png'), dpi=200)
    plt.close()

def plot_udp_port_throughput(df: pd.DataFrame, out_dir: str):
    data = df[(df['l4'] == 'UDP') & df['length'].notna() & df['dst_port'].notna()]
    if data.empty:
        return
    agg = data.groupby('dst_port')['length'].sum().sort_values(ascending=False)
    plt.figure(figsize=(8,5))
    (agg*8/1e6).plot(kind='bar')
    plt.xlabel('UDP dst port')
    plt.ylabel('Total bits (Mb)')
    plt.title('UDP traffic by destination port (MAC level)')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'tr_udp_ports.png'), dpi=200)
    plt.close()

def compute_summary(df: pd.DataFrame) -> pd.DataFrame:
    total_frames = len(df)
    data = df[df['mac_type'] == 'QOSDATA']
    tx = (data['event'] == 't').sum()
    rx = (data['event'] == 'r').sum()
    retry_rate = data['retry'].fillna(0).mean() if not data.empty else 0
    by_rate = data['rate'].value_counts().rename_axis('rate').reset_index(name='frames')
    udp_ports = df[df['l4'] == 'UDP']['dst_port'].value_counts().rename_axis('udp_dst').reset_index(name='frames')
    summary_rows = [
        {'metric': 'total_frames', 'value': total_frames},
        {'metric': 'data_tx_frames', 'value': int(tx)},
        {'metric': 'data_rx_frames', 'value': int(rx)},
        {'metric': 'data_delivery_ratio', 'value': float(rx/tx) if tx else 0.0},
        {'metric': 'data_retry_rate_mean', 'value': float(retry_rate)},
    ]
    summary = pd.DataFrame(summary_rows)
    return summary, by_rate, udp_ports

def reconstruct_paths(df: pd.DataFrame, src_ip: str = '10.0.0.1', dst_ip: str = '10.0.0.10', dst_port: int = 5000) -> pd.DataFrame:
    # Consider only UDP frames matching the flow, with valid ip_id and node
    sel = df[(df['l4'] == 'UDP') & (df['dst_ip'] == dst_ip) & (df['src_ip'] == src_ip) & (df['dst_port'] == dst_port) & df['ip_id'].notna() & df['node'].notna()]
    if sel.empty:
        return pd.DataFrame()
    # For each IP packet id, take receive events ordered by time and list unique nodes
    paths = []
    for ip_id, grp in sel.sort_values('time').groupby('ip_id'):
        hop_nodes = grp['node'].tolist()
        # Keep order but de-duplicate consecutive duplicates
        dedup = []
        for n in hop_nodes:
            if not dedup or dedup[-1] != n:
                dedup.append(n)
        paths.append({
            'ip_id': int(ip_id),
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'dst_port': dst_port,
            'hops': '->'.join(map(str, dedup)),
            'hop_count': len(dedup)
        })
    return pd.DataFrame(paths).sort_values(['hop_count','ip_id'])

def reconstruct_tcp_paths(df: pd.DataFrame, src_ip: str, dst_ip: str, dst_port: int | None = None) -> pd.DataFrame:
    # Consider only TCP segments matching the flow, with valid ip_id and node
    sel = df[(df['l4'] == 'TCP') & (df['dst_ip'] == dst_ip) & (df['src_ip'] == src_ip) & df['ip_id'].notna() & df['node'].notna()]
    if dst_port is not None:
        sel = sel[(sel['dst_port'] == dst_port)]
    if sel.empty:
        return pd.DataFrame()
    # For each IP packet id, take receive events ordered by time and list unique nodes
    paths = []
    for ip_id, grp in sel[sel['event'] == 'r'].sort_values('time').groupby('ip_id'):
        hop_nodes = grp['node'].tolist()
        # Keep order but de-duplicate consecutive duplicates
        dedup = []
        for n in hop_nodes:
            if not dedup or dedup[-1] != n:
                dedup.append(n)
        paths.append({
            'ip_id': int(ip_id),
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'dst_port': dst_port,
            'hops': '->'.join(map(str, dedup)),
            'hop_count': len(dedup)
        })
    return pd.DataFrame(paths).sort_values(['hop_count','ip_id'])

def plot_most_common_path(paths_df: pd.DataFrame, out_dir: str, title_suffix: str = ''):
    if paths_df.empty:
        return
    # Find the most frequent hop string
    counts = paths_df['hops'].value_counts()
    path_str = counts.index[0]
    nodes = [int(x) for x in path_str.split('->')]
    # Simple linear plot of nodes in order
    plt.figure(figsize=(max(6, len(nodes)), 2.5))
    y = [0]*len(nodes)
    x = list(range(len(nodes)))
    plt.plot(x, y, '-o')
    for i, n in enumerate(nodes):
        plt.text(x[i], y[i]+0.05, f"{n}", ha='center')
    for i in range(len(nodes)-1):
        plt.arrow(x[i], 0, 0.8, 0, length_includes_head=True, head_width=0.05, head_length=0.1, fc='k', ec='k')
    plt.yticks([])
    plt.xlabel('Hop index')
    plt.title(f'Most common path {title_suffix}: ' + path_str)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'tr_path_most_common.png'), dpi=200)
    plt.close()

def build_hop_events(df: pd.DataFrame, src_ip: str, dst_ip: str, dst_port: int):
    sel = df[(df['l4'] == 'UDP') & (df['dst_ip'] == dst_ip) & (df['src_ip'] == src_ip) & (df['dst_port'] == dst_port) & df['ip_id'].notna() & df['node'].notna()]
    if sel.empty:
        return []
    events = []  # list of dicts with time, from_node, to_node, rate, length
    # For each IP id, take receive events in time order and create hop transitions
    for ip_id, grp in sel[sel['event'] == 'r'].sort_values('time').groupby('ip_id'):
        rows = grp[['time','node','rate','length']].sort_values('time').to_dict('records')
        for i in range(len(rows)-1):
            nxt = rows[i+1]
            cur = rows[i]
            events.append({
                'time': float(nxt['time']),
                'from_node': int(cur['node']),
                'to_node': int(nxt['node']),
                'rate': str(nxt['rate']),
                'length': int(nxt['length']) if pd.notna(nxt['length']) else None,
            })
    events.sort(key=lambda x: x['time'])
    return events

def animate_paths_time(df: pd.DataFrame, out_dir: str, src_ip: str = '10.0.0.1', dst_ip: str = '10.0.0.10', dst_port: int = 5000):
    events = build_hop_events(df, src_ip, dst_ip, dst_port)
    if not events:
        return
    # Determine node ids present
    node_ids = sorted({n for e in events for n in (e['from_node'], e['to_node'])})
    num_nodes = len(node_ids)
    node_to_idx = {n:i for i,n in enumerate(node_ids)}
    # Positions: linear layout
    xs = list(range(num_nodes))
    ys = [0]*num_nodes

    fig, ax = plt.subplots(figsize=(max(6, num_nodes), 2.5))
    ax.set_ylim(-0.5, 0.5)
    ax.set_xlim(-0.5, num_nodes-0.5)
    ax.set_yticks([])
    ax.set_xticks(xs)
    ax.set_xticklabels([str(n) for n in node_ids])
    ax.set_xlabel('Node ID')
    title = ax.set_title(f'Time-ordered path animation UDP {dst_port} {src_ip}→{dst_ip}')

    # Draw nodes
    ax.scatter(xs, ys, s=100, zorder=3, color='#1f77b4')

    # Prepare arrow objects for edges (keep a trail of last K events)
    K = 20
    arrows = []
    for _ in range(K):
        arr = FancyArrowPatch((0,0),(0,0), arrowstyle='->', mutation_scale=12, color='red', alpha=0.0, lw=2)
        ax.add_patch(arr)
        arrows.append(arr)

    # Text overlay for current hop info
    info_text = ax.text(0.01, 0.95, '', transform=ax.transAxes, ha='left', va='top', fontsize=9)

    times = [e['time'] for e in events]
    t_min, t_max = min(times), max(times)
    # Frame times as quantized to, e.g., 50 fps across the simulation span
    fps = 25
    duration_s = max(1.0, t_max - t_min)
    total_frames = int(duration_s * fps)
    if total_frames > 2000:
        total_frames = 2000  # cap to keep files reasonable
    frame_times = np.linspace(t_min, t_max, num=total_frames)

    # For each frame, pick events that occurred in the last trail_window seconds
    trail_window = 0.5  # seconds

    def init():
        for arr in arrows:
            arr.set_alpha(0.0)
        info_text.set_text('')
        return arrows + [info_text]

    def update(frame_idx):
        t = frame_times[frame_idx]
        # select recent events
        recent = [e for e in events if t - trail_window <= e['time'] <= t]
        # take up to K most recent
        recent = recent[-K:]
        # draw them with fading alpha by age
        for i, arr in enumerate(arrows):
            if i < len(recent):
                ev = recent[-(i+1)]
                xa, xb = node_to_idx[ev['from_node']], node_to_idx[ev['to_node']]
                arr.set_positions((xa,0), (xb,0))
                age = t - ev['time']
                alpha = max(0.0, 1.0 - age / trail_window)
                arr.set_alpha(alpha)
            else:
                arr.set_alpha(0.0)
        # Current event info text (most recent if exists)
        if recent:
            ev = recent[-1]
            info_text.set_text(f"t={ev['time']:.3f}s  {ev['from_node']} → {ev['to_node']}  rate={ev['rate']}  len={ev['length'] or 0}B")
        else:
            info_text.set_text('')
        return arrows + [info_text]

    ani = animation.FuncAnimation(fig, update, frames=len(frame_times), init_func=init, blit=True, interval=1000/fps)
    out_mp4 = os.path.join(out_dir, 'tr_path_animation.mp4')
    out_gif = os.path.join(out_dir, 'tr_path_animation.gif')
    try:
        ani.save(out_mp4, writer='ffmpeg', dpi=150)
    except Exception:
        try:
            ani.save(out_gif, writer='pillow', dpi=150)
        except Exception:
            pass
    plt.close(fig)

def main():
    os.makedirs(TR_DIR, exist_ok=True)
    df = load_all_traces()
    if df.empty:
        print("No .tr files found.")
        return
    # Save raw parsed CSV
    df.to_csv(os.path.join(TR_DIR, 'traces_parsed.csv'), index=False)
    # Plots
    plot_rate_distribution(df, TR_DIR)
    plot_mac_throughput(df, TR_DIR)
    plot_udp_port_throughput(df, TR_DIR)
    # Summaries
    summary, by_rate, udp_ports = compute_summary(df)
    summary.to_csv(os.path.join(TR_DIR, 'tr_summary.csv'), index=False)
    by_rate.to_csv(os.path.join(TR_DIR, 'tr_by_rate.csv'), index=False)
    udp_ports.to_csv(os.path.join(TR_DIR, 'tr_udp_ports.csv'), index=False)
    # Reconstruct paths for UDP 5000 (node 0 -> node 9)
    paths = reconstruct_paths(df, src_ip='10.0.0.1', dst_ip='10.0.0.10', dst_port=5000)
    if not paths.empty:
        paths.to_csv(os.path.join(TR_DIR, 'tr_paths_udp5000.csv'), index=False)
        plot_most_common_path(paths, TR_DIR, title_suffix='UDP dst 5000')
    # Reconstruct paths for TCP flows (6000: 0->9, 6001: 9->0)
    tcp_a = reconstruct_tcp_paths(df, src_ip='10.0.0.1', dst_ip='10.0.0.10', dst_port=6000)
    if not tcp_a.empty:
        tcp_a.to_csv(os.path.join(TR_DIR, 'tr_paths_tcp6000.csv'), index=False)
        plot_most_common_path(tcp_a, TR_DIR, title_suffix='TCP dst 6000')
    tcp_b = reconstruct_tcp_paths(df, src_ip='10.0.0.10', dst_ip='10.0.0.1', dst_port=6001)
    if not tcp_b.empty:
        tcp_b.to_csv(os.path.join(TR_DIR, 'tr_paths_tcp6001.csv'), index=False)
        plot_most_common_path(tcp_b, TR_DIR, title_suffix='TCP dst 6001')
    print("Saved: traces_parsed.csv, tr_summary.csv, tr_by_rate.csv, tr_udp_ports.csv and PNG plots in Lte_outputs")

if __name__ == '__main__':
    main()
