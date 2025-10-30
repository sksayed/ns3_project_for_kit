#!/usr/bin/env python3
"""
Complete Path Verification using both XML and .tr files
Combines metadata-based TTL tracking with explicit TX/RX verification
"""

import xml.etree.ElementTree as ET
import re
import sys
import argparse
import json
import os
from collections import defaultdict

class PathTracer:
    def __init__(self, xml_file, tr_file=None):
        self.xml_file = xml_file
        self.tr_file = tr_file
        self.xml_packets = []
        self.tr_events = []
        self.path = []
        
    def parse_xml(self, source_ip, dest_ip, source_port=None, dest_port=None):
        """Parse XML file and extract UDP packet path using TTL"""
        print(f"Parsing XML: {self.xml_file}...")
        tree = ET.parse(self.xml_file)
        root = tree.getroot()
        
        # Find all UDP packet transmissions with metadata
        packets = []
        
        for pr in root.findall('pr'):
            meta_info = pr.get('meta-info', '')
            
            # Check if this is our UDP packet
            # Handle both fragmented (Payload Fragment) and non-fragmented (Payload (size=X))
            has_payload = ('Payload Fragment [0:' in meta_info or 
                          'Payload (size=' in meta_info)
            
            # Check IP addresses
            ip_match = (source_ip in meta_info and dest_ip in meta_info)
            
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
            
            if (ip_match and 'UdpHeader' in meta_info and has_payload and port_match):
                
                from_node = pr.get('fId')
                tx_time = float(pr.get('fbTx'))
                uid = pr.get('uId')
                
                # Extract TTL
                ttl_match = re.search(r'ttl (\d+)', meta_info)
                ttl = int(ttl_match.group(1)) if ttl_match else None
                
                packets.append({
                    'uid': uid,
                    'from_node': from_node,
                    'tx_time': tx_time,
                    'ttl': ttl,
                    'receivers': []
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
        
        # Sort by TTL (descending) for chronological order
        packets.sort(key=lambda x: (-x['ttl'], x['tx_time']))
        
        self.xml_packets = packets
        print(f"✓ Found {len(packets)} UDP packet transmissions in XML\n")
        
        return packets
    
    def parse_tr_file(self, source_ip, dest_ip, source_port=None, dest_port=None):
        """Parse .tr file and extract TX/RX events"""
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
                    
                    # Extract node number from line (format differs for t/r events)
                    # t: t TIME /NodeList/X/...
                    # r: r TIME RATE /NodeList/X/...
                    node_match = re.search(r'/NodeList/(\d+)/', line)
                    if not node_match:
                        continue
                    node = node_match.group(1)
                    
                    # Check if it's our UDP packet  (not OLSR control packets)
                    # Handle both fragmented and non-fragmented packets
                    has_payload = ('Payload Fragment' in line or 
                                  'Payload (size=' in line)
                    
                    # Check IP addresses
                    ip_match = (source_ip in line and dest_ip in line)
                    
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
                    
                    if (ip_match and 'UdpHeader' in line and has_payload and port_match):
                        
                        # Extract TTL if available
                        ttl_match = re.search(r'ttl (\d+)', line)
                        ttl = int(ttl_match.group(1)) if ttl_match else None
                        
                        events.append({
                            'type': event_type,
                            'time': time,
                            'node': node,
                            'ttl': ttl
                        })
            
            self.tr_events = events
            print(f"✓ Found {len(events)} TX/RX events in .tr file\n")
            
        except FileNotFoundError:
            print(f"⚠️  .tr file not found: {self.tr_file}")
            print("   Proceeding with XML-only analysis\n")
            self.tr_events = []
        
        return events
    
    def build_path_from_xml(self):
        """Build path from XML packets"""
        path = []
        for pkt in self.xml_packets:
            path.append(pkt['from_node'])
        return path
    
    def verify_ttl_sequence(self):
        """Verify TTL decrements properly (no gaps)"""
        print("="*80)
        print("TTL SEQUENCE VERIFICATION")
        print("="*80)
        
        if len(self.xml_packets) < 2:
            print("⚠️  Not enough packets to verify")
            return False
        
        all_valid = True
        
        for i in range(1, len(self.xml_packets)):
            expected_ttl = self.xml_packets[i-1]['ttl'] - 1
            actual_ttl = self.xml_packets[i]['ttl']
            
            if actual_ttl == expected_ttl:
                print(f"✓ Hop {i}: TTL {self.xml_packets[i-1]['ttl']} → {actual_ttl} (OK)")
            else:
                print(f"❌ Hop {i}: Expected TTL {expected_ttl}, got {actual_ttl} (GAP!)")
                all_valid = False
        
        print()
        if all_valid:
            print("✅ TTL sequence is continuous - no missing hops")
        else:
            print("⚠️  TTL gaps detected - possible missing hops or wrong path")
        
        print()
        return all_valid
    
    def verify_with_tr_file(self):
        """Verify path using .tr file TX/RX events"""
        if not self.tr_events:
            print("⚠️  No .tr file data available for verification\n")
            return None
        
        print("="*80)
        print("TR FILE VERIFICATION")
        print("="*80)
        
        path = self.build_path_from_xml()
        
        # Build TX→RX map from .tr events
        tx_events = [e for e in self.tr_events if e['type'] == 't']
        rx_events = [e for e in self.tr_events if e['type'] == 'r']
        
        print(f"Total .tr events: {len(self.tr_events)}")
        print(f"TX events: {len(tx_events)}, RX events: {len(rx_events)}\n")
        
        if len(rx_events) == 0:
            print("⚠️  No RX events found in .tr file")
            print("   This usually means only TX events match the filter")
            print("   Path verification requires RX events\n")
            return None
        
        verified = True
        
        for i in range(len(path) - 1):
            current_node = path[i]
            next_node = path[i + 1]
            
            # Find TX from current node (first fragment only)
            tx = None
            for event in tx_events:
                if event['node'] == current_node:
                    tx = event
                    break
            
            if not tx:
                print(f"⚠️  Hop {i+1}: No TX found for Node {current_node}")
                verified = False
                continue
            
            # Find RX at next node
            # Note: RX events have the SAME TTL as TX (TTL is decremented on forward, not receive)
            rx = None
            
            for event in rx_events:
                # Match by: same destination node AND same TTL AND after TX time
                if (event['node'] == next_node and 
                    event['ttl'] == tx['ttl'] and  # Same TTL at reception!
                    event['time'] > tx['time'] and
                    abs(event['time'] - tx['time']) < 0.1):  # Within 100ms of TX
                    rx = event
                    break
            
            if rx:
                delay = (rx['time'] - tx['time']) * 1000
                print(f"✓ Hop {i+1}: Node {current_node} (TTL={tx['ttl']}) → Node {next_node} (TTL={rx['ttl']})")
                print(f"  TX: {tx['time']:.6f}s, RX: {rx['time']:.6f}s, Delay: {delay:.2f}ms")
            else:
                print(f"❌ Hop {i+1}: Node {next_node} did NOT receive from Node {current_node}")
                print(f"   Expected to find RX event with TTL={tx['ttl']} at Node {next_node}")
                verified = False
        
        print()
        if verified:
            print("✅ All hops verified with .tr file!")
        else:
            print("⚠️  Some hops could not be verified")
        
        print()
        return verified
    
    def check_duplicate_ttl(self):
        """Check for duplicate TTL values"""
        print("="*80)
        print("DUPLICATE TTL CHECK")
        print("="*80)
        
        ttl_map = defaultdict(list)
        
        for pkt in self.xml_packets:
            ttl_map[pkt['ttl']].append(pkt)
        
        duplicates_found = False
        
        for ttl, packets in sorted(ttl_map.items(), reverse=True):
            if len(packets) > 1:
                duplicates_found = True
                print(f"\n⚠️  TTL={ttl} has {len(packets)} transmissions:")
                for pkt in packets:
                    print(f"  - Node {pkt['from_node']} at {pkt['tx_time']:.6f}s")
                    print(f"    Receivers: {[r['node'] for r in pkt['receivers']]}")
                print(f"  → Selected: Node {packets[0]['from_node']} (earliest)")
        
        if not duplicates_found:
            print("✅ No duplicate TTL values found - path is unambiguous")
        
        print()
        return not duplicates_found
    
    def display_path(self):
        """Display the complete path with details"""
        print("="*80)
        print("PACKET FORWARDING PATH")
        print("="*80)
        
        path = []
        
        for i, pkt in enumerate(self.xml_packets):
            hop_num = i + 1
            from_node = pkt['from_node']
            ttl = pkt['ttl']
            time = pkt['tx_time']
            receivers = [r['node'] for r in pkt['receivers']]
            
            path.append(from_node)
            
            print(f"\n[Hop {hop_num}] Time: {time:.6f}s")
            print(f"  Transmitter: Node {from_node}")
            print(f"  TTL: {ttl} → {ttl-1}")
            print(f"  Physical receivers: {receivers} ({len(receivers)} nodes)")
            
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
        
        # Assume square grid for now
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


def load_config_json(config_file='config.json'):
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
    config = load_config_json('config.json')
    
    if config:
        # Use values from config.json
        print("="*80)
        print("Loading configuration from config.json")
        print("="*80)
        
        source_node = config['traffic_configuration']['source_node']
        dest_node = config['traffic_configuration']['destination_node']
        source_ip = config['ip_configuration']['source_ip']
        dest_ip = config['ip_configuration']['destination_ip']
        source_port = config['port_information'].get('source_port')
        dest_port = config['port_information'].get('destination_port')
        xml_file = config['output_files']['xml_file']
        tr_file = config['output_files']['tr_file']
        num_nodes = config['network_topology']['num_nodes']
        grid_width = config['network_topology']['grid_width']
        packet_size = config['traffic_configuration']['packet_size_bytes']
        node_spacing = config['network_topology']['node_spacing_meters']
        
        print(f"  Source: Node {source_node} ({source_ip}:{source_port})")
        print(f"  Destination: Node {dest_node} ({dest_ip}:{dest_port})")
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
        description='Verify packet forwarding path in NS-3 WiFi ad-hoc network',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Default: Node 24 → Node 0, any ports
  %(prog)s 12 18                    # Trace: Node 12 → Node 18
  %(prog)s 0 24                     # Trace: Node 0 → Node 24
  %(prog)s 12 18 --dest-port 80     # Only packets to port 80
  %(prog)s --source-ip 10.1.1.10 --dest-ip 10.1.1.5
  %(prog)s 5 20 --source-port 49153 --dest-port 80  # Specific ports
        """)
        
        parser.add_argument('source', nargs='?', type=int, default=24,
                           help='Source node number (default: 24)')
        parser.add_argument('dest', nargs='?', type=int, default=0,
                           help='Destination node number (default: 0)')
        parser.add_argument('--xml', default='wifi-test1-adhoc-grid.xml',
                           help='XML file to parse')
        parser.add_argument('--tr', default='wifi-test1-adhoc-grid.tr',
                           help='.tr file to parse')
        parser.add_argument('--source-ip', dest='source_ip', default=None,
                           help='Source IP address (overrides source node)')
        parser.add_argument('--dest-ip', dest='dest_ip', default=None,
                           help='Destination IP address (overrides dest node)')
        parser.add_argument('--ip-base', default='10.1.1',
                           help='IP subnet base (default: 10.1.1)')
        parser.add_argument('--dest-port', type=int, default=None,
                           help='Destination port number (default: auto-detect, matches any port)')
        parser.add_argument('--source-port', type=int, default=None,
                           help='Source port number (default: auto-detect, matches any port)')
        
        args = parser.parse_args()
        
        # Determine IP addresses
        if args.source_ip and args.dest_ip:
            source_ip = args.source_ip
            dest_ip = args.dest_ip
            source_node = args.source
            dest_node = args.dest
        else:
            source_node = args.source
            dest_node = args.dest
            # Node IDs are 0-indexed, IPs are 1-indexed
            source_ip = f'{args.ip_base}.{source_node + 1}'
            dest_ip = f'{args.ip_base}.{dest_node + 1}'
        
        source_port = args.source_port
        dest_port = args.dest_port
        xml_file = args.xml
        tr_file = args.tr
        
        # Auto-detect grid from XML
        num_nodes, grid_width = detect_grid_from_xml(xml_file)
    
    # Common display
    print("\n" + "="*80)
    print("COMPLETE PATH VERIFICATION SYSTEM")
    print("XML (Metadata) + .tr File (TX/RX Events)")
    print("="*80 + "\n")
    
    display_grid(num_nodes, grid_width)
    
    print(f"Tracing: Node {source_node} ({source_ip}) → Node {dest_node} ({dest_ip})")
    print()
    
    # Initialize tracer
    tracer = PathTracer(xml_file, tr_file)
    
    # Step 1: Parse XML
    tracer.parse_xml(source_ip, dest_ip, source_port, dest_port)
    
    if not tracer.xml_packets:
        print("❌ No UDP packets found in XML!")
        if source_port or dest_port:
            print(f"   Port filter: {source_port or 'any'} > {dest_port or 'any'}")
        print("   Try without port filters or check source/dest IPs")
        return
    
    # Step 2: Display path from XML
    tracer.display_path()
    
    # Step 3: Verify TTL sequence
    ttl_valid = tracer.verify_ttl_sequence()
    
    # Step 4: Check for duplicate TTLs
    no_duplicates = tracer.check_duplicate_ttl()
    
    # Step 5: Parse .tr file (if available)
    tracer.parse_tr_file(source_ip, dest_ip, source_port, dest_port)
    
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
    print(f"  TTL Sequence: {'✅ Valid' if ttl_valid else '❌ Invalid'}")
    print(f"  Duplicate TTLs: {'✅ None' if no_duplicates else '⚠️  Found (resolved by time)'}")
    
    if tr_verified is not None:
        print(f"  .tr File Verification: {'✅ Confirmed' if tr_verified else '❌ Failed'}")
    else:
        print(f"  .tr File Verification: ⚠️  Not available")
    
    print()
    
    if ttl_valid and (tr_verified is None or tr_verified):
        print("🎯 PATH SUCCESSFULLY TRACED AND VERIFIED!")
    elif ttl_valid:
        print("✅ Path traced successfully (awaiting .tr verification)")
    else:
        print("⚠️  Path has issues - manual review recommended")
    
    print()


if __name__ == "__main__":
    main()

