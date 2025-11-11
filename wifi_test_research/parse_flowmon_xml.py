#!/usr/bin/env python3
"""
FlowMonitor XML parser for Wi-Fi mesh simulations.

Reads the FlowMonitor XML output produced by `wifi-test-2-adhoc-grid.cc`,
aggregates per-STA metrics, and prints a concise report. Optionally writes
the results to a CSV file for further analysis.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple
import xml.etree.ElementTree as ET


DEFAULT_FLOWMON_PATH = Path("wifi_test_research/wifi-test-2-adhoc-grid-flowmon.xml")


def _extract_numeric(value: str | None) -> float:
    """Convert FlowMonitor time/metric strings to floats (seconds/units)."""
    if not value:
        return 0.0

    stripped = []
    for ch in value:
        # Keep digits, decimal markers, exponents, and sign
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


def _aggregate_sta_metrics(
    flows: Dict[int, dict],
    classifier: Dict[int, dict],
    sta_prefix: str = "192.168.1.",
) -> Dict[str, dict]:
    """Aggregate statistics for traffic sourced by STA nodes."""
    sta_metrics: Dict[str, dict] = {}

    for flow_id, flow_info in flows.items():
        metadata = classifier.get(flow_id)
        if not metadata:
            continue

        source_ip = metadata.get("sourceAddress", "")
        if not source_ip.startswith(sta_prefix):
            continue

        metrics = sta_metrics.setdefault(
            source_ip,
            {
                "txPackets": 0,
                "rxPackets": 0,
                "txBytes": 0,
                "rxBytes": 0,
                "lostPackets": 0,
                "delaySum": 0.0,
                "jitterSum": 0.0,
                "protocols": set(),
                "flows": [],
                "firstTx": None,
                "lastRx": None,
            },
        )

        metrics["txPackets"] += flow_info["txPackets"]
        metrics["rxPackets"] += flow_info["rxPackets"]
        metrics["txBytes"] += flow_info["txBytes"]
        metrics["rxBytes"] += flow_info["rxBytes"]
        metrics["lostPackets"] += flow_info["lostPackets"]
        metrics["delaySum"] += flow_info["delaySum"]
        metrics["jitterSum"] += flow_info["jitterSum"]
        metrics["flows"].append(flow_id)

        proto = metadata.get("protocol")
        if proto == "6":
            metrics["protocols"].add("TCP")
        elif proto == "17":
            metrics["protocols"].add("UDP")
        elif proto:
            metrics["protocols"].add(proto)

        first_tx = flow_info["timeFirstTxPacket"]
        last_rx = flow_info["timeLastRxPacket"]
        if metrics["firstTx"] is None or (0 < first_tx < metrics["firstTx"]):
            metrics["firstTx"] = first_tx
        if metrics["lastRx"] is None or last_rx > metrics["lastRx"]:
            metrics["lastRx"] = last_rx

    return sta_metrics


def _format_rows(sta_metrics: Dict[str, dict], sim_time: float | None) -> Iterable[dict]:
    """Compute derived metrics for presentation."""
    sta_ips = sorted(sta_metrics.keys(), key=lambda ip: tuple(int(octet) for octet in ip.split(".")))

    for sta_ip in sta_ips:
        metrics = sta_metrics[sta_ip]
        tx_packets = metrics["txPackets"]
        rx_packets = metrics["rxPackets"]
        delay_sum = metrics["delaySum"]
        first_tx = metrics["firstTx"] or 0.0
        last_rx = metrics["lastRx"] or first_tx

        duration = max(last_rx - first_tx, 0.0)
        if duration <= 0.0 and sim_time:
            duration = sim_time

        throughput_mbps = 0.0
        if duration > 0:
            throughput_mbps = metrics["rxBytes"] * 8.0 / duration / 1e6

        row = {
            "sta_ip": sta_ip,
            "protocol": "/".join(sorted(metrics["protocols"])) or "N/A",
            "tx_packets": tx_packets,
            "rx_packets": rx_packets,
            "lost_packets": metrics["lostPackets"],
            "pdr_percent": (rx_packets / tx_packets * 100.0) if tx_packets > 0 else 0.0,
            "avg_delay_ms": (delay_sum / rx_packets * 1000.0) if rx_packets > 0 else 0.0,
            "throughput_mbps": throughput_mbps,
        }
        yield row


def _print_report(rows: Iterable[dict]) -> None:
    """Print a human-readable report to stdout."""
    rows = list(rows)
    if not rows:
        print("No STA flows found in FlowMonitor XML.")
        return

    header = (
        f"{'STA IP':<16}"
        f"{'Protocol':<12}"
        f"{'PDR (%)':>10}"
        f"{'Avg Delay (ms)':>16}"
        f"{'Throughput (Mbps)':>20}"
        f"{'TX Pkts':>12}"
        f"{'RX Pkts':>12}"
        f"{'Lost Pkts':>12}"
    )
    print(header)
    print("-" * len(header))

    total_pdr = 0.0
    total_delay = 0.0
    total_throughput = 0.0
    counted = 0

    for row in rows:
        print(
            f"{row['sta_ip']:<16}"
            f"{row['protocol']:<12}"
            f"{row['pdr_percent']:>10.2f}"
            f"{row['avg_delay_ms']:>16.2f}"
            f"{row['throughput_mbps']:>20.4f}"
            f"{row['tx_packets']:>12}"
            f"{row['rx_packets']:>12}"
            f"{row['lost_packets']:>12}"
        )
        if row["tx_packets"] > 0:
            total_pdr += row["pdr_percent"]
            total_delay += row["avg_delay_ms"]
            total_throughput += row["throughput_mbps"]
            counted += 1

    print("-" * len(header))
    if counted > 0:
        print(
            f"{'AVERAGE':<16}"
            f"{'':<12}"
            f"{(total_pdr / counted):>10.2f}"
            f"{(total_delay / counted):>16.2f}"
            f"{(total_throughput / counted):>20.4f}"
            f"{'':>12}"
            f"{'':>12}"
            f"{'':>12}"
        )
    print()


def _write_csv(rows: Iterable[dict], csv_path: Path) -> None:
    rows = list(rows)
    if not rows:
        print(f"No data to write to {csv_path}")
        return

    fieldnames = [
        "sta_ip",
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


def _write_markdown(rows: Iterable[dict], md_path: Path) -> None:
    rows = list(rows)
    if not rows:
        print(f"No data to write to {md_path}")
        return

    header = [
        "STA IP",
        "Protocol",
        "PDR (%)",
        "Avg Delay (ms)",
        "Throughput (Mbps)",
        "TX Packets",
        "RX Packets",
        "Lost Packets",
    ]
    with md_path.open("w") as md_file:
        md_file.write("# FlowMonitor STA Metrics\n\n")
        md_file.write("| " + " | ".join(header) + " |\n")
        md_file.write("|" + "|".join([" --- " for _ in header]) + "|\n")
        for row in rows:
            md_file.write(
                "| "
                + " | ".join(
                    [
                        row["sta_ip"],
                        row["protocol"],
                        f"{row['pdr_percent']:.2f}",
                        f"{row['avg_delay_ms']:.2f}",
                        f"{row['throughput_mbps']:.4f}",
                        str(row["tx_packets"]),
                        str(row["rx_packets"]),
                        str(row["lost_packets"]),
                    ]
                )
                + " |\n"
            )
    print(f"Wrote Markdown report to {md_path}")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "xml",
        nargs="?",
        default=DEFAULT_FLOWMON_PATH,
        type=Path,
        help="Path to FlowMonitor XML file (default: %(default)s)",
    )
    parser.add_argument(
        "--sim-time",
        type=float,
        default=None,
        help="Simulation time in seconds (used as fallback for throughput calculation)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Optional path to write metrics as CSV",
    )
    parser.add_argument(
        "--md",
        type=Path,
        help="Optional path to write metrics as Markdown",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    xml_path = args.xml
    if not xml_path.exists():
        print(f"Error: FlowMonitor XML not found: {xml_path}", file=sys.stderr)
        return 1

    flows, classifier = _parse_flowmon(xml_path)
    sta_metrics = _aggregate_sta_metrics(flows, classifier)
    rows = list(_format_rows(sta_metrics, args.sim_time))

    _print_report(rows)

    if args.csv:
        _write_csv(rows, args.csv)
    if args.md:
        _write_markdown(rows, args.md)

    return 0


if __name__ == "__main__":
    sys.exit(main())

