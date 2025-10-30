#!/usr/bin/env python3
import re
import sys
from collections import OrderedDict


def extract_attr(line, names):
    for name in names:
        m = re.search(r"\b" + re.escape(name) + r"=\"([^\"]+)\"", line)
        if m:
            return m.group(1)
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_anim_path.py <anim.xml> [src_ip] [dst_ip]")
        print("Defaults: src=192.168.2.2 dst=200.1.1.2 (Scenario 2)")
        return 2

    anim_xml = sys.argv[1]
    src_ip = sys.argv[2] if len(sys.argv) > 2 else "192.168.2.2"
    dst_ip = sys.argv[3] if len(sys.argv) > 3 else "200.1.1.2"

    # Heuristics for NetAnim packet lines and attributes
    packet_tags = ("<p ", "<packet ")
    # NetAnim often embeds IPs inside meta-info; also sometimes explicit attrs exist
    src_keys = ("srcIpv4", "srcIP", "saddr", "src")
    dst_keys = ("dstIpv4", "dstIP", "daddr", "dst")
    from_keys = ("fromId", "fromNodeId", "fId")
    to_keys = ("toId", "toNodeId", "tId")

    tx_sequence = []
    seen_pairs = set()

    try:
        with open(anim_xml, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not any(tag in line for tag in packet_tags):
                    continue

                # Prefer explicit attributes; fallback to meta-info search
                s = extract_attr(line, src_keys)
                d = extract_attr(line, dst_keys)
                if not s or not d:
                    meta = extract_attr(line, ("meta-info",)) or ""
                    if (src_ip in meta) and (dst_ip in meta):
                        s, d = src_ip, dst_ip
                    else:
                        continue

                if s != src_ip or d != dst_ip:
                    continue

                fr = extract_attr(line, from_keys)
                to = extract_attr(line, to_keys)

                # Record transmitter if present
                if fr:
                    pair = (fr, to or "")
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        tx_sequence.append(fr)
    except FileNotFoundError:
        print(f"Error: File not found: {anim_xml}")
        return 1

    if not tx_sequence:
        print("No matching packet transmissions found for the specified flow.")
        print("Hints: ensure anim.EnablePacketMetadata(true) and correct src/dst IPs.")
        return 0

    # Deduplicate while preserving order
    ordered = list(OrderedDict.fromkeys(tx_sequence))

    # Convert NodeList IDs to AP labels if possible (AP nodes are typically 0..N-1)
    # We just print node IDs; user can map IDs to AP indices if they match.
    path_str = " -> ".join(f"Node{n}" for n in ordered)

    print("Scenario: Sadia -> External Server")
    print(f"Source IP: {src_ip}  Destination IP: {dst_ip}")
    print("Transmitters observed (ordered, deduped):")
    print(path_str)
    if len(ordered) >= 2:
        print(f"Estimated hop count (Tx stages): {len(ordered) - 1}")
    else:
        print("Estimated hop count: 0")


if __name__ == "__main__":
    sys.exit(main())


