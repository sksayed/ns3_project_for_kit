#!/usr/bin/env python3
"""
Complete Mesh Path Verification using both XML and .tr files
Handles TCP/UDP over 802.11s mesh with full hop-by-hop verification
"""

import xml.etree.ElementTree as ET
import re
import sys
import argparse
import json
import os
from collections import defaultdict

class MeshPathTracer:
    def __init__(self, xml_file, tr_file=None):
        self.xml_file = xml_file
        self.tr_file = tr_file
        self.xml_packets = []
        self.tr_events = []
        self.path = []
        self.retransmissions = {}  # Track retransmissions per TTL
        
    def parse_xml(self, source_ip, dest_ip, protocol="both", source_port=None, dest_port=None):
        """Parse XML file and extract mesh packet path using MeshHeader TTL"""
        print(f"Parsing XML: {self.xml_file}...")
        
        # Read and fix XML by removing invalid control characters
        with open(self.xml_file, 'rb') as f:
            xml_bytes = f.read()
        
        # Remove non-printable control characters (except newline, tab, carriage return)
        # NS-3 NetAnim bug writes \x1f (Unit Separator) in TTL fields
        xml_clean = bytes([b for b in xml_bytes if b >= 32 or b in (9, 10, 13)])
        xml_content = xml_clean.decode('utf-8', errors='ignore')
        
        # Also replace any remaining empty TTL values
        xml_content = xml_content.replace('TTL=,', 'TTL=0,')
        xml_content = xml_content.replace('TTL= ,', 'TTL=0,')
        
        # Parse the fixed content
        root = ET.fromstring(xml_content)
        
        # Find all mesh data packet transmissions with metadata
        packets = []
        
        for pr in root.findall('pr'):
            meta_info = pr.get('meta-info', '')
            
            # Must be a mesh data frame (QOSDATA with MeshHeader)
            if 'QOSDATA' not in meta_info or 'dot11s::MeshHeader' not in meta_info:
                continue
            
            # Check if this is our packet based on protocol
            has_tcp = 'TcpHeader' in meta_info
            has_udp = 'UdpHeader' in meta_info
            
            # Protocol filtering
            if protocol == "tcp" and not has_tcp:
                continue
            elif protocol == "udp" and not has_udp:
                continue
            elif protocol == "both" and not (has_tcp or has_udp):
                continue
            
            # Check IP addresses
            ip_match = (source_ip in meta_info and dest_ip in meta_info)
            if not ip_match:
                continue
            
            # Check ports (optional)
            port_match = True
            if source_port is not None or dest_port is not None:
                port_pattern = ''
                if source_port and dest_port:
                    port_pattern = f'{source_port} > {dest_port}'
                elif dest_port:
                    port_pattern = f'> {dest_port}'
                elif source_port:
                    port_pattern = f'{source_port} >'
                port_match = port_pattern in meta_info
            
            if not port_match:
                continue
            
            from_node = pr.get('fId')
            tx_time = float(pr.get('fbTx'))
            uid = pr.get('uId')
            
            # Extract Mesh TTL (primary indicator of hop position)
            mesh_ttl_match = re.search(r'dot11s::MeshHeader.*?ttl\s*=?\s*(\d+)', meta_info)
            mesh_ttl = int(mesh_ttl_match.group(1)) if mesh_ttl_match else None
            
            # Skip packets with invalid/missing TTL (0 means we replaced empty TTL)
            if mesh_ttl is None or mesh_ttl == 0:
                continue
            
            # Extract Retry flag from WifiMacHeader
            retry_match = re.search(r'Retry\s*=\s*(\d+)', meta_info)
            is_retry = (retry_match and retry_match.group(1) == '1')
            
            # Extract sequence number
            seq_match = re.search(r'SeqNumber\s*=\s*(\d+)', meta_info)
            seq_num = int(seq_match.group(1)) if seq_match else None
            
            # Extract IP TTL (for additional verification)
            ip_ttl_match = re.search(r'Ipv4Header.*?ttl\s+(\d+)', meta_info)
            ip_ttl = int(ip_ttl_match.group(1)) if ip_ttl_match else None
            
            # Determine protocol
            pkt_protocol = "TCP" if has_tcp else "UDP" if has_udp else "Unknown"
            
            packets.append({
                'uid': uid,
                'from_node': from_node,
                'tx_time': tx_time,
                'mesh_ttl': mesh_ttl,
                'ip_ttl': ip_ttl,
                'protocol': pkt_protocol,
                'is_retry': is_retry,
                'seq_num': seq_num,
                'receivers': [],
                'meta': meta_info
            })
        
        # Get receiver information for each packet
        for wpr in root.findall('wpr'):
            uid = wpr.get('uId')
            to_node = wpr.get('tId')
            rx_time = float(wpr.get('fbRx'))
            
            # Find corresponding packet and add receiver
            for pkt in packets:
                if pkt['uid'] == uid:
                    pkt['receivers'].append({
                        'node': to_node,
                        'rx_time': rx_time
                    })
                    break
        
        # Sort by Mesh TTL (descending) then by time
        packets.sort(key=lambda x: (-x['mesh_ttl'] if x['mesh_ttl'] else 0, x['tx_time']))
        
        # Count retransmissions and duplicates per TTL
        ttl_stats = defaultdict(lambda: {'total': 0, 'retries': 0, 'unique_nodes': set()})
        
        for pkt in packets:
            ttl = pkt['mesh_ttl']
            ttl_stats[ttl]['total'] += 1
            ttl_stats[ttl]['unique_nodes'].add(pkt['from_node'])
            if pkt['is_retry']:
                ttl_stats[ttl]['retries'] += 1
        
        # Filter to track only ONE packet's journey (earliest NON-RETRY packet at each TTL)
        # This gives us the first packet's hop-by-hop path
        ttl_seen = {}
        filtered_packets = []
        
        for pkt in packets:
            ttl = pkt['mesh_ttl']
            # Take the first non-retry packet, or first retry if no non-retry exists
            if ttl not in ttl_seen:
                ttl_seen[ttl] = pkt
                filtered_packets.append(pkt)
        
        # Store retransmission statistics
        self.retransmissions = {}
        for ttl, stats in ttl_stats.items():
            if stats['retries'] > 0 or stats['total'] > 1:
                self.retransmissions[ttl] = {
                    'total': stats['total'],
                    'retries': stats['retries'],
                    'duplicates': stats['total'] - stats['retries'],
                    'unique_nodes': len(stats['unique_nodes'])
                }
        
        self.xml_packets = filtered_packets
        print(f"✓ Found {len(packets)} total mesh transmissions")
        print(f"✓ Filtered to {len(filtered_packets)} unique hops (first packet's path)")
        
        if self.retransmissions:
            total_retrans = sum(s['retries'] for s in self.retransmissions.values())
            total_dupes = sum(s['duplicates'] for s in self.retransmissions.values())
            print(f"⚠️  Detected {total_retrans} retransmissions")
            if total_dupes > 0:
                print(f"⚠️  Detected {total_dupes} duplicate transmissions (different packets, same TTL)")
        else:
            print(f"✅ No retransmissions detected")
        print()
        
        return filtered_packets
    
    def parse_tr_file(self, source_ip, dest_ip, protocol="both", source_port=None, dest_port=None):
        """Parse .tr file and extract TX/RX events for mesh frames"""
        if not self.tr_file:
            return []
        
        print(f"Parsing .tr file: {self.tr_file}...")
        
        events = []
        
        try:
            with open(self.tr_file, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 10:
                        continue
                    
                    event_type = parts[0]  # 't', 'r', or 'd'
                    time = float(parts[1])
                    
                    # Extract node number from line
                    node_match = re.search(r'/NodeList/(\d+)/', line)
                    if not node_match:
                        continue
                    node = node_match.group(1)
                    
                    # Must have mesh header
                    if 'dot11s::MeshHeader' not in line:
                        continue
                    
                    # Must be QOSDATA (not management or control)
                    if 'QOSDATA' not in line:
                        continue
                    
                    # Check protocol
                    has_tcp = 'TcpHeader' in line
                    has_udp = 'UdpHeader' in line
                    
                    if protocol == "tcp" and not has_tcp:
                        continue
                    elif protocol == "udp" and not has_udp:
                        continue
                    elif protocol == "both" and not (has_tcp or has_udp):
                        continue
                    
                    # Check IP addresses
                    ip_match = (source_ip in line and dest_ip in line)
                    if not ip_match:
                        continue
                    
                    # Check ports (optional)
                    port_match = True
                    if source_port is not None or dest_port is not None:
                        port_pattern = ''
                        if source_port and dest_port:
                            port_pattern = f'{source_port} > {dest_port}'
                        elif dest_port:
                            port_pattern = f'> {dest_port}'
                        elif source_port:
                            port_pattern = f'{source_port} >'
                        port_match = port_pattern in line
                    
                    if not port_match:
                        continue
                    
                    # Extract Mesh TTL
                    mesh_ttl_match = re.search(r'dot11s::MeshHeader.*?ttl\s*=?\s*(\d+)', line)
                    mesh_ttl = int(mesh_ttl_match.group(1)) if mesh_ttl_match else None
                    
                    # Extract IP TTL
                    ip_ttl_match = re.search(r'Ipv4Header.*?ttl\s+(\d+)', line)
                    ip_ttl = int(ip_ttl_match.group(1)) if ip_ttl_match else None
                    
                    events.append({
                        'type': event_type,
                        'time': time,
                        'node': node,
                        'mesh_ttl': mesh_ttl,
                        'ip_ttl': ip_ttl
                    })
            
            self.tr_events = events
            print(f"✓ Found {len(events)} TX/RX events in .tr file\n")
            
        except FileNotFoundError:
            print(f"⚠️  .tr file not found: {self.tr_file}")
            print("   Proceeding with XML-only analysis\n")
            self.tr_events = []
        
        return events
    
    def build_path_from_xml(self):
        """Build path from XML packets (unique forwarding nodes)"""
        path = []
        seen = set()
        for pkt in self.xml_packets:
            node_id = pkt['from_node']
            if node_id not in seen:
                path.append(node_id)
                seen.add(node_id)
        return path
    
    def verify_ttl_sequence(self):
        """Verify Mesh TTL decrements properly (no gaps)"""
        print("="*80)
        print("MESH TTL SEQUENCE VERIFICATION")
        print("="*80)
        
        if len(self.xml_packets) < 2:
            print("⚠️  Not enough packets to verify")
            return False
        
        all_valid = True
        
        for i in range(1, len(self.xml_packets)):
            expected_ttl = self.xml_packets[i-1]['mesh_ttl'] - 1
            actual_ttl = self.xml_packets[i]['mesh_ttl']
            
            if actual_ttl == expected_ttl:
                print(f"✓ Hop {i}: Mesh TTL {self.xml_packets[i-1]['mesh_ttl']} → {actual_ttl} (OK)")
            else:
                print(f"❌ Hop {i}: Expected Mesh TTL {expected_ttl}, got {actual_ttl} (GAP!)")
                all_valid = False
        
        print()
        if all_valid:
            print("✅ Mesh TTL sequence is continuous - no missing hops")
        else:
            print("⚠️  Mesh TTL gaps detected - possible missing hops or alternate paths")
        
        print()
        return all_valid
    
    def verify_with_tr_file(self):
        """Verify path using .tr file TX/RX events"""
        if not self.tr_events:
            print("⚠️  No .tr file data available for verification\n")
            return None
        
        print("="*80)
        print("TR FILE VERIFICATION (Hop-by-Hop)")
        print("="*80)
        
        path = self.build_path_from_xml()
        
        # Build TX→RX map from .tr events
        tx_events = [e for e in self.tr_events if e['type'] == 't']
        rx_events = [e for e in self.tr_events if e['type'] == 'r']
        
        print(f"Total .tr events: {len(self.tr_events)}")
        print(f"TX events: {len(tx_events)}, RX events: {len(rx_events)}\n")
        
        if len(rx_events) == 0:
            print("⚠️  No RX events found in .tr file")
            print("   Path verification requires RX events\n")
            return None
        
        verified = True
        
        for i in range(len(path) - 1):
            current_node = path[i]
            next_node = path[i + 1]
            
            # Find TX from current node with matching mesh TTL
            tx = None
            expected_mesh_ttl = self.xml_packets[i]['mesh_ttl']
            
            for event in tx_events:
                if event['node'] == current_node and event['mesh_ttl'] == expected_mesh_ttl:
                    tx = event
                    break
            
            if not tx:
                print(f"⚠️  Hop {i+1}: No TX found for Node {current_node} (Mesh TTL={expected_mesh_ttl})")
                verified = False
                continue
            
            # Find RX at next node
            # Note: RX events have the SAME Mesh TTL as TX (TTL decrements on forward, not receive)
            rx = None
            
            for event in rx_events:
                # Match by: same destination node AND same Mesh TTL AND after TX time
                if (event['node'] == next_node and 
                    event['mesh_ttl'] == tx['mesh_ttl'] and  # Same Mesh TTL at reception!
                    event['time'] > tx['time'] and
                    abs(event['time'] - tx['time']) < 0.1):  # Within 100ms of TX
                    rx = event
                    break
            
            if rx:
                delay = (rx['time'] - tx['time']) * 1000
                print(f"✓ Hop {i+1}: Node {current_node} (Mesh TTL={tx['mesh_ttl']}) → Node {next_node} (Mesh TTL={rx['mesh_ttl']})")
                print(f"  TX: {tx['time']:.6f}s, RX: {rx['time']:.6f}s, Delay: {delay:.2f}ms")
            else:
                print(f"❌ Hop {i+1}: Node {next_node} did NOT receive from Node {current_node}")
                print(f"   Expected to find RX event with Mesh TTL={tx['mesh_ttl']} at Node {next_node}")
                verified = False
        
        print()
        if verified:
            print("✅ All hops verified with .tr file!")
        else:
            print("⚠️  Some hops could not be verified")
        
        print()
        return verified
    
    def check_duplicate_ttl(self):
        """Check for duplicate Mesh TTL values"""
        print("="*80)
        print("DUPLICATE MESH TTL CHECK")
        print("="*80)
        
        ttl_map = defaultdict(list)
        
        for pkt in self.xml_packets:
            ttl_map[pkt['mesh_ttl']].append(pkt)
        
        duplicates_found = False
        
        for ttl, packets in sorted(ttl_map.items(), reverse=True):
            if len(packets) > 1:
                duplicates_found = True
                print(f"\n⚠️  Mesh TTL={ttl} has {len(packets)} transmissions:")
                for pkt in packets:
                    print(f"  - Node {pkt['from_node']} at {pkt['tx_time']:.6f}s ({pkt['protocol']})")
                    print(f"    Receivers: {[r['node'] for r in pkt['receivers']]}")
                print(f"  → Selected: Node {packets[0]['from_node']} (earliest)")
        
        if not duplicates_found:
            print("✅ No duplicate Mesh TTL values found - path is unambiguous")
        
        print()
        return not duplicates_found
    
    def display_path(self):
        """Display the complete path with details"""
        print("="*80)
        print("MESH PACKET FORWARDING PATH")
        print("="*80)
        
        path = []
        
        for i, pkt in enumerate(self.xml_packets):
            hop_num = i + 1
            from_node = pkt['from_node']
            mesh_ttl = pkt['mesh_ttl']
            ip_ttl = pkt['ip_ttl']
            time = pkt['tx_time']
            protocol = pkt['protocol']
            receivers = [r['node'] for r in pkt['receivers']]
            
            path.append(from_node)
            
            print(f"\n[Hop {hop_num}] Time: {time:.6f}s")
            print(f"  Transmitter: Node {from_node}")
            print(f"  Protocol: {protocol}")
            print(f"  Mesh TTL: {mesh_ttl} → {mesh_ttl-1}")
            print(f"  IP TTL: {ip_ttl}")
            print(f"  Sequence: {pkt['seq_num']}")
            print(f"  Retry: {'Yes ⚠️' if pkt['is_retry'] else 'No'}")
            print(f"  Physical receivers: {receivers} ({len(receivers)} nodes)")
            
            # Show retransmission statistics for this TTL
            if mesh_ttl in self.retransmissions:
                stats = self.retransmissions[mesh_ttl]
                print(f"  ⚠️  TTL {mesh_ttl} stats: {stats['total']} transmissions ({stats['retries']} retries, {stats['unique_nodes']} unique nodes)")
            
            if i > 0:
                prev_time = self.xml_packets[i-1]['tx_time']
                delay = time - prev_time
                print(f"  Inter-hop delay: {delay*1000:.2f}ms")
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"\nComplete Route: {' → '.join(path)}")
        print(f"Total Hops: {len(path) - 1}")
        
        if self.xml_packets:
            total_time = self.xml_packets[-1]['tx_time'] - self.xml_packets[0]['tx_time']
            avg_delay = total_time / (len(path) - 1) if len(path) > 1 else 0
            
            print(f"\nTiming Statistics:")
            print(f"  Start time: {self.xml_packets[0]['tx_time']:.6f}s")
            print(f"  End time: {self.xml_packets[-1]['tx_time']:.6f}s")
            print(f"  Total delay: {total_time*1000:.2f}ms")
            print(f"  Average per hop: {avg_delay*1000:.2f}ms")
        
        # Retransmission summary
        if self.retransmissions:
            print(f"\n⚠️  Retransmission Summary:")
            total_retrans = 0
            total_dupes = 0
            for ttl in sorted(self.retransmissions.keys(), reverse=True):
                stats = self.retransmissions[ttl]
                total_retrans += stats['retries']
                total_dupes += stats['duplicates']
                if stats['retries'] > 0 or stats['unique_nodes'] > 1:
                    issues = []
                    if stats['retries'] > 0:
                        issues.append(f"{stats['retries']} retries")
                    if stats['unique_nodes'] > 1:
                        issues.append(f"{stats['unique_nodes']} different nodes")
                    print(f"  TTL {ttl}: {stats['total']} total ({', '.join(issues)})")
            print(f"  Total retransmissions: {total_retrans}")
            if total_dupes > 0:
                print(f"  Total duplicates (different packets): {total_dupes}")
        else:
            print(f"\n✅ No retransmissions or duplicates detected")
        
        print()
        self.path = path
        return path


def detect_grid_from_xml(xml_file):
    """Auto-detect network topology from XML file"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        nodes = root.findall('node')
        num_nodes = len(nodes)
        
        # Assume square grid for mesh APs
        grid_width = int(num_nodes ** 0.5)
        if grid_width * grid_width != num_nodes:
            grid_width = 5  # Default fallback
        
        return num_nodes, grid_width
    except:
        return 25, 5  # Default


def display_grid(num_nodes, grid_width):
    """Display network grid topology"""
    print("NETWORK TOPOLOGY:")
    print("="*80)
    
    for row in range(grid_width):
        line = "  "
        for col in range(grid_width):
            node_id = row * grid_width + col
            if node_id < num_nodes:
                line += f"{node_id:>3}"
                if col < grid_width - 1:
                    line += " - "
            else:
                line += "   "
        print(line)
        
        if row < grid_width - 1:
            # Print vertical connections
            line = "  "
            for col in range(grid_width):
                node_id = row * grid_width + col
                if node_id < num_nodes and node_id + grid_width < num_nodes:
                    line += "  |  "
                else:
                    line += "     "
                if col < grid_width - 1:
                    line += "   "
            print(line)
    print()


def load_config_json(config_file='wifi-test-reconstruction/config.json'):
    """Load configuration from JSON file written by simulation"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"⚠️  Error parsing {config_file}: {e}")
        return None


def main():
    # Try to load config.json first (written by simulation)
    config = load_config_json('wifi-test-reconstruction/config.json')
    
    if config:
        # Use values from config.json
        print("="*80)
        print("Loading configuration from wifi-test-reconstruction/config.json")
        print("="*80)
        
        source_ip = config['ip_configuration']['source_ip']
        dest_ip = config['ip_configuration']['destination_ip']
        tcp_port = config['port_information']['tcp_port']
        udp_port = config['port_information']['udp_port']
        xml_file = config['output_files']['xml_file']
        tr_file = config['output_files']['tr_file']
        num_nodes = config['network_topology']['num_nodes']
        grid_width = config['network_topology']['grid_width']
        packet_size = config['traffic_configuration']['packet_size_bytes']
        node_spacing = config['network_topology']['node_spacing_meters']
        traffic_type = config['traffic_configuration']['traffic_type']
        use_tcp = config['traffic_configuration']['use_tcp'] == "true"
        use_udp = config['traffic_configuration']['use_udp'] == "true"
        
        # Determine protocol to search for
        if use_tcp and use_udp:
            protocol = "both"
        elif use_tcp:
            protocol = "tcp"
        elif use_udp:
            protocol = "udp"
        else:
            protocol = "both"
        
        print(f"  Scenario: {config['traffic_configuration']['scenario']}")
        print(f"  Source: {source_ip}")
        print(f"  Destination: {dest_ip}")
        print(f"  Protocol: {protocol.upper()} (TCP port: {tcp_port}, UDP port: {udp_port})")
        print(f"  Packet Size: {packet_size} bytes")
        print(f"  Grid: {num_nodes} nodes ({grid_width}x{grid_width})")
        print(f"  Spacing: {node_spacing}m")
        print(f"  Files: {xml_file}, {tr_file}")
        print()
        
        use_config = True
    else:
        # Fallback to command-line arguments
        print("="*80)
        print("No config.json found - using command-line arguments")
        print("="*80 + "\n")
        
        parser = argparse.ArgumentParser(
            description='Verify mesh packet forwarding path in NS-3 802.11s mesh network',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s                                    # Default: uses config.json
  %(prog)s --xml mesh_backhaul_anim.xml      # Specify XML file
  %(prog)s --protocol tcp                     # Only TCP packets
  %(prog)s --protocol udp --dest-port 8100   # Only UDP packets to port 8100
        """)
        
        parser.add_argument('--xml', default='wifi_mesh_backhaul_outputs/mesh_backhaul_anim.xml',
                           help='XML file to parse')
        parser.add_argument('--tr', default='wifi_mesh_backhaul_outputs/mesh_backhaul.tr',
                           help='.tr file to parse')
        parser.add_argument('--source-ip', dest='source_ip', default='192.168.2.2',
                           help='Source IP address')
        parser.add_argument('--dest-ip', dest='dest_ip', default='200.1.1.2',
                           help='Destination IP address')
        parser.add_argument('--protocol', default='both', choices=['tcp', 'udp', 'both'],
                           help='Protocol to trace: tcp, udp, or both')
        parser.add_argument('--tcp-port', type=int, default=7100,
                           help='TCP port number')
        parser.add_argument('--udp-port', type=int, default=8100,
                           help='UDP port number')
        
        args = parser.parse_args()
        
        source_ip = args.source_ip
        dest_ip = args.dest_ip
        tcp_port = args.tcp_port
        udp_port = args.udp_port
        xml_file = args.xml
        tr_file = args.tr
        protocol = args.protocol
        
        # Auto-detect grid from XML
        num_nodes, grid_width = detect_grid_from_xml(xml_file)
    
    # Common display
    print("\n" + "="*80)
    print("MESH PATH VERIFICATION SYSTEM")
    print("XML (Metadata) + .tr File (TX/RX Events)")
    print("="*80 + "\n")
    
    display_grid(num_nodes, grid_width)
    
    print(f"Tracing: {source_ip} → {dest_ip}")
    print(f"Protocol: {protocol.upper()}")
    print()
    
    # Initialize tracer
    tracer = MeshPathTracer(xml_file, tr_file)
    
    # Determine which port to use based on protocol
    src_port = None
    dst_port = None
    if protocol == "tcp":
        dst_port = tcp_port
    elif protocol == "udp":
        dst_port = udp_port
    # For "both", we leave ports as None to match any
    
    # Step 1: Parse XML
    tracer.parse_xml(source_ip, dest_ip, protocol, src_port, dst_port)
    
    if not tracer.xml_packets:
        print("❌ No mesh packets found in XML!")
        print(f"   Protocol: {protocol}")
        print(f"   Source IP: {source_ip}")
        print(f"   Dest IP: {dest_ip}")
        if dst_port:
            print(f"   Dest Port: {dst_port}")
        print("   Make sure simulation ran long enough and NetAnim has metadata enabled")
        return
    
    # Step 2: Display path from XML
    tracer.display_path()
    
    # Step 3: Verify TTL sequence
    ttl_valid = tracer.verify_ttl_sequence()
    
    # Step 4: Check for duplicate TTLs
    no_duplicates = tracer.check_duplicate_ttl()
    
    # Step 5: Parse .tr file (if available)
    tracer.parse_tr_file(source_ip, dest_ip, protocol, src_port, dst_port)
    
    # Step 6: Verify with .tr file
    if tracer.tr_events:
        tr_verified = tracer.verify_with_tr_file()
    else:
        tr_verified = None
    
    # Final verdict
    print("="*80)
    print("FINAL VERDICT")
    print("="*80)
    
    print(f"\n✓ Path extracted: {' → '.join(tracer.path)}")
    print(f"\nVerification Results:")
    print(f"  Mesh TTL Sequence: {'✅ Valid' if ttl_valid else '❌ Invalid'}")
    print(f"  Duplicate Mesh TTLs: {'✅ None' if no_duplicates else '⚠️  Found (resolved by time)'}")
    
    if tr_verified is not None:
        print(f"  .tr File Verification: {'✅ Confirmed' if tr_verified else '❌ Failed'}")
    else:
        print(f"  .tr File Verification: ⚠️  Not available")
    
    print()
    
    if ttl_valid and (tr_verified is None or tr_verified):
        print("🎯 MESH PATH SUCCESSFULLY TRACED AND VERIFIED!")
    elif ttl_valid:
        print("✅ Path traced successfully (awaiting .tr verification)")
    else:
        print("⚠️  Path has issues - manual review recommended")
    
    print()


if __name__ == "__main__":
    main()

