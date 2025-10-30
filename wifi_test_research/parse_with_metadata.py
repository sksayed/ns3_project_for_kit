#!/usr/bin/env python3
"""
Parse NetAnim XML with metadata enabled
Traces UDP packet path using TTL and metadata
"""

import xml.etree.ElementTree as ET
import re

def parse_udp_packet_path(xml_file, source_ip, dest_ip):
    """
    Trace UDP packet path using metadata
    
    Logic: Follow TTL (Time To Live) values
    - Each hop decrements TTL by 1
    - This gives us the chronological forwarding sequence
    """
    print(f"Parsing {xml_file}...")
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Map IP to Node ID
    ip_to_node = {}
    for link in root.findall('nonp2plinkproperties'):
        node_id = link.get('id')
        ip_addr = link.get('ipAddress')
        if ip_addr and '~' in ip_addr:
            ip = ip_addr.split('~')[0]
            if ip != '127.0.0.1':
                ip_to_node[ip] = node_id
    
    print(f"✓ Loaded {len(ip_to_node)} IP mappings")
    
    # Find all UDP packet transmissions
    udp_packets = []
    
    for pr in root.findall('pr'):
        meta_info = pr.get('meta-info', '')
        
        # Check if this is a UDP packet from source to destination
        if (source_ip in meta_info and dest_ip in meta_info and 
            'UdpHeader' in meta_info and 'Payload Fragment [0:' in meta_info):
            
            # Extract information
            from_node = pr.get('fId')
            tx_time = float(pr.get('fbTx'))
            
            # Extract TTL
            ttl_match = re.search(r'ttl (\d+)', meta_info)
            ttl = int(ttl_match.group(1)) if ttl_match else None
            
            # Extract fragment info
            frag_match = re.search(r'Payload Fragment \[(\d+):(\d+)\]', meta_info)
            frag_start = int(frag_match.group(1)) if frag_match else None
            
            udp_packets.append({
                'from_node': from_node,
                'tx_time': tx_time,
                'ttl': ttl,
                'frag_start': frag_start,
                'meta': meta_info
            })
    
    # Sort by TTL (descending) to get chronological forwarding order
    udp_packets.sort(key=lambda x: (-x['ttl'], x['tx_time']))
    
    print(f"✓ Found {len(udp_packets)} UDP packet transmissions\n")
    
    return udp_packets, ip_to_node

def show_grid():
    """Display network topology"""
    print("NETWORK TOPOLOGY (5x5 Grid):")
    print("="*80)
    print("""
      0 -   1 -   2 -   3 -   4
      |     |     |     |     |
      5 -   6 -   7 -   8 -   9
      |     |     |     |     |
     10 -  11 -  12 -  13 -  14
      |     |     |     |     |
     15 -  16 -  17 -  18 -  19
      |     |     |     |     |
     20 -  21 -  22 -  23 -  24
    """)

def main():
    xml_file = 'wifi-test1-adhoc-grid.xml'
    source_ip = '10.1.1.25'  # Node 24
    dest_ip = '10.1.1.1'     # Node 0
    
    print("\n" + "="*80)
    print("UDP PACKET PATH TRACER (Using Metadata)")
    print("="*80 + "\n")
    
    #show_grid()
    
    # Parse the file
    packets, ip_to_node = parse_udp_packet_path(xml_file, source_ip, dest_ip)
    
    if not packets:
        print("No UDP packets found!")
        return
    
    # Extract the path
    print("="*80)
    print(f"FORWARDING PATH: {source_ip} → {dest_ip}")
    print("="*80)
    print("(Following TTL decrement - each hop reduces TTL by 1)\n")
    
    path = []
    
    for i, pkt in enumerate(packets):
        hop_num = i + 1
        from_node = pkt['from_node']
        ttl = pkt['ttl']
        time = pkt['tx_time']
        
        path.append(from_node)
        
        print(f"[Hop {hop_num}] Time: {time:.6f}s")
        print(f"  Node {from_node} forwards packet")
        print(f"  TTL: {ttl} → {ttl-1}")
        
        if i > 0:
            prev_time = packets[i-1]['tx_time']
            delay = time - prev_time
            print(f"  Hop delay: {delay:.6f}s ({delay*1000:.2f}ms)")
        
        print()
    
    # Summary
    print("="*80)
    print("COMPLETE PATH (Chronological Order)")
    print("="*80)
    print(f"\nRoute: {' → '.join(path)}")
    print(f"Total Hops: {len(path) - 1}")
    
    if packets:
        total_time = packets[-1]['tx_time'] - packets[0]['tx_time']
        print(f"\nEnd-to-End Delay:")
        print(f"  Start: {packets[0]['tx_time']:.6f}s (Node {packets[0]['from_node']})")
        print(f"  End:   {packets[-1]['tx_time']:.6f}s (Node {packets[-1]['from_node']})")
        print(f"  Total: {total_time:.6f}s ({total_time*1000:.2f}ms)")
        print(f"  Average per hop: {total_time/(len(path)-1)*1000:.2f}ms")
    
    print()

if __name__ == "__main__":
    main()

