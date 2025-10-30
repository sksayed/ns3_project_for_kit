#!/bin/bash

# Simple NR Simulation Runner Script
# This script compiles and runs the simple NR simulation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Simple NR Simulation Runner ===${NC}"

# Check if we're in the right directory
if [ ! -f "ns3" ]; then
    echo -e "${RED}Error: Please run this script from the ns-3-dev root directory${NC}"
    exit 1
fi

# Check if NR module is available
if [ ! -d "contrib/nr" ]; then
    echo -e "${RED}Error: NR module not found. Please ensure NR module is installed.${NC}"
    exit 1
fi

# Create scratch directory if it doesn't exist
mkdir -p scratch

# Copy the simulation file to scratch
echo -e "${YELLOW}Copying simulation file to scratch directory...${NC}"
cp 5g/src/simple-nr-simulation.cc scratch/

# Build the simulation
echo -e "${YELLOW}Building the simulation...${NC}"
./ns3 build

# Check if build was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Build successful!${NC}"
else
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

# Create output directory
mkdir -p 5g/outputs

# Run the simulation with different parameters
echo -e "${BLUE}Running simple NR simulation...${NC}"
echo -e "${YELLOW}Parameters: 1 gNB, 2 UEs, 1 second simulation${NC}"

./ns3 run "simple-nr-simulation --simTime=1 --gNbNum=1 --ueNumPergNb=2 --enableLogging=false" > 5g/outputs/simple-nr-output.txt 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Simulation completed successfully!${NC}"
    echo -e "${BLUE}Output saved to: 5g/outputs/simple-nr-output.txt${NC}"
    
    # Show summary
    echo -e "${YELLOW}=== Simulation Summary ===${NC}"
    tail -20 5g/outputs/simple-nr-output.txt
else
    echo -e "${RED}Simulation failed!${NC}"
    echo -e "${YELLOW}Check the output file for details: 5g/outputs/simple-nr-output.txt${NC}"
    exit 1
fi

echo -e "${GREEN}=== Simple NR Simulation Complete ===${NC}"
