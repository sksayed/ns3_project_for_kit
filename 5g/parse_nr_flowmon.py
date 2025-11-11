#!/usr/bin/env python3
"""
FlowMonitor XML parser for the NR playfield scenario.

Reads the FlowMonitor XML produced by `nr_playfield_traces.cc`, aggregates per-UE
statistics, prints a concise summary, and optionally saves the results to CSV/Markdown.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple
import xml.etree.ElementTree as ET


DEFAULT_FLOWMON_PATH = Path("5g_outputs/flowmon-nr-playfield-rw.xml")


def _extract_numeric(value: str | None) -> float:
    """Convert FlowMonitor time/metric strings to floats."""
    if not value:
        return 0.0

    stripped = []
    for ch in value:
        if ch.isdigit() or ch in ".-+eE":
            stripped.append(ch)
    numeric = "".join(stripped)
    if not numeric:
        return 0.0

    try:
        return float(numeric)
    except ValueError:
        return 0.0


def _extract_seconds(value: str | None) -> float:
    """Convert FlowMonitor time strings with units to seconds."""
    if not value:
        return 0.0

    v = value.strip()
    scale = 1.0
    if v.endswith("ns"):
        scale = 1e-9
    elif v.endswith("ms"):
        scale = 1e-3
    elif v.endswith("us"):
        scale = 1e-6
    elif v.endswith("ps"):
        scale = 1e-12

    return _extract_numeric(v) * scale


def _parse_flowmon(xml_path: Path) -> Tuple[Dict[int, dict], Dict[int, dict]]:
    """Parse FlowMonitor XML and return flow statistics and classifier entries."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    flows: Dict[int, dict] = {}
    for flow_elem in root.findall(".//FlowStats/Flow"):
        flow_id = int(flow_elem.get("flowId"))
        flows[flow_id] = {
            "txBytes": int(flow_elem.get("txBytes", 0)),
            "rxBytes": int(flow_elem.get("rxBytes", 0)),
            "txPackets": int(flow_elem.get("txPackets", 0)),
            "rxPackets": int(flow_elem.get("rxPackets", 0)),
            "lostPackets": int(flow_elem.get("lostPackets", 0)),
            "delaySum": _extract_seconds(flow_elem.get("delaySum")),
            "jitterSum": _extract_seconds(flow_elem.get("jitterSum")),
            "timeFirstTxPacket": _extract_seconds(flow_elem.get("timeFirstTxPacket")),
            "timeLastRxPacket": _extract_seconds(flow_elem.get("timeLastRxPacket")),
        }

    classifier: Dict[int, dict] = {}
    ipv4_classifier = root.find(".//Ipv4FlowClassifier")
    if ipv4_classifier is not None:
        for flow_elem in ipv4_classifier.findall("Flow"):
            flow_id = int(flow_elem.get("flowId"))
            classifier[flow_id] = {
                "sourceAddress": flow_elem.get("sourceAddress"),
                "destinationAddress": flow_elem.get("destinationAddress"),
                "protocol": flow_elem.get("protocol"),
                "sourcePort": flow_elem.get("sourcePort"),
                "destinationPort": flow_elem.get("destinationPort"),
            }

    return flows, classifier


def _ue_index_from_ip(ip: str, prefix: str, offset: int) -> int | None:
    if not ip.startswith(prefix):
        return None
    try:
        last_octet = int(ip.split(".")[-1])
    except ValueError:
        return None
    ue_id = last_octet - offset
    return ue_id if ue_id >= 0 else None


def _aggregate_ue_metrics(
    flows: Dict[int, dict],
    classifier: Dict[int, dict],
    ue_prefix: str,
    ue_offset: int,
) -> Dict[int, dict]:
    """Aggregate per-UE statistics for uplink flows."""
    metrics: Dict[int, dict] = {}

    for flow_id, flow_info in flows.items():
        meta = classifier.get(flow_id)
        if not meta:
            continue

        ue_id = _ue_index_from_ip(meta.get("sourceAddress", ""), ue_prefix, ue_offset)
        if ue_id is None:
            continue

        entry = metrics.setdefault(
            ue_id,
            {
                "ip": meta["sourceAddress"],
                "protocols": set(),
                "txPackets": 0,
                "rxPackets": 0,
                "txBytes": 0,
                "rxBytes": 0,
                "lostPackets": 0,
                "delaySum": 0.0,
                "firstTx": None,
                "lastRx": None,
            },
        )

        entry["txPackets"] += flow_info["txPackets"]
        entry["rxPackets"] += flow_info["rxPackets"]
        entry["txBytes"] += flow_info["txBytes"]
        entry["rxBytes"] += flow_info["rxBytes"]
        entry["lostPackets"] += flow_info["lostPackets"]
        entry["delaySum"] += flow_info["delaySum"]

        proto = meta.get("protocol")
        if proto == "6":
            entry["protocols"].add("TCP")
        elif proto == "17":
            entry["protocols"].add("UDP")
        elif proto:
            entry["protocols"].add(proto)

        first_tx = flow_info["timeFirstTxPacket"]
        last_rx = flow_info["timeLastRxPacket"]
        if entry["firstTx"] is None or (0.0 < first_tx < entry["firstTx"]):
            entry["firstTx"] = first_tx
        if entry["lastRx"] is None or last_rx > entry["lastRx"]:
            entry["lastRx"] = last_rx

    return metrics


def _format_rows(
    metrics: Dict[int, dict],
    sim_time: float | None,
) -> Iterable[dict]:
    for ue_id in sorted(metrics.keys()):
        entry = metrics[ue_id]
        tx_packets = entry["txPackets"]
        rx_packets = entry["rxPackets"]
        duration = 0.0
        if entry["firstTx"] is not None and entry["lastRx"] is not None:
            duration = max(entry["lastRx"] - entry["firstTx"], 0.0)
        if duration <= 0.0 and sim_time:
            duration = sim_time

        throughput_mbps = (
            entry["rxBytes"] * 8.0 / duration / 1e6 if duration > 0 and entry["rxBytes"] > 0 else 0.0
        )

        yield {
            "ue_id": ue_id,
            "ip": entry["ip"],
            "protocol": "/".join(sorted(entry["protocols"])) or "N/A",
            "tx_packets": tx_packets,
            "rx_packets": rx_packets,
            "lost_packets": entry["lostPackets"],
            "pdr_percent": (rx_packets / tx_packets * 100.0) if tx_packets > 0 else 0.0,
            "avg_delay_ms": (entry["delaySum"] / rx_packets * 1000.0) if rx_packets > 0 else 0.0,
            "throughput_mbps": throughput_mbps,
        }


def _print_report(rows: Iterable[dict]) -> None:
    rows = list(rows)
    if not rows:
        print("No UE flows found in FlowMonitor XML.")
        return

    header = (
        f"{'UE':<4}"
        f"{'IP':<16}"
        f"{'Protocol':<12}"
        f"{'PDR (%)':>10}"
        f"{'Avg Delay (ms)':>16}"
        f"{'Throughput (Mbps)':>20}"
        f"{'TX Pkts':>10}"
        f"{'RX Pkts':>10}"
        f"{'Lost':>8}"
    )
    print(header)
    print("-" * len(header))

    total_pdr = 0.0
    total_delay = 0.0
    total_throughput = 0.0
    counted = 0

    for row in rows:
        print(
            f"{row['ue_id']:<4}"
            f"{row['ip']:<16}"
            f"{row['protocol']:<12}"
            f"{row['pdr_percent']:>10.2f}"
            f"{row['avg_delay_ms']:>16.2f}"
            f"{row['throughput_mbps']:>20.2f}"
            f"{row['tx_packets']:>10}"
            f"{row['rx_packets']:>10}"
            f"{row['lost_packets']:>8}"
        )
        if row["tx_packets"] > 0:
            total_pdr += row["pdr_percent"]
            total_delay += row["avg_delay_ms"]
            total_throughput += row["throughput_mbps"]
            counted += 1

    print("-" * len(header))
    if counted > 0:
        print(
            f"{'AVG':<4}"
            f"{'':<16}"
            f"{'':<12}"
            f"{(total_pdr / counted):>10.2f}"
            f"{(total_delay / counted):>16.2f}"
            f"{(total_throughput / counted):>20.2f}"
            f"{'':>10}"
            f"{'':>10}"
            f"{'':>8}"
        )
    print()


def _write_markdown(rows: Iterable[dict], md_path: Path) -> None:
    rows = list(rows)
    if not rows:
        print(f"No data to write to {md_path}")
        return

    with md_path.open("w") as md_file:
        md_file.write("# NR Per-UE FlowMonitor Metrics\n\n")
        md_file.write("| UE | IP | Protocol | PDR (%) | Avg Delay (ms) | Throughput (Mbps) | TX Packets | RX Packets | Lost Packets |\n")
        md_file.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for row in rows:
            md_file.write(
                f"| {row['ue_id']} | {row['ip']} | {row['protocol']} | "
                f"{row['pdr_percent']:.2f} | {row['avg_delay_ms']:.2f} | "
                f"{row['throughput_mbps']:.2f} | {row['tx_packets']} | "
                f"{row['rx_packets']} | {row['lost_packets']} |\n"
            )
    print(f"Wrote Markdown report to {md_path}")


def _write_csv(rows: Iterable[dict], csv_path: Path) -> None:
    rows = list(rows)
    if not rows:
        print(f"No data to write to {csv_path}")
        return

    fieldnames = [
        "ue_id",
        "ip",
        "protocol",
        "pdr_percent",
        "avg_delay_ms",
        "throughput_mbps",
        "tx_packets",
        "rx_packets",
        "lost_packets",
    ]
    with csv_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote CSV report to {csv_path}")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xml",
        type=Path,
        default=DEFAULT_FLOWMON_PATH,
        help="Path to FlowMonitor XML file (default: %(default)s)",
    )
    parser.add_argument(
        "--sim-time",
        type=float,
        default=None,
        help="Simulation time in seconds (used for throughput fallback)",
    )
    parser.add_argument(
        "--ue-prefix",
        default="7.0.0.",
        help="Prefix that identifies UE IPv4 addresses (default: %(default)s)",
    )
    parser.add_argument(
        "--ue-offset",
        type=int,
        default=2,
        help="Offset applied to the last octet to compute UE IDs (default: %(default)s)",
    )
    parser.add_argument(
        "--md",
        type=Path,
        help="Optional path to write Markdown output",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Optional path to write CSV output",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    xml_path = args.xml
    if not xml_path.exists():
        print(f"Error: FlowMonitor XML not found: {xml_path}", file=sys.stderr)
        return 1

    flows, classifier = _parse_flowmon(xml_path)
    metrics = _aggregate_ue_metrics(flows, classifier, args.ue_prefix, args.ue_offset)
    rows = list(_format_rows(metrics, args.sim_time))

    _print_report(rows)

    if args.md:
        _write_markdown(rows, args.md)
    if args.csv:
        _write_csv(rows, args.csv)

    return 0


if __name__ == "__main__":
    sys.exit(main())

