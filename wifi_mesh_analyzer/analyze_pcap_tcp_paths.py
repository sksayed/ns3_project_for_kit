#!/usr/bin/env python3
import os
import re
import subprocess
import csv
from glob import glob

OUT_DIR = "wifi_mesh_outputs"
PCAP_GLOB = os.path.join(OUT_DIR, "wifi_mesh_playfield_rw_pcap-*.pcap")

node_from_file_re = re.compile(r"rw_pcap-(?P<node>\d+)\.pcap$")

def tshark_available() -> bool:
    try:
        subprocess.run(["tshark", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except FileNotFoundError:
        return False

def run_tshark_fields(pcap_path: str, display_filter: str, fields: list[str]) -> list[list[str]]:
    cmd = [
        "tshark", "-r", pcap_path,
        "-Y", display_filter,
        "-T", "fields"
    ]
    for f in fields:
        cmd += ["-e", f]
    # ensure one record per line
    cmd += ["-E", "separator=,", "-E", "occurrence=f"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        return []
    lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
    rows = [ln.split(",") for ln in lines]
    return rows

def collect_tcp_events(dst_ip: str, dst_port: int) -> list[dict]:
    events: list[dict] = []
    for pcap in sorted(glob(PCAP_GLOB)):
        m = node_from_file_re.search(pcap)
        if not m:
            continue
        node = int(m.group("node"))
        # Only data packets for this flow (exclude SYN/ACK only by requiring tcp.len>0)
        df = f"ip && tcp && ip.dst=={dst_ip} && tcp.dstport=={dst_port} && tcp.len>0"
        rows = run_tshark_fields(
            pcap, df,
            fields=["frame.time_epoch", "ip.id", "ip.src", "ip.dst", "tcp.dstport", "tcp.len"]
        )
        for r in rows:
            try:
                t = float(r[0])
                ip_id = int(r[1])
                src = r[2]
                dst = r[3]
                dport = int(r[4])
                length = int(r[5]) if r[5] else 0
            except Exception:
                continue
            events.append({
                "time": t,
                "node": node,
                "ip_id": ip_id,
                "src_ip": src,
                "dst_ip": dst,
                "dst_port": dport,
                "length": length,
            })
    events.sort(key=lambda x: (x["ip_id"], x["time"]))
    return events

def reconstruct_paths_from_events(events: list[dict]) -> list[dict]:
    paths: list[dict] = []
    if not events:
        return paths
    # group by ip_id preserving order
    by_id: dict[int, list[dict]] = {}
    for ev in events:
        by_id.setdefault(ev["ip_id"], []).append(ev)
    for ip_id, lst in by_id.items():
        # sort by time across nodes
        lst.sort(key=lambda x: x["time"]) 
        hop_nodes: list[int] = []
        for ev in lst:
            if not hop_nodes or hop_nodes[-1] != ev["node"]:
                hop_nodes.append(ev["node"])
        if not lst:
            continue
        paths.append({
            "ip_id": ip_id,
            "src_ip": lst[0]["src_ip"],
            "dst_ip": lst[0]["dst_ip"],
            "dst_port": lst[0]["dst_port"],
            "hops": "->".join(map(str, hop_nodes)),
            "hop_count": len(hop_nodes),
        })
    paths.sort(key=lambda x: (x["hop_count"], x["ip_id"]))
    return paths

def write_csv(rows: list[dict], out_path: str) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

def main():
    if not tshark_available():
        print("tshark not found. Install with: sudo apt install tshark")
        return
    # 0 -> 9 TCP 6000
    ev_a = collect_tcp_events(dst_ip="10.0.0.10", dst_port=6000)
    paths_a = reconstruct_paths_from_events(ev_a)
    write_csv(paths_a, os.path.join(OUT_DIR, "tr_paths_tcp6000_pcap.csv"))

    # 9 -> 0 TCP 6001
    ev_b = collect_tcp_events(dst_ip="10.0.0.1", dst_port=6001)
    paths_b = reconstruct_paths_from_events(ev_b)
    write_csv(paths_b, os.path.join(OUT_DIR, "tr_paths_tcp6001_pcap.csv"))

    print("PCAP TCP paths done.")

if __name__ == "__main__":
    main()


