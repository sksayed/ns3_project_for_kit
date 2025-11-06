#!/usr/bin/env python3
"""
Re-run path verification on existing simulation results
to extract hop sequences for the reports
"""

import subprocess
import os
import json
import shutil
from pathlib import Path

BASE_RESULTS_DIR = "wifi_test_research/results"
NS3_DIR = "/home/sayed/ns-3-dev"

def extract_hop_paths(output_text):
    """Extract hop sequence from path verification output"""
    hop_data = {
        'hop_sequence': None,
        'hop_count': 0,
        'tcp_path': None,
        'udp_path': None
    }
    
    lines = output_text.split('\n')
    for line in lines:
        if 'Complete Route:' in line:
            path_str = line.split('Complete Route:')[1].strip()
            hop_data['hop_sequence'] = path_str
            hop_data['hop_count'] = len(path_str.split('→')) - 1 if '→' in path_str else 0
        elif '✓ Path extracted:' in line:
            path_str = line.split('✓ Path extracted:')[1].strip()
            if not hop_data['hop_sequence']:
                hop_data['hop_sequence'] = path_str
                hop_data['hop_count'] = len(path_str.split('→')) - 1 if '→' in path_str else 0
    
    return hop_data

def rerun_path_verification():
    """Re-run path verification on all existing results"""
    print("="*80)
    print("RE-RUNNING PATH VERIFICATION")
    print("="*80)
    
    count = 0
    success = 0
    
    # Walk through all result directories
    for sta_dir in sorted(Path(BASE_RESULTS_DIR).glob("sta_*")):
        for pkt_dir in sorted(sta_dir.glob("pktsize_*")):
            for config_dir in sorted(pkt_dir.glob("config_*")):
                count += 1
                
                xml_file = config_dir / "wifi-test-2-adhoc-grid.xml"
                sta_tr_file = config_dir / "wifi-test-2-sta.tr"
                config_file = config_dir / "config_test_2.json"
                
                if not xml_file.exists():
                    print(f"Skipping {config_dir} - no XML file")
                    continue
                
                print(f"\nProcessing: {config_dir}")
                
                # Copy config to expected location
                if config_file.exists():
                    shutil.copy(str(config_file), 'wifi_test_research/config_test_2.json')
                
                try:
                    result = subprocess.run([
                        'python3',
                        'wifi_test_research/test_2_verify_mesh_path.py',
                        '--xml', str(xml_file),
                        '--sta-tr', str(sta_tr_file)
                    ],
                    cwd=NS3_DIR,
                    capture_output=True,
                    text=True,
                    timeout=60
                    )
                    
                    # Extract hop path
                    hop_data = extract_hop_paths(result.stdout)
                    
                    # Save to path_analysis.json
                    path_file = config_dir / "path_analysis.json"
                    with open(path_file, 'w') as f:
                        json.dump(hop_data, f, indent=2)
                    
                    if hop_data['hop_sequence']:
                        print(f"  ✓ Path: {hop_data['hop_sequence']}")
                        success += 1
                    else:
                        print(f"  ⚠ No path found")
                    
                except subprocess.TimeoutExpired:
                    print(f"  ⚠ Timeout")
                except Exception as e:
                    print(f"  ⚠ Error: {e}")
    
    print(f"\n{'='*80}")
    print(f"Processed: {count} directories")
    print(f"Paths extracted: {success}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    rerun_path_verification()


