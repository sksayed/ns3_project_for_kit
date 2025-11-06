#!/bin/bash

# Script to test STA height impact on PDR
# Mesh nodes at z=15m (rooftop level), STA at varying heights
# Buildings are 15m tall

cd /home/sayed/ns-3-dev

OUTPUT_DIR="wifi_test_research/height_tests"

echo "==============================================================================="
echo "STA HEIGHT TEST - Vertical Spacing Analysis"
echo "==============================================================================="
echo "Configuration:"
echo "  - Mesh AP nodes: z = 1.5m (typical outdoor mounting height)"
echo "  - Buildings: 15m tall (0-15m)"
echo "  - Node spacing: 250m (optimal)"
echo "  - STA heights: 5m, 10m, 15m, 20m, 25m, 30m"
echo ""
echo "Test Question: Can users at different heights connect to ground-level APs?"
echo "Expected:"
echo "  - z = 0-5m: Ground level users (best case)"
echo "  - z = 10m: Mid-level users (2-3 floors up)"
echo "  - z = 15m: Rooftop level (at building height)"
echo "  - z > 15m: Above buildings (clear LOS)"
echo "==============================================================================="
echo ""

# Test heights from 5m to 30m in 5m increments
for height in 5 10 15 20 25 30; do
    echo "=== TEST: STA Height = ${height}m ==="
    echo "Running simulation..."
    
    ./ns3 run "wifi-test-2-adhoc-grid --staHeight=$height" 2>&1 \
        > "$OUTPUT_DIR/test-sta-${height}m.txt"
    
    echo "✓ Completed"
    echo ""
done

echo "==============================================================================="
echo "Extracting results..."
echo "==============================================================================="

# Function to extract packet loss from output
extract_loss() {
    local file=$1
    grep "Total Lost Packets:" "$file" | grep -oP '\([0-9]+\.[0-9]+%\)' | tr -d '()%'
}

# Function to extract average delay
extract_delay() {
    local file=$1
    grep "Average Delay:" "$file" | grep -oP '[0-9]+\.[0-9]+'
}

# Function to calculate PDR from loss
calc_pdr() {
    local loss=$1
    echo "100 - $loss" | bc -l
}

echo ""
echo "STA Height Test Results:"
echo "=========================================================================="
echo "Height | Packet Loss % | PDR (%) | Avg Delay (ms) | Rating"
echo "-------|---------------|---------|----------------|--------"

for height in 5 10 15 20 25 30; do
    file="$OUTPUT_DIR/test-sta-${height}m.txt"
    if [ -f "$file" ]; then
        loss=$(extract_loss "$file")
        delay=$(extract_delay "$file")
        if [ -n "$loss" ] && [ -n "$delay" ]; then
            pdr=$(calc_pdr "$loss")
            
            # Determine rating
            if (( $(echo "$pdr >= 99.0" | bc -l) )); then
                rating="⭐ Excellent"
            elif (( $(echo "$pdr >= 97.0" | bc -l) )); then
                rating="✅ Good"
            elif (( $(echo "$pdr >= 95.0" | bc -l) )); then
                rating="⚠️  Fair"
            else
                rating="❌ Poor"
            fi
            
            printf "%4dm  | %12s%% | %6.2f%% | %13s | %s\n" "$height" "$loss" "$pdr" "$delay" "$rating"
        fi
    fi
done

echo "=========================================================================="
echo ""
echo "Building Height Reference: 15m"
echo "Mesh AP Height: 1.5m (ground-level APs)"
echo ""
echo "==============================================================================="
echo "ANALYSIS SUMMARY"
echo "==============================================================================="

# Save results to summary file
{
    echo "# STA Height Test Results"
    echo ""
    echo "Date: $(date)"
    echo "Configuration: Mesh nodes at z=15m, Buildings at 15m height"
    echo ""
    echo "| Height | Packet Loss % | PDR (%) | Avg Delay (ms) | Rating |"
    echo "|--------|---------------|---------|----------------|--------|"
    
    for height in 5 10 15 20 25 30; do
        file="$OUTPUT_DIR/test-sta-${height}m.txt"
        if [ -f "$file" ]; then
            loss=$(extract_loss "$file")
            delay=$(extract_delay "$file")
            if [ -n "$loss" ] && [ -n "$delay" ]; then
                pdr=$(calc_pdr "$loss")
                
                if (( $(echo "$pdr >= 99.0" | bc -l) )); then
                    rating="⭐ Excellent"
                elif (( $(echo "$pdr >= 97.0" | bc -l) )); then
                    rating="✅ Good"
                elif (( $(echo "$pdr >= 95.0" | bc -l) )); then
                    rating="⚠️  Fair"
                else
                    rating="❌ Poor"
                fi
                
                echo "| ${height}m | ${loss}% | ${pdr}% | ${delay}ms | $rating |"
            fi
        fi
    done
    
    echo ""
    echo "## Key Findings"
    echo ""
    echo "- Buildings: 15m height"
    echo "- Mesh nodes: 15m (rooftop level)"
    echo "- Best PDR found at: [See table above]"
    
} > "$OUTPUT_DIR/RESULTS-SUMMARY.md"

echo "Results saved to $OUTPUT_DIR/RESULTS-SUMMARY.md"
echo "==============================================================================="

