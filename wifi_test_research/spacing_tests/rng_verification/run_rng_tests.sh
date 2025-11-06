#!/bin/bash

# Script to verify if 250m is consistently better than 200m
# Runs multiple tests with different RNG seeds

cd /home/sayed/ns-3-dev

OUTPUT_DIR="wifi_test_research/spacing_tests/rng_verification"

echo "==============================================================================="
echo "RNG VERIFICATION TEST - 200m vs 250m Spacing"
echo "==============================================================================="
echo "Running 5 tests for each spacing with different RNG seeds..."
echo ""

# Test 200m spacing with 5 different RNG seeds
echo "Testing 200m spacing..."
for i in {1..5}; do
    echo "  Run $i/5..."
    ./ns3 run "wifi-test-2-adhoc-grid --nodeSpacing=200 --RngRun=$i" 2>&1 \
        > "$OUTPUT_DIR/test-200m-run$i.txt"
done

echo ""
echo "Testing 250m spacing..."
# Test 250m spacing with 5 different RNG seeds
for i in {1..5}; do
    echo "  Run $i/5..."
    ./ns3 run "wifi-test-2-adhoc-grid --nodeSpacing=250 --RngRun=$i" 2>&1 \
        > "$OUTPUT_DIR/test-250m-run$i.txt"
done

echo ""
echo "==============================================================================="
echo "Extracting results..."
echo "==============================================================================="

# Function to extract packet loss from output
extract_loss() {
    local file=$1
    grep "Total Lost Packets:" "$file" | grep -oP '\(.*?\)' | grep -oP '[0-9]+\.[0-9]+'
}

# Function to extract average delay
extract_delay() {
    local file=$1
    grep "Average Delay:" "$file" | grep -oP '[0-9]+\.[0-9]+'
}

# Collect 200m results
echo ""
echo "200m Spacing Results:"
echo "Run | Loss %  | Avg Delay (ms)"
echo "----|---------|--------------"
total_loss_200=0
total_delay_200=0
count_200=0
for i in {1..5}; do
    file="$OUTPUT_DIR/test-200m-run$i.txt"
    if [ -f "$file" ]; then
        loss=$(extract_loss "$file")
        delay=$(extract_delay "$file")
        if [ -n "$loss" ] && [ -n "$delay" ]; then
            printf "%3d | %6s%% | %s\n" "$i" "$loss" "$delay"
            total_loss_200=$(echo "$total_loss_200 + $loss" | bc)
            total_delay_200=$(echo "$total_delay_200 + $delay" | bc)
            count_200=$((count_200 + 1))
        fi
    fi
done

# Collect 250m results
echo ""
echo "250m Spacing Results:"
echo "Run | Loss %  | Avg Delay (ms)"
echo "----|---------|--------------"
total_loss_250=0
total_delay_250=0
count_250=0
for i in {1..5}; do
    file="$OUTPUT_DIR/test-250m-run$i.txt"
    if [ -f "$file" ]; then
        loss=$(extract_loss "$file")
        delay=$(extract_delay "$file")
        if [ -n "$loss" ] && [ -n "$delay" ]; then
            printf "%3d | %6s%% | %s\n" "$i" "$loss" "$delay"
            total_loss_250=$(echo "$total_loss_250 + $loss" | bc)
            total_delay_250=$(echo "$total_delay_250 + $delay" | bc)
            count_250=$((count_250 + 1))
        fi
    fi
done

# Calculate averages
echo ""
echo "==============================================================================="
echo "STATISTICAL ANALYSIS"
echo "==============================================================================="

if [ $count_200 -gt 0 ]; then
    avg_loss_200=$(echo "scale=4; $total_loss_200 / $count_200" | bc)
    avg_delay_200=$(echo "scale=2; $total_delay_200 / $count_200" | bc)
    echo "200m Average: Loss = ${avg_loss_200}%, Delay = ${avg_delay_200}ms"
fi

if [ $count_250 -gt 0 ]; then
    avg_loss_250=$(echo "scale=4; $total_loss_250 / $count_250" | bc)
    avg_delay_250=$(echo "scale=2; $total_delay_250 / $count_250" | bc)
    echo "250m Average: Loss = ${avg_loss_250}%, Delay = ${avg_delay_250}ms"
fi

echo ""
echo "==============================================================================="
echo "CONCLUSION"
echo "==============================================================================="

if [ $count_200 -gt 0 ] && [ $count_250 -gt 0 ]; then
    # Compare averages
    loss_diff=$(echo "$avg_loss_200 - $avg_loss_250" | bc)
    delay_diff=$(echo "$avg_delay_200 - $avg_delay_250" | bc)
    
    echo "Difference (200m - 250m):"
    echo "  Packet Loss: ${loss_diff}%"
    echo "  Delay: ${delay_diff}ms"
    echo ""
    
    # Determine winner
    if (( $(echo "$avg_loss_250 < $avg_loss_200" | bc -l) )); then
        echo "✅ 250m is CONSISTENTLY BETTER (lower loss)"
    elif (( $(echo "$avg_loss_200 < $avg_loss_250" | bc -l) )); then
        echo "❌ 200m is actually better (lower loss)"
    else
        echo "⚖️  Both spacings perform similarly"
    fi
fi

echo "==============================================================================="






