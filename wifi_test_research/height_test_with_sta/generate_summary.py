#!/usr/bin/env python3
"""
Summary Table Generator for Mesh AP Height Optimization
Generates markdown table with PDR, Throughput, Delay, and Rating
Sorted by PDR (descending) and Delay (ascending)
"""

import csv
import os

# Get the script's directory and construct absolute paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, 'results', 'parsed_results.csv')
OUTPUT_MD = os.path.join(SCRIPT_DIR, 'ANALYSIS-RESULTS.md')

def get_rating(pdr, delay):
    """
    Determine rating based on PDR and delay
    Returns: emoji rating string
    """
    if pdr >= 99.0 and delay < 10.0:
        return "⭐ Excellent"
    elif pdr >= 98.0 and delay < 15.0:
        return "✅ Very Good"
    elif pdr >= 95.0 and delay < 20.0:
        return "✅ Good"
    elif pdr >= 90.0:
        return "⚠️ Fair"
    else:
        return "❌ Poor"


def main():
    print("=" * 80)
    print("  SUMMARY TABLE GENERATOR")
    print("=" * 80)
    print(f"  Input: {INPUT_CSV}")
    print(f"  Output: {OUTPUT_MD}")
    print()
    
    # Check if input file exists
    if not os.path.exists(INPUT_CSV):
        print(f"✗ Input file not found: {INPUT_CSV}")
        print("  Run parse_results.py first!")
        return
    
    # Read CSV data
    data = []
    with open(INPUT_CSV, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append({
                'ap_height': float(row['ap_height']),
                'sta_height': int(row['sta_height']),
                'pdr_mean': float(row['pdr_mean']),
                'pdr_std': float(row['pdr_std']),
                'throughput_mean': float(row['throughput_mean']),
                'throughput_std': float(row['throughput_std']),
                'delay_mean': float(row['delay_mean']),
                'delay_std': float(row['delay_std']),
                'num_trials': int(row['num_trials'])
            })
    
    print(f"Loaded {len(data)} configurations")
    print()
    
    # Sort by PDR (descending) then Delay (ascending)
    data.sort(key=lambda x: (-x['pdr_mean'], x['delay_mean']))
    
    # Generate markdown table
    with open(OUTPUT_MD, 'w') as md:
        md.write("# Mesh AP Height Optimization - Analysis Results\n\n")
        md.write("**Date**: Generated automatically\n\n")
        md.write("**Configuration**: 3 AP heights × 6 STA heights × 3 trials = 54 simulations\n\n")
        md.write("**Metrics**:\n")
        md.write("- **PDR (Packet Delivery Ratio)**: Percentage of packets successfully delivered\n")
        md.write("- **Throughput**: Average data rate in Mbps\n")
        md.write("- **End-to-End Delay**: Average packet delay in milliseconds\n\n")
        md.write("---\n\n")
        
        # Overall summary table (sorted by performance)
        md.write("## Overall Results (Sorted by Performance)\n\n")
        md.write("| Rank | AP Height (m) | STA Height (m) | PDR (%) | Throughput (Mbps) | Delay (ms) | Rating |\n")
        md.write("|------|---------------|----------------|---------|-------------------|------------|--------|\n")
        
        for idx, row in enumerate(data, 1):
            rating = get_rating(row['pdr_mean'], row['delay_mean'])
            md.write(f"| {idx} | **{row['ap_height']}** | **{row['sta_height']}** | ")
            md.write(f"{row['pdr_mean']:.2f} ± {row['pdr_std']:.2f} | ")
            md.write(f"{row['throughput_mean']:.2f} ± {row['throughput_std']:.2f} | ")
            md.write(f"{row['delay_mean']:.2f} ± {row['delay_std']:.2f} | ")
            md.write(f"{rating} |\n")
        
        md.write("\n---\n\n")
        
        # Results grouped by AP height
        md.write("## Results by AP Height\n\n")
        
        ap_heights = sorted(set(row['ap_height'] for row in data))
        
        for ap_h in ap_heights:
            md.write(f"### AP Height: {ap_h}m\n\n")
            md.write("| STA Height (m) | PDR (%) | Throughput (Mbps) | Delay (ms) | Rating |\n")
            md.write("|----------------|---------|-------------------|------------|--------|\n")
            
            # Filter and sort by STA height for this AP height
            ap_data = [r for r in data if r['ap_height'] == ap_h]
            ap_data.sort(key=lambda x: x['sta_height'])
            
            for row in ap_data:
                rating = get_rating(row['pdr_mean'], row['delay_mean'])
                md.write(f"| **{row['sta_height']}** | ")
                md.write(f"{row['pdr_mean']:.2f} ± {row['pdr_std']:.2f} | ")
                md.write(f"{row['throughput_mean']:.2f} ± {row['throughput_std']:.2f} | ")
                md.write(f"{row['delay_mean']:.2f} ± {row['delay_std']:.2f} | ")
                md.write(f"{rating} |\n")
            
            md.write("\n")
        
        md.write("---\n\n")
        
        # Best configurations
        md.write("## Best Configurations\n\n")
        
        # Top 5 by PDR
        md.write("### Top 5 by PDR\n\n")
        top_pdr = sorted(data, key=lambda x: -x['pdr_mean'])[:5]
        md.write("| Rank | AP Height (m) | STA Height (m) | PDR (%) | Delay (ms) |\n")
        md.write("|------|---------------|----------------|---------|------------|\n")
        for idx, row in enumerate(top_pdr, 1):
            md.write(f"| {idx} | {row['ap_height']} | {row['sta_height']} | ")
            md.write(f"{row['pdr_mean']:.2f} | {row['delay_mean']:.2f} |\n")
        md.write("\n")
        
        # Top 5 by lowest delay
        md.write("### Top 5 by Lowest Delay\n\n")
        top_delay = sorted(data, key=lambda x: x['delay_mean'])[:5]
        md.write("| Rank | AP Height (m) | STA Height (m) | Delay (ms) | PDR (%) |\n")
        md.write("|------|---------------|----------------|------------|----------|\n")
        for idx, row in enumerate(top_delay, 1):
            md.write(f"| {idx} | {row['ap_height']} | {row['sta_height']} | ")
            md.write(f"{row['delay_mean']:.2f} | {row['pdr_mean']:.2f} |\n")
        md.write("\n")
        
        # Top 5 by throughput
        md.write("### Top 5 by Throughput\n\n")
        top_throughput = sorted(data, key=lambda x: -x['throughput_mean'])[:5]
        md.write("| Rank | AP Height (m) | STA Height (m) | Throughput (Mbps) | PDR (%) |\n")
        md.write("|------|---------------|----------------|-------------------|----------|\n")
        for idx, row in enumerate(top_throughput, 1):
            md.write(f"| {idx} | {row['ap_height']} | {row['sta_height']} | ")
            md.write(f"{row['throughput_mean']:.2f} | {row['pdr_mean']:.2f} |\n")
        md.write("\n")
        
        md.write("---\n\n")
        
        # Recommendations
        md.write("## Recommendations\n\n")
        
        best_config = data[0]  # Already sorted by performance
        md.write(f"**Optimal Configuration**: AP Height = **{best_config['ap_height']}m**, ")
        md.write(f"STA Height = **{best_config['sta_height']}m**\n\n")
        md.write(f"- **PDR**: {best_config['pdr_mean']:.2f}% (± {best_config['pdr_std']:.2f}%)\n")
        md.write(f"- **Throughput**: {best_config['throughput_mean']:.2f} Mbps (± {best_config['throughput_std']:.2f} Mbps)\n")
        md.write(f"- **Delay**: {best_config['delay_mean']:.2f} ms (± {best_config['delay_std']:.2f} ms)\n")
        md.write(f"- **Rating**: {get_rating(best_config['pdr_mean'], best_config['delay_mean'])}\n\n")
        
        # Summary by AP height
        md.write("### Summary by AP Height\n\n")
        for ap_h in ap_heights:
            ap_configs = [r for r in data if r['ap_height'] == ap_h]
            avg_pdr = sum(r['pdr_mean'] for r in ap_configs) / len(ap_configs)
            avg_delay = sum(r['delay_mean'] for r in ap_configs) / len(ap_configs)
            avg_throughput = sum(r['throughput_mean'] for r in ap_configs) / len(ap_configs)
            
            md.write(f"**AP Height {ap_h}m**: Avg PDR = {avg_pdr:.2f}%, ")
            md.write(f"Avg Delay = {avg_delay:.2f} ms, ")
            md.write(f"Avg Throughput = {avg_throughput:.2f} Mbps\n\n")
        
        md.write("---\n\n")
        md.write("*Analysis generated automatically from 54 simulation runs*\n")
    
    print("=" * 80)
    print(f"✓ Summary table generated: {OUTPUT_MD}")
    print("=" * 80)
    print()
    print("Top 3 configurations:")
    for idx, row in enumerate(data[:3], 1):
        rating = get_rating(row['pdr_mean'], row['delay_mean'])
        print(f"  {idx}. AP={row['ap_height']}m, STA={row['sta_height']}m: ")
        print(f"     PDR={row['pdr_mean']:.2f}%, Delay={row['delay_mean']:.2f}ms, {rating}")
    print()


if __name__ == '__main__':
    main()

