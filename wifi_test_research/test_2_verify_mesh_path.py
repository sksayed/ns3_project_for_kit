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
import html
from collections import defaultdict

# Constants
CONFIG_FILE = 'config_test_2.json'
OUTPUT_DIR = 'wifi_test_research'
DEFAULT_XML = 'wifi-test-2-adhoc-grid.xml'
DEFAULT_TR = 'wifi-test-2-adhoc-grid.tr'

class MeshPathTracer:
    def __init__(self, xml_file, tr_file=None, sta_tr_file=None):
        self.xml_file = xml_file
        self.tr_file = tr_file
        self.sta_tr_file = sta_tr_file  # Separate .tr file for STA traffic
        self.xml_packets = []
        self.ap_sta_packets = []  # Non-mesh AP/STA traffic
        self.tr_events = []
        self.sta_tr_events = []  # STA trace events
        self.path = []
        self.retransmissions = {}  # Track retransmissions per TTL
        self.complete_path = []  # Combined AP/STA + Mesh path
    
    @staticmethod
    def mac_to_node_id(mac_address):
        """Convert MAC address to Node ID
        ns-3 format: 00:00:00:00:00:XX where XX = (Node_ID + 1) in hex
        """
        if not mac_address or mac_address == 'ff:ff:ff:ff:ff:ff':
            return None
        try:
            # Extract last byte (XX) from MAC address
            last_byte = mac_address.split(':')[-1]
            # Convert hex to decimal and subtract 1
            node_id = int(last_byte, 16) - 1
            return node_id
        except:
            return None
        
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
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            print(f"⚠️  XML Parse Error: {e}")
            print(f"   Trying file-based parsing...")
            try:
                tree = ET.parse(self.xml_file)
                root = tree.getroot()
            except ET.ParseError as e2:
                print(f"❌ Both parsing methods failed: {e2}")
                print(f"   XML file may be corrupted. Try regenerating the simulation output.")
                return []
        
        # Find all mesh data packet transmissions with metadata
        packets = []
        
        for pr in root.findall('pr'):
            meta_info = pr.get('meta-info', '')
            
            # Unescape HTML entities (e.g., &gt; &lt; &amp;)
            meta_info = html.unescape(meta_info)
            
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
            
            # Extract WiFi MAC addresses
            sa_match = re.search(r'SA=([0-9a-f:]+)', meta_info)
            da_match = re.search(r'DA=([0-9a-f:]+)', meta_info)
            ta_match = re.search(r'TA=([0-9a-f:]+)', meta_info)
            ra_match = re.search(r'RA=([0-9a-f:]+)', meta_info)
            
            sa = sa_match.group(1) if sa_match else None
            da = da_match.group(1) if da_match else None
            ta = ta_match.group(1) if ta_match else None
            ra = ra_match.group(1) if ra_match else None
            
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
                'sa': sa,
                'da': da,
                'ta': ta,
                'ra': ra,
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
        
        # Filter to track ONE packet's complete journey through the mesh
        # Strategy: Track using SA+DA pair (constant) + Mesh TTL decrement + time window
        filtered_packets = []
        
        if packets:
            # Start with the first packet (highest TTL, earliest time)
            first_pkt = packets[0]
            filtered_packets.append(first_pkt)
            
            current_ttl = first_pkt['mesh_ttl']
            current_time = first_pkt['tx_time']
            packet_sa = first_pkt['sa']  # Source Address - stays constant
            packet_da = first_pkt['da']  # Destination Address - stays constant
            
            # Follow this packet through subsequent hops
            first_pkt_time = first_pkt['tx_time']
            
            for next_ttl in range(current_ttl - 1, 0, -1):
                # Find the next hop: same SA+DA, TTL-1
                # Use cumulative time window (1 second from start) to handle both TCP and UDP
                # TCP: hops every ~2ms, UDP: hops every ~100ms
                candidates = [p for p in packets 
                             if p['mesh_ttl'] == next_ttl 
                             and p['sa'] == packet_sa
                             and p['da'] == packet_da
                             and (p['tx_time'] - first_pkt_time) < 1.0]  # 1 second cumulative window
                
                if candidates:
                    next_pkt = candidates[0]
                    filtered_packets.append(next_pkt)
                    current_time = next_pkt['tx_time']
                else:
                    # No matching packet found - path ends
                    break
        
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
        print(f"✓ Filtered to {len(filtered_packets)} unique hops (single packet journey)")
        
        # Validate tracking
        if len(filtered_packets) > 1:
            time_span = filtered_packets[-1]['tx_time'] - filtered_packets[0]['tx_time']
            sa_consistent = all(p['sa'] == filtered_packets[0]['sa'] for p in filtered_packets if p['sa'])
            da_consistent = all(p['da'] == filtered_packets[0]['da'] for p in filtered_packets if p['da'])
            print(f"✓ Packet tracking: Time span={time_span*1000:.2f}ms")
            print(f"✓ MAC Address validation: SA consistent={sa_consistent}, DA consistent={da_consistent}")
            if filtered_packets[0]['sa'] and filtered_packets[0]['da']:
                sa_node = self.mac_to_node_id(filtered_packets[0]['sa'])
                da_node = self.mac_to_node_id(filtered_packets[0]['da'])
                print(f"  SA={filtered_packets[0]['sa']} (Node {sa_node}), DA={filtered_packets[0]['da']} (Node {da_node})")
        
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
    
    def parse_ap_sta_traffic(self, source_ip, dest_ip, protocol="both", source_port=None, dest_port=None):
        """Parse XML file for non-mesh AP/STA traffic (802.11ac without MeshHeader)"""
        print(f"Parsing AP/STA traffic (non-mesh): {self.xml_file}...")
        
        # Use file-based parsing for large XMLs
        try:
            tree = ET.parse(self.xml_file)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"⚠️  XML Parse Error: {e}")
            print(f"   Trying alternative parsing method...")
            # Try cleaning the XML
            with open(self.xml_file, 'rb') as f:
                xml_bytes = f.read()
            
            xml_clean = bytes([b for b in xml_bytes if b >= 32 or b in (9, 10, 13)])
            xml_content = xml_clean.decode('utf-8', errors='ignore')
            xml_content = xml_content.replace('TTL=,', 'TTL=0,')
            xml_content = xml_content.replace('TTL= ,', 'TTL=0,')
            
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e2:
                print(f"❌ Both parsing methods failed: {e2}")
                self.ap_sta_packets = []
                return []
        
        # Find AP/STA packets (802.11 frames WITHOUT MeshHeader)
        packets = []
        
        for pr in root.findall('pr'):
            meta_info = pr.get('meta-info', '')
            meta_info = html.unescape(meta_info)
            
            # Must be QOSDATA but WITHOUT MeshHeader (this is AP/STA traffic)
            if 'QOSDATA' not in meta_info:
                continue
            if 'dot11s::MeshHeader' in meta_info:
                continue  # Skip mesh frames
            
            # Check protocol
            has_tcp = 'TcpHeader' in meta_info
            has_udp = 'UdpHeader' in meta_info
            
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
            
            # Extract WiFi MAC addresses
            sa_match = re.search(r'SA=([0-9a-f:]+)', meta_info)
            da_match = re.search(r'DA=([0-9a-f:]+)', meta_info)
            ta_match = re.search(r'TA=([0-9a-f:]+)', meta_info)
            ra_match = re.search(r'RA=([0-9a-f:]+)', meta_info)
            
            sa = sa_match.group(1) if sa_match else None
            da = da_match.group(1) if da_match else None
            ta = ta_match.group(1) if ta_match else None
            ra = ra_match.group(1) if ra_match else None
            
            # Extract IP TTL
            ip_ttl_match = re.search(r'Ipv4Header.*?ttl\s+(\d+)', meta_info)
            ip_ttl = int(ip_ttl_match.group(1)) if ip_ttl_match else None
            
            # Determine protocol
            pkt_protocol = "TCP" if has_tcp else "UDP" if has_udp else "Unknown"
            
            # Determine if this is STA->AP or AP->STA based on ToDS/FromDS
            tods_match = re.search(r'ToDS=(\d)', meta_info)
            fromds_match = re.search(r'FromDS=(\d)', meta_info)
            tods = int(tods_match.group(1)) if tods_match else 0
            fromds = int(fromds_match.group(1)) if fromds_match else 0
            
            if tods == 1 and fromds == 0:
                direction = "STA→AP"
            elif tods == 0 and fromds == 1:
                direction = "AP→STA"
            else:
                direction = "Unknown"
            
            packets.append({
                'uid': uid,
                'from_node': from_node,
                'tx_time': tx_time,
                'ip_ttl': ip_ttl,
                'protocol': pkt_protocol,
                'sa': sa,
                'da': da,
                'ta': ta,
                'ra': ra,
                'direction': direction,
                'meta': meta_info
            })
        
        # Sort by time
        packets.sort(key=lambda x: x['tx_time'])
        
        # Take first packet as representative
        if packets:
            self.ap_sta_packets = [packets[0]]
            print(f"✓ Found {len(packets)} AP/STA transmissions (showing first packet)")
            print(f"  Direction: {packets[0]['direction']}")
            if packets[0]['sa']:
                sa_node = self.mac_to_node_id(packets[0]['sa'])
                print(f"  SA: {packets[0]['sa']} (Node {sa_node})")
            if packets[0]['da']:
                da_node = self.mac_to_node_id(packets[0]['da'])
                print(f"  DA: {packets[0]['da']} (Node {da_node})")
        else:
            print(f"✓ No AP/STA traffic found")
            self.ap_sta_packets = []
        
        print()
        return self.ap_sta_packets
    
    def parse_tr_file(self, source_ip, dest_ip, protocol="both", source_port=None, dest_port=None):
        """Parse .tr file and extract TX/RX events for mesh frames"""
        # Try sta_tr_file first if it exists, then fall back to tr_file
        tr_files = []
        if self.sta_tr_file:
            tr_files.append(('STA', self.sta_tr_file))
        if self.tr_file:
            tr_files.append(('Mesh', self.tr_file))
        
        if not tr_files:
            return []
        
        events = []
        
        for file_type, tr_file in tr_files:
            print(f"Parsing {file_type} .tr file: {tr_file}...")
            
            try:
                with open(tr_file, 'r') as f:
                    for line in f:
                        # Unescape HTML entities in trace file
                        line = html.unescape(line)
                        
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
                            'ip_ttl': ip_ttl,
                            'file_type': file_type
                        })
                
                print(f"✓ Found {len(events)} TX/RX events in {file_type} .tr file")
                
            except FileNotFoundError:
                print(f"⚠️  {file_type} .tr file not found: {tr_file}")
                print("   Skipping this trace file\n")
            except Exception as e:
                print(f"⚠️  Error parsing {file_type} .tr file: {e}")
        
        self.tr_events = events
        print(f"✓ Total TX/RX events from all .tr files: {len(events)}\n")
        
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
    
    def build_complete_path(self):
        """Build complete path combining AP/STA and Mesh segments"""
        complete_path = []
        
        # Determine AP node from mesh path (first mesh node is the AP)
        ap_node_id = None
        if self.xml_packets:
            ap_node_id = self.xml_packets[0]['from_node']
        
        if self.ap_sta_packets:
            # Add STA → AP segment
            pkt = self.ap_sta_packets[0]
            if pkt['direction'] == "STA→AP":
                # STA is the transmitter
                complete_path.append({
                    'type': 'AP/STA',
                    'description': 'STA (source)',
                    'node_id': None,  # STA doesn't have a mesh node ID
                    'ip': None,  # Will be extracted from the packet
                    'interface': '802.11ac'
                })
                # AP is the first mesh node
                complete_path.append({
                    'type': 'AP',
                    'description': f'Node {ap_node_id} AP' if ap_node_id is not None else 'AP Node',
                    'node_id': ap_node_id,
                    'interface': '802.11ac'
                })
        
        # Add mesh path
        for pkt in self.xml_packets:
            node_id = pkt['from_node']
            complete_path.append({
                'type': 'Mesh',
                'description': f'Node {node_id} Mesh',
                'node_id': node_id,
                'interface': '802.11s'
            })
        
        # Add final destination from last mesh packet's RA
        if self.xml_packets and self.xml_packets[-1]['ra']:
            final_node = self.mac_to_node_id(self.xml_packets[-1]['ra'])
            if final_node is not None:
                # Check if this node isn't already in the path
                if not complete_path or complete_path[-1]['node_id'] != str(final_node):
                    complete_path.append({
                        'type': 'Gateway',
                        'description': f'Node {final_node} Gateway',
                        'node_id': str(final_node),
                        'interface': 'Ethernet'
                    })
        
        self.complete_path = complete_path
        return complete_path
    
    def display_complete_path(self):
        """Display the complete path including AP/STA and Mesh segments"""
        print("="*80)
        print("COMPLETE PATH: STA → INTERNET")
        print("="*80)
        print()
        
        if not self.complete_path:
            self.build_complete_path()
        
        if not self.complete_path:
            print("⚠️  No complete path available")
            return
        
        for i, hop in enumerate(self.complete_path):
            hop_num = i + 1
            print(f"[Hop {hop_num}] {hop['description']}")
            print(f"  Type: {hop['type']}")
            print(f"  Interface: {hop['interface']}")
            if i < len(self.complete_path) - 1:
                print(f"        ↓")
        
        print()
        print("="*80)
        print("PATH SUMMARY")
        print("="*80)
        
        # Count segments
        ap_sta_hops = sum(1 for h in self.complete_path if h['type'] in ['AP/STA', 'AP'])
        mesh_hops = sum(1 for h in self.complete_path if h['type'] == 'Mesh')
        
        path_desc = " → ".join([h['description'] for h in self.complete_path])
        print(f"\nComplete Route: {path_desc}")
        print(f"Total Hops: {len(self.complete_path) - 1}")
        print(f"  AP/STA Segment: {ap_sta_hops} hops")
        print(f"  Mesh Segment: {mesh_hops} hops")
        print()
    
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
            print(f"  WiFi MAC Sequence: {pkt['seq_num']}")
            if pkt['sa']:
                sa_node = self.mac_to_node_id(pkt['sa'])
                print(f"  SA (Source): {pkt['sa']} → Node {sa_node}")
            if pkt['da']:
                da_node = self.mac_to_node_id(pkt['da'])
                print(f"  DA (Dest): {pkt['da']} → Node {da_node}")
            if pkt['ta']:
                ta_node = self.mac_to_node_id(pkt['ta'])
                print(f"  TA (Transmitter): {pkt['ta']} → Node {ta_node}")
            if pkt['ra']:
                ra_node = self.mac_to_node_id(pkt['ra'])
                print(f"  RA (Receiver): {pkt['ra']} → Node {ra_node}")
            print(f"  Retry: {'Yes ⚠️' if pkt['is_retry'] else 'No'}")
            print(f"  Physical receivers: {receivers} ({len(receivers)} nodes)")
            
            # Show retransmission statistics for this TTL
            if mesh_ttl in self.retransmissions:
                stats = self.retransmissions[mesh_ttl]
                print(f"  ⚠️  TTL {mesh_ttl} stats: {stats['total']} transmissions ({stats['retries']} retries, {stats['unique_nodes']} unique nodes)")
            
            if i > 0:
                prev_time = self.xml_packets[i-1]['tx_time']
                prev_sa = self.xml_packets[i-1]['sa']
                prev_da = self.xml_packets[i-1]['da']
                delay = time - prev_time
                print(f"  Inter-hop delay: {delay*1000:.2f}ms")
                
                # Validation warnings
                if pkt['sa'] != prev_sa:
                    print(f"  ⚠️  WARNING: SA changed - Different packet!")
                if pkt['da'] != prev_da:
                    print(f"  ⚠️  WARNING: DA changed - Different packet!")
                if delay > 0.01:
                    print(f"  ⚠️  WARNING: Large time gap ({delay*1000:.2f}ms) - Different packets!")
        
        # Add final destination node to path
        if self.xml_packets and self.xml_packets[-1]['ra']:
            # Extract final destination from last hop's RA (Receiver Address)
            final_dest_node = self.mac_to_node_id(self.xml_packets[-1]['ra'])
            if final_dest_node is not None and str(final_dest_node) not in path:
                path.append(str(final_dest_node))
        
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


def load_config_json(config_file=CONFIG_FILE):
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
    # Parse command-line arguments first
    parser = argparse.ArgumentParser(
        description='Verify mesh packet forwarding path in NS-3 802.11s mesh network',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument('--xml', default=None, help='XML file to parse')
    parser.add_argument('--tr', default=None, help='.tr file to parse (mesh traffic)')
    parser.add_argument('--sta-tr', dest='sta_tr', default=None, help='.tr file for STA traffic')
    parser.add_argument('--source-ip', dest='source_ip', default=None, help='Source IP address')
    parser.add_argument('--dest-ip', dest='dest_ip', default=None, help='Destination IP address')
    parser.add_argument('--protocol', default=None, choices=['tcp', 'udp', 'both'], help='Protocol to trace')
    parser.add_argument('--tcp-port', type=int, default=None, help='TCP port number')
    parser.add_argument('--udp-port', type=int, default=None, help='UDP port number')
    
    args = parser.parse_args()
    
    # Try to load config file
    config_paths = [CONFIG_FILE, f'{OUTPUT_DIR}/{CONFIG_FILE}']
    config = None
    for config_path in config_paths:
        if os.path.exists(config_path):
            config = load_config_json(config_path)
            break
    
    if config:
        # Use values from config_test_2.json (but allow command-line override)
        print("="*80)
        print("Loading configuration from config_test_2.json")
        print("="*80)
        
        # Command-line args override config
        source_ip = args.source_ip if args.source_ip else config['ip_configuration']['source_ip']
        dest_ip = args.dest_ip if args.dest_ip else config['ip_configuration']['destination_ip']
        
        # Handle different config formats
        if 'tcp_port' in config['port_information']:
            tcp_port = args.tcp_port if args.tcp_port else config['port_information']['tcp_port']
            udp_port = args.udp_port if args.udp_port else config['port_information']['udp_port']
        else:
            tcp_port = args.tcp_port if args.tcp_port else None
            udp_port = args.udp_port if args.udp_port else config['port_information'].get('destination_port', 80)
        
        xml_file = args.xml if args.xml else config['output_files']['xml_file']
        tr_file = args.tr if args.tr else config['output_files']['tr_file']
        sta_tr_file = args.sta_tr if args.sta_tr else config['output_files'].get('sta_tr_file', None)
        num_nodes = config['network_topology']['num_nodes']
        grid_width = config['network_topology']['grid_width']
        packet_size = config['traffic_configuration']['packet_size_bytes']
        node_spacing = config['network_topology']['node_spacing_meters']
        
        # Determine protocol (command-line overrides config)
        if args.protocol:
            protocol = args.protocol
        else:
            # Default to 'both' since we have both UDP and TCP in simulation
            protocol = 'both'
        
        print(f"  Source: {source_ip}")
        print(f"  Destination: {dest_ip}")
        if tcp_port:
            print(f"  Protocol: {protocol.upper()} (TCP port: {tcp_port}, UDP port: {udp_port})")
        else:
            print(f"  Protocol: {protocol.upper()} (Port: {udp_port})")
        print(f"  Packet Size: {packet_size} bytes")
        print(f"  Grid: {num_nodes} nodes ({grid_width}x{grid_width})")
        print(f"  Spacing: {node_spacing}m")
        print(f"  Files: {xml_file}, {tr_file}")
        print()
        
        use_config = True
    else:
        # No config found - use command-line defaults
        print("="*80)
        print(f"No {CONFIG_FILE} found - using command-line arguments")
        print("="*80 + "\n")
        
        source_ip = args.source_ip if args.source_ip else '10.1.1.1'
        dest_ip = args.dest_ip if args.dest_ip else '10.1.1.9'
        tcp_port = args.tcp_port if args.tcp_port else 8080
        udp_port = args.udp_port if args.udp_port else 9
        xml_file = args.xml if args.xml else DEFAULT_XML
        tr_file = args.tr if args.tr else DEFAULT_TR
        sta_tr_file = args.sta_tr if args.sta_tr else None
        protocol = args.protocol if args.protocol else 'both'
        
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
    tracer = MeshPathTracer(xml_file, tr_file, sta_tr_file)
    
    # Determine which port to use based on protocol
    src_port = None
    dst_port = None
    if protocol == "tcp" and tcp_port:
        dst_port = tcp_port
    elif protocol == "udp":
        dst_port = udp_port
    # For "both", we leave ports as None to match any
    
    # Step 1: Check if source IP is from STA network (192.168.2.x)
    is_sta_source = source_ip.startswith('192.168.2.')
    
    # Track the IP to use for mesh/tr file lookups (may differ from source_ip for STA)
    mesh_lookup_ip = source_ip
    
    # Step 2: Parse AP/STA traffic if source is STA
    if is_sta_source:
        print(f"🔍 Detected STA source IP ({source_ip}), parsing AP/STA traffic...")
        tracer.parse_ap_sta_traffic(source_ip, dest_ip, protocol, src_port, dst_port)
        
        # If STA traffic found, translate source IP to mesh network IP for mesh parsing
        # STA traffic goes through AP which forwards to mesh as Node IP
        if tracer.ap_sta_packets:
            # Find which node is the AP (from RA in AP/STA packet)
            ap_pkt = tracer.ap_sta_packets[0]
            ap_node = tracer.mac_to_node_id(ap_pkt['ra']) if ap_pkt['ra'] else None
            if ap_node is not None:
                # Translate to mesh IP (e.g., Node 8 = 10.1.1.9)
                mesh_source_ip = f"10.1.1.{ap_node + 1}"
                mesh_lookup_ip = mesh_source_ip  # Update lookup IP for .tr file
                print(f"  → Translating to mesh source IP: {mesh_source_ip} (Node {ap_node})")
                # Now parse mesh traffic with the mesh IP
                tracer.parse_xml(mesh_source_ip, dest_ip, protocol, src_port, dst_port)
            else:
                # Fallback: try parsing with original source
                tracer.parse_xml(source_ip, dest_ip, protocol, src_port, dst_port)
        else:
            # No AP/STA traffic found, try mesh anyway
            tracer.parse_xml(source_ip, dest_ip, protocol, src_port, dst_port)
    else:
        # Step 3: Parse mesh traffic directly
        tracer.parse_xml(source_ip, dest_ip, protocol, src_port, dst_port)
    
    # Step 4: Display results
    if tracer.ap_sta_packets and tracer.xml_packets:
        # We have both AP/STA and mesh segments - display complete path
        print("\n" + "="*80)
        print("✅ COMPLETE PATH FOUND: STA → AP → MESH → GATEWAY → INTERNET")
        print("="*80 + "\n")
        
        tracer.display_complete_path()
        print()
        tracer.display_path()  # Also show detailed mesh path
    elif tracer.xml_packets:
        # Only mesh path available
        tracer.display_path()
    elif tracer.ap_sta_packets:
        # Only AP/STA found, no mesh path
        print("⚠️  Found AP/STA traffic but no mesh forwarding path")
        print("   This might indicate traffic didn't reach the mesh network")
        return
    else:
        print("❌ No packets found in XML!")
        print(f"   Protocol: {protocol}")
        print(f"   Source IP: {source_ip}")
        print(f"   Dest IP: {dest_ip}")
        if dst_port:
            print(f"   Dest Port: {dst_port}")
        print("   Make sure simulation ran long enough and NetAnim has metadata enabled")
        return
    
    # Step 3: Verify TTL sequence
    ttl_valid = tracer.verify_ttl_sequence()
    
    # Step 4: Check for duplicate TTLs
    no_duplicates = tracer.check_duplicate_ttl()
    
    # Step 5: Parse .tr file (if available) - use mesh_lookup_ip for STA traffic
    tracer.parse_tr_file(mesh_lookup_ip, dest_ip, protocol, src_port, dst_port)
    
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

